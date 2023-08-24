import logging
import time
from _decimal import Decimal
from typing import Optional, List

from rubi import (
    OrderEvent,
    OrderBook,
    OrderType,
    NewLimitOrder,
    OrderSide,
    NewCancelOrder,
    OrderTrackingClient,
    RubiconMarketApproval,
    TransactionStatus,
)
from web3.types import TxParams

from event_trading_framework import BaseEventTradingFramework
from example_bots.helpers.grid import Grid

logger = logging.getLogger(__name__)


class GridBot(BaseEventTradingFramework):
    def __init__(
        self,
        pair_name: str,
        grid: Grid,
        client: OrderTrackingClient,
    ):
        # Setup client
        self.client = client

        # set max approval for pair
        self.pair_name = pair_name
        base_asset, quote_asset = pair_name.split("/")

        current_base_allowance = client.get_allowance(
            base_asset, self.client.network.rubicon_market.address
        )
        if (
            current_base_allowance
            != client.network.tokens[base_asset].max_approval_amount()
        ):
            transaction = client.approve(
                RubiconMarketApproval(
                    token=base_asset,
                    amount=self.client.network.tokens[base_asset].max_approval_amount(),
                )
            )
            if transaction:
                client.execute_transaction(transaction=transaction)

        current_quote_allowance = client.get_allowance(
            quote_asset, self.client.network.rubicon_market.address
        )
        if (
            current_quote_allowance
            != client.network.tokens[quote_asset].max_approval_amount()
        ):
            transaction = client.approve(
                RubiconMarketApproval(
                    token=quote_asset,
                    amount=self.client.network.tokens[
                        quote_asset
                    ].max_approval_amount(),
                )
            )
            if transaction:
                client.execute_transaction(transaction=transaction)

        # Instantiate framework
        super().__init__(event_queue=client.message_queue)

        # Strategy variables
        self.grid: Grid = grid

        # allowed to trade
        self.allowed_to_place_new_orders: bool = False

        # Orderbook data
        self.orderbook: Optional[OrderBook] = None

        # Transaction variables
        self.consecutive_failure_count = 0

    def on_startup(self):
        # Orderbook poller
        self.client.start_orderbook_poller(pair_name=self.pair_name)

        base_asset_wallet_balance = self.client.get_balance(self.grid.base_asset)
        quote_asset_wallet_balance = self.client.get_balance(self.grid.quote_asset)

        self.grid.update_inventory(
            open_orders=self.client.open_limit_orders,
            base_asset_wallet_balance=base_asset_wallet_balance,
            quote_asset_wallet_balance=quote_asset_wallet_balance,
        )

        # set allowed_to_place_new_orders to True
        self.allowed_to_place_new_orders = True

    def on_shutdown(self):
        logger.info("Shutting down")

    def on_orderbook(self, orderbook: OrderBook):
        logger.debug(f"NEW ORDERBOOK, timestamp: {time.time_ns()}")
        logger.debug(orderbook)

        # set strategy orderbook
        self.orderbook = orderbook

        # construct and place grid
        if self.allowed_to_place_new_orders:
            orders = self.grid.get_orders(
                best_bid_price=orderbook.best_bid(),
                best_ask_price=orderbook.best_ask(),
            )

            transaction = self.build_new_limit_orders(orders=orders)
            if transaction:
                self.place_transaction(transaction=transaction)
        else:
            logger.info("Not currently allowed to place new orders")

    def on_order(self, order: OrderEvent):
        logger.debug(f"NEW ORDER EVENT, timestamp: {time.time_ns()}")
        logger.debug(order)

        if order.order_type == OrderType.LIMIT_TAKEN:
            self.grid.add_trade(
                order_side=order.order_side, price=order.price, size=order.size
            )

    ######################################################################
    # place transaction methods
    ######################################################################

    def build_new_limit_orders(self, orders: Optional[List[NewLimitOrder]]) -> TxParams:
        new_orders: List[NewLimitOrder] = list(
            filter(lambda order: not self._is_open_order(order), orders)
        )

        orders_to_place: List[
            NewLimitOrder
        ] = self._check_sufficient_inventory_to_place(new_orders=new_orders)

        if orders_to_place is None or len(orders_to_place) == 0:
            logger.debug("no new orders provided to place_new_limit_orders")
            return

        transaction_amount = sum(map(lambda order: order.size, orders_to_place))
        if self.grid.min_transaction_size_in_base > transaction_amount:
            # Do not send a transaction which does not meet the min transaction size
            return

        if len(orders_to_place) == 1:
            logger.info(
                f"placing limit order: {orders_to_place}, timestamp: {time.time_ns()}"
            )

            return self.client.limit_order(order=orders_to_place[0])
        else:
            logger.info(
                f"batch placing limit orders: {orders_to_place}, timestamp: {time.time_ns()}"
            )

            return self.client.batch_limit_orders(orders=orders_to_place)

    def build_cancel_all_open_orders(self) -> None:
        orders_to_cancel: List[NewCancelOrder] = list(
            map(
                lambda order_id: NewCancelOrder(
                    pair_name=self.pair_name, order_id=order_id
                ),
                self.client.open_limit_orders.keys(),
            )
        )

        if orders_to_cancel is None or len(orders_to_cancel) == 0:
            logger.debug("no orders to cancel")
            return

        if len(orders_to_cancel) == 1:
            return self.client.cancel_limit_order(order=orders_to_cancel[0])
        else:
            return self.client.batch_cancel_limit_orders(orders=orders_to_cancel)

    def place_transaction(self, transaction: TxParams):
        try:
            result = self.client.execute_transaction(transaction=transaction)

            match result.transaction_status:
                case TransactionStatus.SUCCESS:
                    self.consecutive_failure_count = 0
                    logger.info(f"Successful transaction: {result.transaction_hash}")
                case TransactionStatus.FAILURE:
                    self.consecutive_failure_count += 1
                    logger.warning(f"Failed transaction: {result.transaction_hash}")

        except Exception as e:
            self.consecutive_failure_count += 1
            logger.error(f"Failed to place transaction {transaction}: {e}")

        if self.consecutive_failure_count >= 5:
            self.allowed_to_place_new_orders = False
            self.running = False
            raise Exception(
                f"Failed to place transactions {self.consecutive_failure_count} times in a row. Not placing"
                f"any more orders"
            )

    ######################################################################
    # helper methods
    ######################################################################

    def _check_sufficient_inventory_to_place(
        self, new_orders: List[NewLimitOrder]
    ) -> List[NewLimitOrder]:
        base_amount_available = self.client.get_balance(self.grid.base_asset)
        quote_amount_available = self.client.get_balance(self.grid.quote_asset)

        orders_to_place = []

        for order in new_orders:
            match order.order_side:
                case OrderSide.BUY:
                    if quote_amount_available == Decimal("0"):
                        continue

                    if order.size * order.price <= quote_amount_available:
                        quote_amount_available -= order.size * order.price
                    else:
                        order.size = quote_amount_available / order.price
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

    def _is_open_order(self, order: NewLimitOrder) -> bool:
        for open_order in self.client.open_limit_orders.values():
            if order.order_side == open_order.order_side and abs(
                order.price - self.grid.round_to_grid_tick(open_order.price)
            ) < (self.grid.price_tick / Decimal("2")):
                if order.size >= open_order.remaining_size:
                    order.size = order.size - open_order.remaining_size

                    if order.size < self.grid.min_order_size_in_base:
                        return True
                else:
                    return True

        return False
