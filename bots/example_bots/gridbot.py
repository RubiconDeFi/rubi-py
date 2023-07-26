import logging as log
import time
from _decimal import Decimal
from typing import Dict, Optional, List

from rubi import (
    OrderEvent, OrderBook, Client, EmitOfferEvent, EmitTakeEvent, EmitCancelEvent, OrderType,
    NewLimitOrder, Transaction, NewCancelOrder
)

from event_trading_framework import BaseEventTradingFramework, TransactionResult, TransactionStatus, \
    ThreadedTransactionManager
from example_bots.helpers.active_limit_order import ActiveLimitOrder
from example_bots.helpers.grid import Grid


class GridBot(BaseEventTradingFramework):
    def __init__(
        self,
        grids: Dict[str, Grid],
        client: Client,
        min_transaction_size: Decimal | str,
    ):
        # Setup grids
        self.grids: Dict[str, Grid] = grids

        # Setup client
        self.client = client
        for pair_name, _ in self.grids.items():
            client.add_pair(pair_name=pair_name)

            pair = client.get_pair(pair_name=pair_name)

            # set max approval for pair
            client.update_pair_allowance(
                pair_name=pair.name,
                new_base_asset_allowance=pair.base_asset.max_approval_amount(),
                new_quote_asset_allowance=pair.quote_asset.max_approval_amount()
            )

        # Check wallet has sufficient balance of assets
        self._check_wallet_balance()

        # Initialise transaction manager
        transaction_manager = ThreadedTransactionManager(client=client)

        # Instantiate framework
        super().__init__(event_queue=client.message_queue, transaction_manager=transaction_manager)

        # allowed to trade
        self.allowed_to_place_new_orders: bool = False

        # Orderbook data
        self.orderbook: Dict[str, OrderBook] = {}

        # Transaction variables
        self.pending_transactions: Dict[int, Transaction] = {}
        self.active_limit_orders: Dict[int, ActiveLimitOrder] = {}

        self.consecutive_failure_count = 0

        self.min_transaction_size = Decimal(min_transaction_size)

        self.allowed_order_price_differential = Decimal(1 / 10 ** 18)
        self.allowed_order_size_differential = Decimal(1 / 10 ** 18)

    def on_startup(self):
        for pair_name, grid in self.grids.items():
            # Orderbook poller
            self.client.start_orderbook_poller(pair_name=pair_name)

            self.orderbook[pair_name] = self.client.get_orderbook(pair_name=pair_name)

            # Order event pollers
            self.client.start_event_poller(
                pair_name=pair_name, event_type=EmitOfferEvent, filters={"maker": self.client.wallet}
            )
            self.client.start_event_poller(
                pair_name=pair_name, event_type=EmitTakeEvent, filters={"maker": self.client.wallet}
            )
            self.client.start_event_poller(
                pair_name=pair_name, event_type=EmitCancelEvent, filters={"maker": self.client.wallet}
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
        self.orderbook[orderbook.pair_name] = orderbook

        # construct and place grid
        if self.allowed_to_place_new_orders:
            orders = []
            for pair_name, grid in self.grids.items():
                orders.extend(
                    grid.get_orders(
                        best_bid_price=self.orderbook[pair_name].best_bid(),
                        best_ask_price=self.orderbook[pair_name].best_ask(),
                    )
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

                self.grids[order.pair_name].add_trade(order_side=order.order_side, price=order.price, size=order.size)

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
                self.consecutive_failure_count = 0
                log.info(f"Successful transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                         f"with nonce: {result.nonce}")
            case TransactionStatus.FAILURE:
                self.consecutive_failure_count += 1
                log.warning(f"Failed transaction: {result.transaction_receipt.transaction_hash.hex()}, "
                            f"with nonce: {result.nonce}")

        if self.consecutive_failure_count >= 5:
            self.allowed_to_place_new_orders = False
            raise Exception(f"Failed to place transactions {self.consecutive_failure_count} times in a row. Not placing"
                            f"any more orders")

        del self.pending_transactions[result.nonce]

    ######################################################################
    # place transaction methods
    ######################################################################

    def place_new_limit_orders(self, orders: Optional[List[NewLimitOrder]]) -> None:
        new_orders: List[NewLimitOrder] = list(filter(
            lambda order: not self._is_active_or_pending_order(order), orders
        ))

        orders_to_place: List[NewLimitOrder] = []
        for _, grid in self.grids.items():
            orders_to_place.extend(grid.check_sufficient_inventory_to_place(
                new_orders=new_orders,
                active_limit_orders=list(self.active_limit_orders.values()),
                pending_transactions=list(self.pending_transactions.values())
            ))

        if orders_to_place is None or len(orders_to_place) == 0:
            log.debug("no new orders provided to place_new_limit_orders")
            return

        transaction = Transaction(orders=orders_to_place)

        transaction_amount = sum(map(lambda order: order.size * order.price, transaction.orders))
        if self.min_transaction_size > transaction_amount:
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
                lambda order_id: NewCancelOrder(
                    pair_name=self.active_limit_orders[order_id].pair_name,
                    order_id=order_id
                ),
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

    def _check_wallet_balance(self):
        amounts_required: Dict[str, Decimal] = {}

        for _, grid in self.grids.items():
            if grid.base_asset in amounts_required:
                amounts_required[grid.base_asset] += grid.get_base_asset_amount()
            else:
                amounts_required[grid.base_asset] = grid.get_base_asset_amount()
            if grid.quote_asset in amounts_required:
                amounts_required[grid.quote_asset] += grid.get_quote_asset_amount()
            else:
                amounts_required[grid.quote_asset] = grid.get_quote_asset_amount()

        exceptions = []

        for _, pair in self.client._pairs.items():
            if pair.base_asset.symbol in amounts_required:
                balance = pair.base_asset.to_decimal(pair.base_asset.balance_of(self.client.wallet))

                if amounts_required[pair.base_asset.symbol] > balance:
                    exceptions.append(
                        f"Insufficient amount of {pair.base_asset.symbol} to run bot, have: "
                        f"{balance}, config requires: {amounts_required[pair.base_asset.symbol]}."
                    )
            if pair.quote_asset.symbol in amounts_required:
                balance = pair.quote_asset.to_decimal(pair.quote_asset.balance_of(self.client.wallet))

                if amounts_required[pair.quote_asset.symbol] > balance:
                    exceptions.append(
                        f"Insufficient amount of {pair.quote_asset.symbol} to run bot, have: "
                        f"{balance}, config requires: {amounts_required[pair.quote_asset.symbol]}."
                    )

        if len(exceptions) > 0:
            raise Exception(" ".join(exceptions))

    def _is_active_or_pending_order(self, order: NewLimitOrder) -> bool:
        for active_order in self.active_limit_orders.values():
            if (
                order.order_side == active_order.order_side
                and abs(
                    order.price - self.grids[order.pair_name].round_to_grid_tick(active_order.price)
                ) < self.allowed_order_price_differential
            ):
                if order.size >= active_order.remaining_size():
                    order.size = order.size - active_order.remaining_size()

                    if order.size < self.grids[order.pair_name].min_order_size_in_base:
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

                    if order.size < self.grids[order.pair_name].min_order_size_in_base:
                        return True
                    else:
                        return True

        return False
