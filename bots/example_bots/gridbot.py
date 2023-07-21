import logging as log
import time
from _decimal import Decimal
from typing import Dict, Optional, List

from rubi import (
    OrderEvent, OrderBook, Client, EmitOfferEvent, EmitTakeEvent, EmitCancelEvent, OrderType,
    NewLimitOrder, OrderSide, Transaction, NewCancelOrder
)

from event_trading_framework import BaseEventTradingFramework, TransactionResult, TransactionStatus, \
    ThreadedTransactionManager
from example_bots.helpers.active_limit_order import ActiveLimitOrder
from example_bots.helpers.grid import Grid


class GridBot(BaseEventTradingFramework):
    def __init__(
        self,
        pair_name: str,
        grid: Grid,
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
        transaction_manager = ThreadedTransactionManager(client=client)

        # Instantiate framework
        super().__init__(event_queue=client.message_queue, transaction_manager=transaction_manager)

        # Strategy objects
        self.pair = client.get_pair(pair_name=pair_name)

        # Strategy variables
        self.grid: Grid = grid

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
        self.client.start_event_poller(
            pair_name=self.pair.name, event_type=EmitOfferEvent, filters={"maker": self.client.wallet}
        )
        self.client.start_event_poller(
            pair_name=self.pair.name, event_type=EmitTakeEvent, filters={"maker": self.client.wallet}
        )
        self.client.start_event_poller(
            pair_name=self.pair.name, event_type=EmitCancelEvent, filters={"maker": self.client.wallet}
        )

        # set allowed_to_place_new_orders to True
        self.allowed_to_place_new_orders = True

    def on_shutdown(self):
        self.cancel_all_active_orders()

        # Wait for all orders to be cancelled
        time.sleep(10)

    def on_orderbook(self, orderbook: OrderBook):
        log.debug(f"NEW ORDERBOOK, timestamp: {time.time_ns()}")
        log.debug(orderbook)

        # set strategy orderbook
        self.orderbook = orderbook

        # construct and place grid
        if self.allowed_to_place_new_orders:
            orders = self.grid.get_orders(
                best_bid_price=orderbook.best_bid(),
                best_ask_price=orderbook.best_ask(),
            )

            self.place_new_limit_orders(orders=orders)
        else:
            log.info("Not currently allowed to place new orders")

    def on_order(self, order: OrderEvent):
        log.debug(f"NEW ORDER EVENT, timestamp: {time.time_ns()}")
        log.debug(order)

        match order.order_type:
            case OrderType.LIMIT:
                self.active_limit_orders[order.limit_order_id] = ActiveLimitOrder.from_order_event(order=order)
            case OrderType.LIMIT_TAKEN:
                taken_order = self.active_limit_orders[order.limit_order_id]

                self.grid.add_trade(order_side=order.order_side, price=order.price, size=order.size)

                if taken_order.is_full_take(take_event=order):
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

        # TODO: gas tracking should be done here

        match result.status:
            case TransactionStatus.SUCCESS:
                log.info(f"Successful transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                         f"with nonce: {result.nonce}")
            case TransactionStatus.FAILURE:
                log.warning(f"Failed transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                            f"with nonce: {result.nonce}")

        del self.pending_transactions[result.nonce]

    ######################################################################
    # place transaction methods
    ######################################################################

    def place_new_limit_orders(self, orders: Optional[List[NewLimitOrder]]) -> None:
        new_orders: List[NewLimitOrder] = list(filter(
            lambda order: not self._is_active_or_pending_order(order), orders
        ))

        orders_to_place: List[NewLimitOrder] = self._check_sufficient_inventory_to_place(new_orders=new_orders)

        if orders_to_place is None or len(orders_to_place) == 0:
            log.debug("no new orders provided to place_new_limit_orders")
            return

        transaction = Transaction(orders=orders_to_place)

        transaction_amount = sum(map(lambda order: order.size, transaction.orders))
        if self.grid.min_transaction_size_in_base > transaction_amount:
            # Do not send a transaction which does not meet the min transaction size
            return

        if len(transaction.orders) == 1:
            log.debug(f"placing limit order: {transaction.orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.place_limit_order, transaction)
        else:
            log.debug(f"batch placing limit orders: {transaction.orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.batch_place_limit_orders, transaction)

        self.pending_transactions[nonce] = transaction

    def cancel_all_active_orders(self) -> None:
        orders_to_cancel: List[NewCancelOrder] = list(
            map(
                lambda order_id: NewCancelOrder(pair_name=self.pair.name, order_id=order_id),
                self.active_limit_orders.keys()
            )
        )

        if orders_to_cancel is None or len(orders_to_cancel) == 0:
            log.debug("no orders to cancel")
            return

        transaction = Transaction(orders=orders_to_cancel)

        if len(transaction.orders) == 1:
            log.debug(f"cancelling limit order: {transaction.orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.cancel_limit_order, transaction)
        else:
            log.debug(f"batch cancelling limit orders: {transaction.orders}, timestamp: {time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.batch_cancel_limit_orders, transaction)

        self.pending_transactions[nonce] = transaction

    ######################################################################
    # helper methods
    ######################################################################

    def _amount_in_market(self, side: OrderSide) -> Decimal:
        active_orders = list(filter(lambda order: order.order_side == side, self.active_limit_orders.values()))
        pending_orders = []
        for pending_transaction in self.pending_transactions.values():
            pending_orders.extend(list(filter(lambda order: order.order_side == side, pending_transaction.orders)))

        amount = (
            sum(map(lambda order: order.remaining_size(), active_orders)) +
            sum(map(lambda order: order.size, pending_orders))
        )

        return amount

    def _check_sufficient_inventory_to_place(self, new_orders: List[NewLimitOrder]) -> List[NewLimitOrder]:
        quote_in_market = self._amount_in_market(side=OrderSide.BUY)
        base_in_market = self._amount_in_market(side=OrderSide.SELL)

        quote_amount_available = self.grid.get_quote_asset_amount() - quote_in_market
        base_amount_available = self.grid.get_base_asset_amount() - base_in_market

        orders_to_place = []

        for order in new_orders:
            match order.order_side:
                case OrderSide.BUY:
                    if quote_amount_available == Decimal("0"):
                        continue

                    if order.size <= quote_amount_available:
                        quote_amount_available -= order.size
                    else:
                        order.size = quote_amount_available
                        quote_amount_available = Decimal("0")
                    if order.size >= self.grid.min_order_size_in_base:
                        orders_to_place.append(order)

                case OrderSide.SELL:
                    if base_amount_available == Decimal("0"):
                        continue

                    if order.size <= base_amount_available:
                        base_amount_available -= order.size
                    else:
                        order.size = base_amount_available
                        base_amount_available = Decimal("0")
                    if order.size >= self.grid.min_order_size_in_base:
                        orders_to_place.append(order)

        return orders_to_place

    def _is_active_or_pending_order(self, order: NewLimitOrder) -> bool:
        for active_order in self.active_limit_orders.values():
            if (
                order.order_side == active_order.order_side
                and abs(
                    order.price - self.grid.round_to_grid_tick(active_order.price)
                ) < self.allowed_order_price_differential
            ):
                if order.size >= active_order.remaining_size():
                    order.size = order.size - active_order.remaining_size()

                    if order.size < self.grid.min_order_size_in_base:
                        return True
                else:
                    return True

        for pending_transactions in self.pending_transactions.values():
            for pending_order in pending_transactions.orders:
                if (
                    isinstance(pending_order, NewLimitOrder) and
                    order.order_side == pending_order.order_side and
                    abs(order.price - pending_order.price) < self.allowed_order_price_differential
                ):
                    if order.size >= pending_order.size:
                        order.size = order.size - pending_order.size

                    if order.size < self.grid.min_order_size_in_base:
                        return True
                    else:
                        return True

        return False

    def _remove_own_orders_from_book(self):
        for active_order in self.active_limit_orders.values():
            match active_order.order_side:
                case OrderSide.BUY:
                    self.orderbook.bids.remove_liquidity_from_book(price=active_order.price, size=active_order.size)
                case OrderSide.SELL:
                    self.orderbook.asks.remove_liquidity_from_book(price=active_order.price, size=active_order.size)
