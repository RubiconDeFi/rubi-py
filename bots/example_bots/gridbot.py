import logging as log
import time
from _decimal import Decimal
from typing import Dict, Optional, List, Tuple

from rubi import (
    OrderEvent, OrderBook, Client, EmitOfferEvent, EmitTakeEvent, EmitCancelEvent, OrderType,
    NewLimitOrder, OrderSide, Transaction
)

from event_trading_framework import BaseEventTradingFramework, TransactionResult, TransactionStatus, \
    ThreadedTransactionManager
from example_bots.grid_types.active_limit_order import ActiveLimitOrder
from example_bots.grid_types.grid_params import GridParams
from example_bots.helpers.gas_manager import GasManager
from example_bots.helpers.inventory_manager import Inventory


class GridBot(BaseEventTradingFramework):
    def __init__(
        self,
        pair_name: str,
        grid_params: GridParams,
        client: Client,
    ):
        # Setup client
        self.client = client
        client.add_pair(pair_name=pair_name)

        # set max approval for pair
        pair = client.get_pair(pair_name=pair_name)
        client.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=pair.base_asset.max_approval_amount(),
            new_quote_asset_allowance=pair.quote_asset.max_approval_amount()
        )

        # Initialise transaction manager
        transaction_manager = ThreadedTransactionManager(
            client=client
        )

        # Instantiate framework
        super().__init__(event_queue=client.message_queue, transaction_manager=transaction_manager)

        # Setup gas tracker
        self.gas_tracker = GasManager(allowed_fluctuation=Decimal("0.5"), ema_multiplier=Decimal("0.05"))

        # Strategy objects
        self.pair = client.get_pair(pair_name=pair_name)
        self.inventory = Inventory(pair=self.pair, quote_asset_amount=grid_params.quote_asset_amount)

        # Strategy variables
        self.grid: GridParams = grid_params

        # allowed to trade
        self.allowed_to_place_new_orders: bool = False

        # Orderbook data
        self.orderbook: Optional[OrderBook] = None

        # Transaction variables
        self.pending_transactions: Dict[int, Transaction] = {}
        self.active_limit_orders: Dict[int, ActiveLimitOrder] = {}

        self.allowed_order_price_differential = Decimal(1 / 10 ** 18)
        self.allowed_order_size_differential = Decimal(1 / 10 ** 18)

    def on_startup(self):
        # Orderbook poller
        self.client.start_orderbook_poller(pair_name=self.pair.name)

        # Order event pollers
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitOfferEvent)
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitTakeEvent)
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitCancelEvent)

    def on_orderbook(self, orderbook: OrderBook):
        log.debug(f"NEW ORDERBOOK, timestamp: {time.time_ns()}")
        log.debug(orderbook)

        # set strategy orderbook
        self.orderbook = orderbook

        # construct and place grid
        self.place_new_limit_orders(orders=self.construct_grid())

    def on_order(self, order: OrderEvent):
        log.debug(f"NEW ORDER EVENT, timestamp: {time.time_ns()}")
        log.debug(order)

        match order.order_type:
            case OrderType.LIMIT:
                self.active_limit_orders[order.limit_order_id] = ActiveLimitOrder.from_order_event(order=order)
            case OrderType.LIMIT_TAKEN:
                taken_order = self.active_limit_orders[order.limit_order_id]

                self.inventory.add_trade(order_side=order.order_side, price=order.price, size=order.size)

                if taken_order.is_full_take(pair=self.pair, take_event=order):
                    log.info(f"Limit order {order.limit_order_id} fully taken")
                    del self.active_limit_orders[order.limit_order_id]
                else:
                    self.active_limit_orders[order.limit_order_id].update_with_take(take_event=order)
            case OrderType.CANCEL:
                log.info(f"Limit order {order.limit_order_id} cancelled")
                del self.active_limit_orders[order.limit_order_id]

    def on_transaction_result(self, result: TransactionResult):
        log.debug(f"NEW TRANSACTION RESULT, timestamp: {time.time_ns()}")
        log.debug(result)

        if result.transaction_receipt is None:
            log.warning(f"Failed to place transaction, with nonce: {result.nonce}")
            del self.pending_transactions[result.nonce]
            return

        # TODO: figure out gas tracking
        # if not self.gas_tracker.is_acceptable_cost(transaction=result):
        #     log.warning("Significant deviation ema gas cost. Pausing trading")
        #     self.allowed_to_place_new_orders = False
        #     # TODO: Cancel all current and pending orders
        #
        # self.gas_tracker.add_transaction(transaction=result)

        match result.status:
            case TransactionStatus.SUCCESS:
                log.info(f"Successful transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                         f"with nonce: {result.nonce}")
            case TransactionStatus.FAILURE:
                log.warning(f"Failed transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                            f"with nonce: {result.nonce}")

        del self.pending_transactions[result.nonce]

    ######################################################################
    # strategy methods
    ######################################################################

    def construct_grid(self):
        grid_orders = self.construct_grid_side(side=OrderSide.BUY) + self.construct_grid_side(side=OrderSide.SELL)

        return grid_orders

    def construct_grid_side(self, side: OrderSide) -> Optional[List[NewLimitOrder]]:
        grid_levels: [Tuple[int, int]] = []

        current_amount_available = (
            self.inventory.quote_asset_amount if side == OrderSide.BUY else self.inventory.base_asset_amount
        )

        for i in range(self.grid.number_levels - 1, -1, -1):
            price = self.grid.get_level_price(side=side, level=i)
            size = self.grid.get_level_size(level=i)

            if current_amount_available > size * price:
                grid_levels.append((price, size))
                current_amount_available -= size * price
            else:
                grid_levels.append((price, current_amount_available))
                break

        orders_to_place = []
        for level in grid_levels:
            if level[1] * level[0] >= self.grid.min_order_size_in_quote:
                orders_to_place.append(NewLimitOrder(
                    pair_name=self.pair.name,
                    order_side=side,
                    size=level[1],
                    price=level[0]
                ))

        return orders_to_place

    ######################################################################
    # place transaction methods
    ######################################################################

    def place_new_limit_orders(self, orders: Optional[List[NewLimitOrder]]) -> None:
        orders_to_place: List[NewLimitOrder] = list(filter(
            lambda order: not self._is_active_or_pending_order(order), orders
        ))

        if orders_to_place is None or len(orders_to_place) == 0:
            log.debug("no new orders provided to place_new_limit_orders")
            return

        transaction = Transaction(orders=orders_to_place)

        if len(orders) == 1:
            log.debug(f"placing limit order: {orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.place_limit_order, transaction)
        else:
            log.debug(f"batch placing limit orders: {orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.batch_place_limit_orders, transaction)

        self.pending_transactions[nonce] = transaction

    ######################################################################
    # helper methods
    ######################################################################

    def _is_active_or_pending_order(self, order: NewLimitOrder) -> bool:
        for active_order in self.active_limit_orders.values():
            if (
                order.order_side == active_order.order_side and
                abs(order.price - round(active_order.price, 18)) < self.allowed_order_price_differential and
                abs(order.size - round(active_order.size, 18)) < self.allowed_order_size_differential
            ):
                return True

        for pending_transactions in self.pending_transactions.values():
            for pending_order in pending_transactions.orders:
                if (
                    isinstance(pending_order, NewLimitOrder) and
                    order.order_side == pending_order.order_side and
                    abs(order.price - pending_order.price) < self.allowed_order_price_differential and
                    abs(order.size - pending_order.size) < self.allowed_order_size_differential
                ):
                    return True

        return False

    def _remove_own_orders_from_book(self):
        for active_order in self.active_limit_orders.values():
            match active_order.order_side:
                case OrderSide.BUY:
                    self.orderbook.bids.remove_liquidity_from_book(price=active_order.price, size=active_order.size)
                case OrderSide.SELL:
                    self.orderbook.asks.remove_liquidity_from_book(price=active_order.price, size=active_order.size)
