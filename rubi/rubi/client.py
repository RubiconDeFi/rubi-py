import logging as log
import math
from _decimal import Decimal
from multiprocessing import Queue
from threading import Thread
from time import sleep
from typing import Union, List, Optional, Dict, Type, Any, Callable

from eth_typing import ChecksumAddress
from web3.types import EventData

from rubi import (
    OrderSide, NewMarketOrder, NewLimitOrder, Pair, OrderBook,
    NetworkName,
    Network,
    RubiconMarket, RubiconRouter, ERC20, PairDoesNotExistException, BaseEvent, OrderEvent,
    Transaction, BaseNewOrder, NewCancelOrder, UpdateLimitOrder
)


class Client:

    def __init__(
        self,
        network_name: NetworkName,
        http_node_url: str,
        wallet: Union[ChecksumAddress, str],
        key: str,
        message_queue: Optional[Queue] = None,
    ):
        self.network = Network.build(name=network_name, http_node_url=http_node_url)

        self.wallet = self.network.w3.to_checksum_address(wallet)
        self.key = key

        self.market = RubiconMarket.from_network(network=self.network, wallet=self.wallet, key=key)
        self.router = RubiconRouter.from_network(network=self.network, wallet=self.wallet, key=key)

        self._pairs: Dict[str, Pair] = {}
        self._pair_orderbooks: Dict[str, OrderBook] = {}

        self.message_queue = message_queue

    ######################################################################
    # pair methods
    ######################################################################

    def add_pair(self, pair_name: str, base_asset_allowance: Decimal, quote_asset_allowance: Decimal) -> None:
        base, quote = pair_name.split("/")

        base_asset = ERC20.from_network(name=base, network=self.network, wallet=self.wallet, key=self.key)
        quote_asset = ERC20.from_network(name=quote, network=self.network, wallet=self.wallet, key=self.key)

        current_base_asset_allowance = self._from_erc20_amount(
            amount=base_asset.allowance(owner=self.wallet, spender=self.market.address),
            asset=base_asset
        )
        current_quote_asset_allowance = self._from_erc20_amount(
            amount=quote_asset.allowance(owner=self.wallet, spender=self.market.address),
            asset=quote_asset
        )

        self._pairs[f"{base}/{quote}"] = Pair(
            name=pair_name,
            base_asset=base_asset,
            quote_asset=quote_asset,
            current_base_asset_allowance=current_base_asset_allowance,
            current_quote_asset_allowance=current_quote_asset_allowance
        )

        self.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=base_asset_allowance,
            new_quote_asset_allowance=quote_asset_allowance
        )

    def get_pairs_list(self) -> List[str]:
        return list(self._pairs.keys())

    def update_pair_allowance(
        self,
        pair_name: str,
        new_base_asset_allowance: Decimal,
        new_quote_asset_allowance: Decimal
    ) -> None:
        pair = self.get_pair(pair_name=pair_name)

        if pair.current_base_asset_allowance != new_base_asset_allowance:
            self._update_asset_allowance(
                asset=pair.base_asset,
                spender=self.market.address,
                new_allowance=new_base_asset_allowance
            )
            pair.update_base_asset_allowance(new_base_asset_allowance=new_base_asset_allowance)

        if pair.current_base_asset_allowance != new_quote_asset_allowance:
            self._update_asset_allowance(
                asset=pair.quote_asset,
                spender=self.market.address,
                new_allowance=new_quote_asset_allowance
            )
            pair.update_quote_asset_allowance(new_quote_asset_allowance=new_quote_asset_allowance)

    def get_pair(self, pair_name: str) -> Pair:
        pair = self._pairs[pair_name]

        if pair is None:
            raise PairDoesNotExistException(
                "add pair to the client using the add_pair method before placing orders for the pair"
            )

        return pair

    def remove_pair(self, pair_name: str) -> None:
        self.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=Decimal("0"),
            new_quote_asset_allowance=Decimal("0")
        )

        del self._pairs[pair_name]
        del self._pair_orderbooks[pair_name]

    ######################################################################
    # book methods
    ######################################################################

    def get_orderbook(self, pair_name: str) -> OrderBook:
        pair = self.get_pair(pair_name=pair_name)

        rubicon_book = self.router.get_book_from_pair(asset=pair.base_asset.address, quote=pair.quote_asset.address)

        print(rubicon_book)

        return OrderBook.from_rubicon_book(
            rubicon_book=rubicon_book,
            base_asset=pair.base_asset,
            quote_asset=pair.quote_asset
        )

    def start_orderbook_poller(self, pair_name: str, poll_time: int = 2) -> None:
        if self.message_queue is None:
            raise Exception("orderbook poller is configured to place messages on the message queue. message queue"
                            "cannot be none")

        # Check that pair is defined before starting
        pair = self.get_pair(pair_name=pair_name)

        thread = Thread(
            target=self._start_orderbook_poller,
            args=(pair, poll_time),
            daemon=True
        )
        thread.start()

    def _start_orderbook_poller(self, pair: Pair, poll_time: int = 2) -> None:
        polling: bool = True
        while polling:
            try:
                order_book = self.get_orderbook(pair_name=pair.name)

                self._pair_orderbooks[pair.name] = order_book

                self.message_queue.put(order_book)
            except PairDoesNotExistException:
                log.warning("pair does not exist in client. shutting down orderbook poller")
                polling = False
            except Exception as e:
                log.error(e)
            sleep(poll_time)

    ######################################################################
    # event methods
    ######################################################################

    def start_event_poller(
        self,
        pair_name: str,
        event_type: Type[BaseEvent],
        filters: Optional[Dict[str, Any]] = None,
        event_handler: Optional[Callable] = None,
        poll_time: int = 2
    ) -> None:
        if self.message_queue is None:
            raise Exception("event poller is configured to place messages on the message queue. message queue"
                            "cannot be none")

        pair = self._pairs.get(pair_name)

        argument_filters = event_type.default_filters(
            bid_identifier=pair.bid_identifier,
            ask_identifier=pair.ask_identifier,
            wallet=self.wallet
        ) if filters is None else filters

        event_type.get_event_contract(market=self.market, router=self.router).start_event_poller(
            pair_name=pair_name,
            event_type=event_type,
            argument_filters=argument_filters,
            event_handler=self._default_event_handler if event_handler is None else event_handler,
            poll_time=poll_time
        )

    def _default_event_handler(self, pair_name: str, event_type: Type[BaseEvent], event_data: EventData) -> None:
        raw_event = event_type(block_number=event_data["blockNumber"], **event_data["args"])

        if raw_event.client_filter(wallet=self.wallet):
            pair = self._pairs.get(pair_name)

            order_event = OrderEvent.from_event(pair=pair, event=raw_event, wallet=self.wallet)

            self.message_queue.put(order_event)

    ######################################################################
    # order methods
    ######################################################################
    # TODO: would be cool if these methods could understand how much they are spending on gas (use TxReceipt)
    # also need a way to return the order id for limit orders

    def place_market_order(self, transaction: Transaction) -> str:
        # TODO instantiate best_ask and best_bid properly
        # This will probably require an orderbook to be instantiated
        best_ask = 1
        best_bid = 1

        if len(transaction.orders) > 1:
            raise Exception("call place_order with one order only")

        order: NewMarketOrder = transaction.orders[0]  # noqa

        pair = self.get_pair(pair_name=order.pair)

        match order.order_side:
            case OrderSide.BUY:
                return self.market.buy_all_amount(
                    buy_gem=pair.base_asset.address,
                    buy_amt=self._to_erc20_amount(order.size, pair.base_asset),
                    pay_gem=pair.quote_asset.address,
                    max_fill_amount=self._to_erc20_amount(
                        (1 + order.allowable_slippage) * best_ask, pair.quote_asset
                    ),
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )
            case OrderSide.SELL:
                return self.market.sell_all_amount(
                    pay_gem=pair.base_asset.address,
                    pay_amt=self._to_erc20_amount(order.size, pair.base_asset),
                    buy_gem=pair.quote_asset.address,
                    min_fill_amount=self._to_erc20_amount(
                        (1 - order.allowable_slippage) * best_bid, pair.quote_asset
                    ),
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )

    def place_limit_order(self, transaction: Transaction) -> str:
        if len(transaction.orders) > 1:
            raise Exception("call place_order with one order only")

        order: NewLimitOrder = transaction.orders[0]  # noqa

        pair = self.get_pair(pair_name=order.pair)

        match order.order_side:
            case OrderSide.BUY:
                return self.market.offer(
                    pay_amt=self._to_erc20_amount(order.price * order.size, pair.quote_asset),
                    pay_gem=pair.quote_asset.address,
                    buy_amt=self._to_erc20_amount(order.size, pair.base_asset),
                    buy_gem=pair.base_asset.address,
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )
            case OrderSide.SELL:
                return self.market.offer(
                    pay_amt=self._to_erc20_amount(order.size, pair.base_asset),
                    pay_gem=pair.base_asset.address,
                    buy_amt=self._to_erc20_amount(order.price * order.size, pair.quote_asset),
                    buy_gem=pair.quote_asset.address,
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )

    def cancel_limit_order(self, transaction: Transaction) -> str:
        if len(transaction.orders) > 1:
            raise Exception("call place_order with one order only")

        order: NewCancelOrder = transaction.orders[0]  # noqa

        return self.market.cancel(
            id=order.order_id,
            nonce=transaction.nonce,
            gas=transaction.gas,
            max_fee_per_gas=transaction.max_fee_per_gas,
            max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
        )

    def batch_place_limit_orders(self, transaction: Transaction) -> str:
        pay_amts = []
        pay_gems = []
        buy_amts = []
        buy_gems = []

        for order in transaction.orders:
            order: NewLimitOrder
            pair = self.get_pair(order.pair)

            match order.order_side:
                case OrderSide.BUY:
                    pay_amts.append(self._to_erc20_amount(order.price * order.size, pair.quote_asset))
                    pay_gems.append(pair.quote_asset.address)
                    buy_amts.append(self._to_erc20_amount(order.size, pair.base_asset))
                    buy_gems.append(pair.base_asset.address)
                case OrderSide.SELL:
                    pay_amts.append(self._to_erc20_amount(order.size, pair.base_asset))
                    pay_gems.append(pair.base_asset.address)
                    buy_amts.append(self._to_erc20_amount(order.price * order.size, pair.quote_asset))
                    buy_gems.append(pair.quote_asset.address)

        return self.market.batch_offer(
            pay_amts=pay_amts,
            pay_gems=pay_gems,
            buy_amts=buy_amts,
            buy_gems=buy_gems,
            nonce=transaction.nonce,
            gas=transaction.gas,
            max_fee_per_gas=transaction.max_fee_per_gas,
            max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
        )

    def batch_update_limit_orders(self, transaction: Transaction) -> str:
        order_ids = []
        pay_amts = []
        pay_gems = []
        buy_amts = []
        buy_gems = []

        for order in transaction.orders:
            order: UpdateLimitOrder
            pair = self.get_pair(order.pair)

            order_ids.append(order.order_id)

            match order.order_side:
                case OrderSide.BUY:
                    pay_amts.append(self._to_erc20_amount(order.price * order.size, pair.quote_asset))
                    pay_gems.append(pair.quote_asset.address)
                    buy_amts.append(self._to_erc20_amount(order.size, pair.base_asset))
                    buy_gems.append(pair.base_asset.address)
                case OrderSide.SELL:
                    pay_amts.append(self._to_erc20_amount(order.size, pair.base_asset))
                    pay_gems.append(pair.base_asset.address)
                    buy_amts.append(self._to_erc20_amount(order.price * order.size, pair.quote_asset))
                    buy_gems.append(pair.quote_asset.address)

        return self.market.batch_offer(
            pay_amts=pay_amts,
            pay_gems=pay_gems,
            buy_amts=buy_amts,
            buy_gems=buy_gems,
            nonce=transaction.nonce,
            gas=transaction.gas,
            max_fee_per_gas=transaction.max_fee_per_gas,
            max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
        )

    def batch_cancel_limit_orders(self, transaction: Transaction) -> str:
        order_ids = []

        for order in transaction.orders:
            order: NewCancelOrder

            order_ids.append(order.order_id)

        return self.market.batch_cancel(
            ids=order_ids,
            nonce=transaction.nonce,
            gas=transaction.gas,
            max_fee_per_gas=transaction.max_fee_per_gas,
            max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
        )

    ######################################################################
    # helper methods
    ######################################################################

    # TODO: revisit as the safer thing is to set approval to 0 and then set approval to new_allowance
    # or use increaseAllowance and decreaseAllowance but the current abi does not support these methods
    # See: https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    def _update_asset_allowance(
        self,
        asset: ERC20,
        spender: ChecksumAddress,
        new_allowance: Decimal
    ) -> None:
        log.info(
            asset.approve(
                spender=spender,
                amount=self._to_erc20_amount(amount=new_allowance, asset=asset)
            )
        )

    # TODO: implement this and use check transactions before they go through to prevent failure
    @staticmethod
    def _check_allowance(pair: Pair, order: BaseNewOrder):
        pass

    @staticmethod
    def _to_erc20_amount(amount: Decimal, asset: ERC20) -> int:
        return math.floor(amount * 10 ** asset.decimal)

    @staticmethod
    def _from_erc20_amount(amount: int, asset: ERC20) -> Decimal:
        return Decimal(amount) / Decimal(10 ** asset.decimal)
