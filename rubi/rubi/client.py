import logging as log
from _decimal import Decimal
from multiprocessing import Queue
from threading import Thread
from time import sleep
from typing import Union, List, Optional, Dict, Type, Any, Callable

from eth_typing import ChecksumAddress
from web3.types import EventData

from rubi.contracts import (
    RubiconMarket,
    RubiconRouter,
    ERC20,
)
from rubi.network import (
    Network,
)
from rubi.types import (
    OrderSide,
    NewMarketOrder,
    NewLimitOrder,
    Pair,
    OrderBook,
    PairDoesNotExistException,
    BaseEvent,
    OrderEvent,
    Transaction,
    BaseNewOrder,
    NewCancelOrder,
    UpdateLimitOrder
)


class Client:
    """This class is a client for Rubicon. It aims to provide a simple and understandable interface when interacting
    with the Rubicon protocol. If not instantiated with a wallet and key then all the methods that require signing
    will throw an error.

    :param network: A Network instance
    :type network: Network
    :param message_queue: Optional message queue for processing events (optional, default is None).
    :type message_queue: Optional[Queue]
    :param wallet: Wallet address (optional, default is None).
    :type wallet: Optional[ChecksumAddress]
    :param key: Key for the wallet (optional, default is None).
    :type key: Optional[str]
    """

    def __init__(
        self,
        network: Network,
        message_queue: Optional[Queue] = None,
        wallet: Optional[Union[ChecksumAddress, str]] = None,
        key: Optional[str] = None,
    ):
        """constructor method."""
        self.network = network

        self.wallet = self.network.w3.to_checksum_address(wallet) if wallet else wallet  # type: ChecksumAddress |  None
        self.key = key  # type: str |  None

        self.market = RubiconMarket.from_network(network=self.network, wallet=self.wallet, key=self.key)
        self.router = RubiconRouter.from_network(network=self.network, wallet=self.wallet, key=self.key)

        self._pairs: Dict[str, Pair] = {}
        self._pair_orderbooks: Dict[str, OrderBook] = {}

        self.message_queue = message_queue  # type: Queue | None

    @classmethod
    def from_http_node_url(
        cls,
        http_node_url: str,
        custom_token_addresses_file: Optional[str] = None,
        message_queue: Optional[Queue] = None,
        wallet: Optional[Union[ChecksumAddress, str]] = None,
        key: Optional[str] = None,
    ):
        """Initialize a Client using a http_node_url.

        :param http_node_url: URL of the HTTP node.
        :type http_node_url: str
        :param custom_token_addresses_file: The name of a yaml file (relative to the current working directory) with
            custom token addresses. Overwrites the token config found in network_config/{chain}/network.yaml.
            (optional, default is None).
        :type custom_token_addresses_file: Optional[str]
        :param message_queue: Optional message queue for processing events (optional, default is None).
        :type message_queue: Optional[Queue]
        :param wallet: Wallet address (optional, default is None).
        :type wallet: Optional[Union[ChecksumAddress, str]]
        :param key: Key for the wallet (optional, default is None).
        :type key: str
        """
        network = Network.from_config(
            http_node_url=http_node_url,
            custom_token_addresses_file=custom_token_addresses_file
        )

        return cls(
            network=network,
            message_queue=message_queue,
            wallet=wallet,
            key=key
        )

    ######################################################################
    # pair methods
    ######################################################################

    def add_pair(
        self, pair_name: str,
        base_asset_allowance: Optional[Decimal] = None,
        quote_asset_allowance: Optional[Decimal] = None
    ) -> None:
        """Add a Pair to the Client. This method creates a Pair instance and adds it to the Client's internal
        _pairs dictionary. Additionally, this method updates the spender allowance of the Rubicon Market for both
        base asset and the quote asset.

        :param pair_name: Name of the Pair in the format "<base_asset>/<quote_asset>".
        :type pair_name: str
        :param base_asset_allowance: Allowance for the base asset (optional, default is None).
        :type base_asset_allowance: Optional[Decimal]
        :param quote_asset_allowance: Allowance for the quote asset (optional, default is None).
        :type quote_asset_allowance: Optional[Decimal]
        """

        base, quote = pair_name.split("/")

        base_asset = ERC20.from_network(name=base, network=self.network, wallet=self.wallet, key=self.key)
        quote_asset = ERC20.from_network(name=quote, network=self.network, wallet=self.wallet, key=self.key)

        current_base_asset_allowance = base_asset.to_decimal(
            number=base_asset.allowance(owner=self.wallet, spender=self.market.address)
        )
        current_quote_asset_allowance = quote_asset.to_decimal(
            number=quote_asset.allowance(owner=self.wallet, spender=self.market.address)
        )

        if current_base_asset_allowance == Decimal("0") or current_quote_asset_allowance == Decimal("0"):
            log.warning("allowance for base or quote asset is zero. this may cause issues when placing orders")

        self._pairs[f"{base}/{quote}"] = Pair(
            name=pair_name,
            base_asset=base_asset,
            quote_asset=quote_asset,
            current_base_asset_allowance=current_base_asset_allowance,
            current_quote_asset_allowance=current_quote_asset_allowance
        )

        # only edit allowance if client has signing rights
        if self.wallet is not None and self.key is not None:
            self.update_pair_allowance(
                pair_name=pair_name,
                new_base_asset_allowance=base_asset_allowance,
                new_quote_asset_allowance=quote_asset_allowance
            )

    def get_pairs_list(self) -> List[str]:
        """Get a list of all pair names in the clients internal _pairs dictionary.

        :return: List of pair names.
        :rtype: List[str]
        """
        return list(self._pairs.keys())

    def update_pair_allowance(
        self,
        pair_name: str,
        new_base_asset_allowance: Optional[Decimal] = None,
        new_quote_asset_allowance: Optional[Decimal] = None
    ) -> None:
        """Update the allowance for the base and quote assets of a pair if the current allowance is different from the
        new allowance. This method also updates the Pair data structure so that the allowance can be read without having
        to do a call to the chain.

        :param pair_name: Name of the pair.
        :type pair_name: str
        :param new_base_asset_allowance: New allowance for the base asset. (optional, default is None).
        :type new_base_asset_allowance: Optional[Decimal]
        :param new_quote_asset_allowance: New allowance for the quote asset. (optional, default is None).
        :type new_quote_asset_allowance: Optional[Decimal]
        :raises PairDoesNotExistException: If the pair does not exist in the clients internal _pairs dict.
        """
        pair = self.get_pair(pair_name=pair_name)

        if new_base_asset_allowance and pair.current_base_asset_allowance != new_base_asset_allowance:
            self._update_asset_allowance(
                asset=pair.base_asset,
                spender=self.market.address,
                new_allowance=new_base_asset_allowance
            )
            pair.update_base_asset_allowance(new_base_asset_allowance=new_base_asset_allowance)

        if new_quote_asset_allowance and pair.current_base_asset_allowance != new_quote_asset_allowance:
            self._update_asset_allowance(
                asset=pair.quote_asset,
                spender=self.market.address,
                new_allowance=new_quote_asset_allowance
            )
            pair.update_quote_asset_allowance(new_quote_asset_allowance=new_quote_asset_allowance)

    def get_pair(self, pair_name: str) -> Pair:
        """Retrieves the Pair object associated with the specified pair name. If the pair does not exist
        in the client, it raises a PairDoesNotExistException.

        :param pair_name: Name of the pair.
        :type pair_name: str
        :return: The Pair object.
        :rtype: Pair
        :raises PairDoesNotExistException: If the pair does not exist in the client.
        """
        pair = self._pairs.get(pair_name)

        if pair is None:
            raise PairDoesNotExistException(
                "add pair to the client using the add_pair method before placing orders for the pair"
            )

        return pair

    def remove_pair(self, pair_name: str) -> None:
        """Removes a pair from the client. It updates the pair's asset allowances
        to zero and deletes the pair and its corresponding order book from the client.

        :param pair_name: Name of the pair to remove.
        :type pair_name: str
        :raises PairDoesNotExistException: If the pair does not exist in the client before removal.
        """
        self.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=Decimal("0"),
            new_quote_asset_allowance=Decimal("0")
        )

        del self._pairs[pair_name]
        if self._pair_orderbooks.get(pair_name):
            del self._pair_orderbooks[pair_name]

    ######################################################################
    # orderbook methods
    ######################################################################

    def get_orderbook(self, pair_name: str) -> OrderBook:
        """Retrieve the order book for a specific pair from the Rubicon Router.

        :param pair_name: Name of the pair to retrieve the order book for.
        :type pair_name: str
        :return: The order book for the specified pair.
        :rtype: OrderBook
        :raises PairDoesNotExistException: If the pair does not exist in the client.
        """
        pair = self.get_pair(pair_name=pair_name)

        rubicon_offer_book = self.router.get_book_from_pair(
            asset=pair.base_asset.address,
            quote=pair.quote_asset.address
        )

        return OrderBook.from_rubicon_offer_book(
            offer_book=rubicon_offer_book,
            base_asset=pair.base_asset,
            quote_asset=pair.quote_asset
        )

    def start_orderbook_poller(self, pair_name: str, poll_time: int = 2) -> None:
        """Starts a background thread that continuously polls the order book for the specified pair
        at a specified polling interval. The retrieved order book is added to the message queue of the client.
        The poller will run until the pair is removed from the client.

        :param pair_name: Name of the pair to start the order book poller for.
        :type pair_name: str
        :param poll_time: Polling interval in seconds, defaults to 2 seconds.
        :type poll_time: int, optional
        :raises Exception: If the message queue is not configured.
        :raises PairDoesNotExistException: If the pair does not exist in the client.
        """

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

    # TODO: ideally this should use the RubiconMarket events to update itself instead of repeatedly polling the
    #  get_orderbook method. But it's fine for now.
    def _start_orderbook_poller(self, pair: Pair, poll_time: int = 2) -> None:
        """The internal implementation of the order book poller. It continuously retrieves the order book
        for the specified pair and adds it to the pair order books dictionary and the message queue of the client. The
        poller will run until the pair is removed from the client.

        :param pair: The pair to start the order book poller for.
        :type pair: Pair
        :param poll_time: Polling interval in seconds, defaults to 2 seconds.
        :type poll_time: int, optional
        """
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
        """Starts a background event poller that continuously listens for events of the specified event type
        related to the specified pair. The retrieved events are processed by the event handler and added to the message
        queue of the client. The poller will run until the pair is removed from the client.

        :param pair_name: Name of the pair to start the event poller for.
        :type pair_name: str
        :param event_type: Type of the event to listen for.
        :type event_type: Type[BaseEvent]
        :param filters: Optional filters to apply when retrieving events, defaults to the events default filters
            (optional, default is None).
        :type filters: Optional[Dict[str, Any]], optional
        :param event_handler: Optional event handler function to process the retrieved events, defaults to the
            self._default_event_handler (optional, default is None).
        :type event_handler: Optional[Callable], optional
        :param poll_time: Polling interval in seconds, defaults to 2 seconds.
        :type poll_time: int, optional
        :raises Exception: If the message queue is not configured.
        :raises PairDoesNotExistException: If the pair does not exist in the client.
        """
        if self.message_queue is None:
            raise Exception("event poller is configured to place messages on the message queue. message queue"
                            "cannot be none")

        pair = self.get_pair(pair_name)

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
        """The default event handler function used by the event poller. It processes the retrieved events
        and adds the corresponding order events to the message queue of the client.

        :param pair_name: Name of the pair associated with the event.
        :type pair_name: str
        :param event_type: Type of the event.
        :type event_type: Type[BaseEvent]
        :param event_data: Data of the retrieved event.
        :type event_data: EventData
        """
        raw_event = event_type(block_number=event_data["blockNumber"], **event_data["args"])

        if raw_event.client_filter(wallet=self.wallet):
            pair = self._pairs.get(pair_name)

            order_event = OrderEvent.from_event(pair=pair, event=raw_event, wallet=self.wallet)

            self.message_queue.put(order_event)

    ######################################################################
    # order methods
    ######################################################################
    # TODO: would be cool if these methods could understand how much they are spending on gas (use TxReceipt)
    #  also need a way to return the order id for limit orders
    #  we could listen for the event and return the order id along with relevant gas spend information 
    #  one thing we will need to be conscious of and figure out how to handle is the fact that gas is calculated in a
    #  variety of ways depending upon the chain

    def place_market_order(self, transaction: Transaction) -> str:
        """Place a market order transaction by executing the specified transaction object. The transaction
        object should contain a single order of type NewMarketOrder. The order is retrieved from the transaction and
        the corresponding market buy or sell method is called based on the order side.

        :param transaction: Transaction object containing the market order.
        :type transaction: Transaction
        :return: The transaction hash of the executed market order.
        :rtype: str
        :raises Exception: If the transaction contains more than one order.
        """
        if len(transaction.orders) > 1:
            raise Exception("call place_order with one order only")

        order: NewMarketOrder = transaction.orders[0]  # noqa

        pair = self.get_pair(pair_name=order.pair)

        match order.order_side:
            case OrderSide.BUY:
                return self.market.buy_all_amount(
                    buy_gem=pair.base_asset.address,
                    buy_amt=pair.base_asset.to_integer(order.size),
                    pay_gem=pair.quote_asset.address,
                    max_fill_amount=pair.quote_asset.to_integer(order.worst_execution_price),
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )
            case OrderSide.SELL:
                return self.market.sell_all_amount(
                    pay_gem=pair.base_asset.address,
                    pay_amt=pair.base_asset.to_integer(order.size),
                    buy_gem=pair.quote_asset.address,
                    min_fill_amount=pair.quote_asset.to_integer(order.worst_execution_price),
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )

    def place_limit_order(self, transaction: Transaction) -> str:
        """Place a limit order transaction by executing the specified transaction object. The transaction object should
        contain a single order of type NewLimitOrder.

        :param transaction: Transaction object containing the limit order.
        :type transaction: Transaction
        :return: The transaction hash of the executed limit order.
        :rtype: str
        :raises Exception: If the transaction contains more than one order.
        """
        if len(transaction.orders) > 1:
            raise Exception("call place_order with one order only")

        order: NewLimitOrder = transaction.orders[0]  # noqa

        pair = self.get_pair(pair_name=order.pair)

        match order.order_side:
            case OrderSide.BUY:
                return self.market.offer(
                    pay_amt=pair.quote_asset.to_integer(order.price * order.size),
                    pay_gem=pair.quote_asset.address,
                    buy_amt=pair.base_asset.to_integer(order.size),
                    buy_gem=pair.base_asset.address,
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )
            case OrderSide.SELL:
                return self.market.offer(
                    pay_amt=pair.base_asset.to_integer(order.size),
                    pay_gem=pair.base_asset.address,
                    buy_amt=pair.quote_asset.to_integer(order.price * order.size),
                    buy_gem=pair.quote_asset.address,
                    nonce=transaction.nonce,
                    gas=transaction.gas,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    max_priority_fee_per_gas=transaction.max_priority_fee_per_gas
                )

    def cancel_limit_order(self, transaction: Transaction) -> str:
        """Place a limit order cancel transaction by executing the specified transaction object. The transaction object
        should contain a single order of type NewCancelOrder.

        :param transaction: Transaction object containing the cancel order.
        :type transaction: Transaction
        :return: The transaction hash of the executed cancel order.
        :rtype: str
        :raises Exception: If the transaction contains more than one order.
        """
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
        """Place multiple limit orders in a batch transaction.

        :param transaction: Transaction object containing multiple limit orders.
        :type transaction: Transaction
        :return: The transaction hash of the executed batch limit orders.
        :rtype: str
        """
        pay_amts = []
        pay_gems = []
        buy_amts = []
        buy_gems = []

        for order in transaction.orders:
            order: NewLimitOrder
            pair = self.get_pair(order.pair)

            match order.order_side:
                case OrderSide.BUY:
                    pay_amts.append(pair.quote_asset.to_integer(order.price * order.size))
                    pay_gems.append(pair.quote_asset.address)
                    buy_amts.append(pair.base_asset.to_integer(order.size))
                    buy_gems.append(pair.base_asset.address)
                case OrderSide.SELL:
                    pay_amts.append(pair.base_asset.to_integer(order.size))
                    pay_gems.append(pair.base_asset.address)
                    buy_amts.append(pair.quote_asset.to_integer(order.price * order.size))
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
        """Update multiple limit orders in a batch transaction.

        :param transaction: Transaction object containing multiple limit order updates.
        :type transaction: Transaction
        :return: The transaction hash of the executed batch limit order updates.
        :rtype: str
        """
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
                    pay_amts.append(pair.quote_asset.to_integer(order.price * order.size))
                    pay_gems.append(pair.quote_asset.address)
                    buy_amts.append(pair.base_asset.to_integer(order.size))
                    buy_gems.append(pair.base_asset.address)
                case OrderSide.SELL:
                    pay_amts.append(pair.base_asset.to_integer(order.size))
                    pay_gems.append(pair.base_asset.address)
                    buy_amts.append(pair.quote_asset.to_integer(order.price * order.size))
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
        """Cancel multiple limit orders in a batch transaction.

        :param transaction: Transaction object containing multiple limit order cancellations.
        :type transaction: Transaction
        :return: The transaction hash of the executed batch limit order cancellations.
        :rtype: str
        """
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
    #  or use increaseAllowance and decreaseAllowance but the current abi does not support these methods
    #  See: https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    @staticmethod
    def _update_asset_allowance(
        asset: ERC20,
        spender: ChecksumAddress,
        new_allowance: Decimal
    ) -> None:
        log.info(
            asset.approve(
                spender=spender,
                amount=asset.to_integer(number=new_allowance)
            )
        )

    # TODO: implement this and use check transactions before they go through to prevent failure
    @staticmethod
    def _check_allowance(pair: Pair, order: BaseNewOrder):
        pass
