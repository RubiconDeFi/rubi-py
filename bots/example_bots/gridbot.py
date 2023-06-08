import logging as log
import os
import signal
import time
from _decimal import Decimal
from multiprocessing import Queue
from typing import Dict, Optional, List, Tuple

from dotenv import load_dotenv
from rubi import (
    OrderEvent, OrderBook, Client, EmitOfferEvent, EmitTakeEvent, EmitCancelEvent, OrderType,
    NewLimitOrder, OrderSide, Transaction
)

from event_trading_framework import BaseEventTradingFramework
from event_trading_framework.gas_tracker import GasTracker
from event_trading_framework.transaction_manager import TransactionResult, TransactionStatus
from event_trading_framework.types.inventory import Inventory
from event_trading_framework.types.types import ActiveLimitOrder
from example_bots.grid import Grid


class GridBot(BaseEventTradingFramework):
    def __init__(
        self,
        pair_name: str,
        grid: Grid,
        min_order_size: Decimal,
        client: Client,
    ):
        super().__init__(event_queue=client.message_queue, nonce=client.get_nonce())

        # Setup client
        self.client = client
        client.add_pair(pair_name=pair_name)

        # Setup gas tracker
        self.gas_tracker = GasTracker(allowed_fluctuation=Decimal("0.5"), ema_multiplier=Decimal("0.05"))

        # Strategy objects
        self.pair = client.get_pair(pair_name=pair_name)
        self.inventory = Inventory(pair=self.pair, quote_asset_amount=grid.quote_asset_amount)

        # Strategy variables
        self.grid: Grid = grid
        self.min_order_size: Decimal = min_order_size

        # allowed to trade
        self.allowed_to_place_new_orders: bool = False

        # Orderbook data
        self.orderbook: Optional[OrderBook] = None

        # Transaction data
        self.pending_transactions: Dict[int, Transaction] = {}
        self.active_limit_orders: Dict[int, ActiveLimitOrder] = {}

        self.can_place = True

    def on_startup(self):
        # Orderbook poller
        self.client.start_orderbook_poller(pair_name=self.pair.name)

        # Order event pollers
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitOfferEvent)
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitTakeEvent)
        self.client.start_event_poller(pair_name=self.pair.name, event_type=EmitCancelEvent)

    def on_orderbook(self, orderbook: OrderBook):
        log.info("NEW ORDERBOOK")
        log.info(f"{time.time_ns()}")
        log.debug(orderbook)

        # set strategy orderbook
        self.orderbook = orderbook

        # construct and place grid
        if self.can_place:
            self.place_new_limit_orders(orders=self.construct_grid())

    def on_order(self, order: OrderEvent):
        log.info("NEW ORDER EVENT")
        log.info(f"{time.time_ns()}")
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
        log.info("NEW TRANSACTION RESULT")
        log.info(f"{time.time_ns()}")
        log.debug(result)

        if result.transaction_receipt is None:
            log.warning(f"Failed to place transaction, with nonce: {result.nonce}")
            del self.pending_transactions[result.nonce]
            return

        if not self.gas_tracker.is_acceptable_cost(transaction=result):
            log.warning("Significant deviation ema gas cost. Pausing trading")
            self.allowed_to_place_new_orders = False
            # TODO: Cancel all current and pending orders

        self.gas_tracker.add_transaction(transaction=result)

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

        for i in range(grid.number_levels - 1, -1, -1):
            price = grid.get_level_price(side=side, level=i)
            size = grid.get_level_size(level=i, price=price)

            if current_amount_available > size * price:
                grid_levels.append((price, size))
                current_amount_available -= size * price
            else:
                grid_levels.append((price, current_amount_available))
                break

        orders_to_place = []
        for level in grid_levels:
            if level[1] > self.min_order_size / grid.mid_price:
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
        self.can_place = False
        orders_to_place: List[NewLimitOrder] = list(filter(lambda order: not self._is_active_order(order), orders))

        if orders_to_place is None or len(orders_to_place) == 0:
            log.debug("no new orders provided to place_new_limit_orders")
            return

        transaction = Transaction(orders=orders_to_place)

        if len(orders) == 1:
            log.info(f"placing limit order: {orders}")
            log.info(f"{time.time_ns()}")
            nonce = self.transaction_manager.place_transaction(self.client.place_limit_order, transaction)
        else:
            log.debug(f"batch placing limit orders: {orders}")
            nonce = self.transaction_manager.place_transaction(self.client.batch_place_limit_orders, transaction)

        self.pending_transactions[nonce] = transaction

    def _is_active_order(self, order: NewLimitOrder) -> bool:
        for active_order in self.active_limit_orders.values():
            if (
                order.order_side == active_order.order_side and
                order.price == active_order.price and
                order.size == active_order.size
            ):
                return True

        return False

    ######################################################################
    # helper methods
    ######################################################################

    def _remove_own_orders_from_book(self):
        for active_order in self.active_limit_orders.values():
            match active_order.order_side:
                case OrderSide.BUY:
                    self.orderbook.bids.remove_liquidity_from_book(price=active_order.price, size=active_order.size)
                case OrderSide.SELL:
                    self.orderbook.asks.remove_liquidity_from_book(price=active_order.price, size=active_order.size)


if __name__ == "__main__":
    # setup logging
    log.basicConfig(level=log.INFO)

    # load and set env variables
    load_dotenv("local.env")

    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("DEV_WALLET")
    key = os.getenv("DEV_KEY")

    # Initialize strategy message queue
    message_queue = Queue()

    # Initialize rubicon client
    rubicon_client = Client.from_http_node_url(
        http_node_url=http_node_url,
        message_queue=message_queue,
        wallet=wallet,
        key=key
    )

    # Setup Grid
    grid = Grid(
        starting_base_asset_amount=Decimal("0"),
        starting_quote_asset_amount=Decimal("200"),
        starting_mid_price=Decimal("1860"),
        grid_spread_in_quote=Decimal("2"),
        level_spread_multiplier=Decimal("0"),
        number_levels=1,
        level_allocation_multiplier=Decimal("0")
    )

    # Initialize grid bot strategy
    grid_bot = GridBot(
        pair_name="WETH/USDC",
        grid=grid,
        min_order_size=Decimal("20"),
        client=rubicon_client,
    )

    # Shutdown bot on keyboard signal
    signal.signal(signal.SIGINT, grid_bot.stop)

    # Start grid bot strategy
    grid_bot.start()
