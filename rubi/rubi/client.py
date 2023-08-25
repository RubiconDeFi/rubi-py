import logging
from _decimal import Decimal
from multiprocessing import Queue
from threading import Thread
from time import sleep
from typing import Union, List, Optional, Dict, Type, Any, Callable, Tuple

import pandas as pd
from eth_typing import ChecksumAddress
from web3.types import EventData, Nonce, TxParams

from rubi import LimitOrder
from rubi.contracts import (
    ERC20,
    TransactionReceipt,
    EmitFeeEvent,
    EmitOfferEvent,
    EmitTakeEvent,
    EmitCancelEvent,
    EmitApproval,
    EmitTransfer,
)
from rubi.data import MarketData, SubgraphOffer
from rubi.network import (
    Network,
)
from rubi.rubicon_types import (
    OrderSide,
    NewMarketOrder,
    NewLimitOrder,
    OrderBook,
    BaseEvent,
    FeeEvent,
    OrderEvent,
    NewCancelOrder,
    UpdateLimitOrder,
    Approval,
    RubiconMarketApproval,
    RubiconRouterApproval,
    Transfer,
    ApprovalEvent,
    TransferEvent,
)

logger = logging.getLogger(__name__)


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

        self.message_queue = message_queue  # type: Queue | None

        # Authentication
        self.wallet = (
            self.network.w3.to_checksum_address(wallet) if wallet else wallet
        )  # type: ChecksumAddress |  None
        self._key = key  # type: str |  None

        self.market_data = MarketData.from_network(network=network)

    @classmethod
    def from_http_node_url(
        cls,
        http_node_url: str,
        message_queue: Optional[Queue] = None,
        wallet: Optional[Union[ChecksumAddress, str]] = None,
        key: Optional[str] = None,
        custom_token_addresses_file: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a Client using a http_node_url.

        :param http_node_url: URL of the HTTP node.
        :type http_node_url: str
        :param message_queue: Optional message queue for processing events (optional, default is None).
        :type message_queue: Optional[Queue]
        :param wallet: Wallet address (optional, default is None).
        :type wallet: Optional[Union[ChecksumAddress, str]]
        :param key: Key for the wallet (optional, default is None).
        :type key: str
        :param custom_token_addresses_file: The name of a yaml file (relative to the current working directory) with
            custom token addresses. Overwrites the token config found in network_config/{chain}/network.yaml.
            (optional, default is None).
        :type custom_token_addresses_file: Optional[str]
        """
        network = Network.from_http_node_url(
            http_node_url=http_node_url,
            custom_token_addresses_file=custom_token_addresses_file,
        )

        return cls(
            network=network,
            message_queue=message_queue,
            wallet=wallet,
            key=key,
        )

    ######################################################################
    # transaction methods
    ######################################################################

    def get_nonce(self) -> Nonce:
        """Get the current transaction count of the wallet to determine the nonce

        :return: The current nonce of the wallet
        :rtype: Nonce
        """
        return self.network.w3.eth.get_transaction_count(self.wallet)

    def get_transaction_receipt(
        self,
        transaction_hash: str,
        pair_names: Optional[List[str]] = None,
    ) -> TransactionReceipt:
        """Get the transaction receipt for a given transaction hash.

        :param transaction_hash: The transaction hash.
        :type transaction_hash: str
        :param pair_names: If handling a transaction that interacted with the rubicon market we can decode events into
            human-readable format if we know the pairs in the transaction. (defaults to None and no decoding is done)
        :type pair_names: Optional[List[str]]
        :return: A TransactionReceipt for the transaction hash.
        :rtype: TransactionReceipt
        :return:
        """

        transaction_receipt = self.network.transaction_handler.get_transaction_receipt(
            transaction_hash=transaction_hash,
        )

        return self._handle_transaction_receipt_raw_events(
            transaction_receipt=transaction_receipt,
            pair_names=pair_names,
        )

    def execute_transaction(self, transaction: TxParams) -> TransactionReceipt:
        """Execute the passed transaction.

        :param transaction: The transaction hash.
        :type transaction: TxParams
        :return: A TransactionReceipt of the executed transaction.
        :rtype: TransactionReceipt
        :return:
        """
        pair_names = transaction["pair_names"] if "pair_names" in transaction else None

        transaction_receipt = self.network.transaction_handler.execute_transaction(
            transaction=transaction, key=self._key
        )

        processed_transaction_receipt = self._handle_transaction_receipt_raw_events(
            transaction_receipt=transaction_receipt,
            pair_names=pair_names,
        )

        return processed_transaction_receipt

    ######################################################################
    # token methods
    ######################################################################

    def get_balance(
        self, token: str, wallet: Optional[ChecksumAddress] = None
    ) -> Decimal:
        """Get balance of a token.

        :param token: The token to get the balance of
        :type token: str
        :param wallet: The wallet balance to check (Optional, defaults to client wallet)
        :type wallet: ChecksumAddress
        :return: The token balance of the wallet
        :rtype: Decimal
        """
        if not wallet:
            wallet = self.wallet

        balance = self.network.tokens[token].balance_of(account=wallet)

        return self.network.tokens[token].to_decimal(balance)

    def get_allowance(self, token: str, spender: ChecksumAddress) -> Decimal:
        """Get a spenders allowance for a certain token.

        :param token: The token to check the allowance of
        :type token: str
        :param spender: The spender address
        :type spender: ChecksumAddress
        :return: The allowance of the spender
        :rtype: Decimal
        """

        allowance = self.network.tokens[token].allowance(
            owner=self.wallet, spender=spender
        )

        return self.network.tokens[token].to_decimal(allowance)

    # TODO: revisit as the safer thing is to set approval to 0 and then set approval to new_allowance
    #  or use increaseAllowance and decreaseAllowance but the current abi does not support these methods
    #  See: https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    def approve(
        self,
        approval: Approval,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """
        Construct an approval transaction.

        :param approval: The approval of a spender of an ERC20
        :type approval: Approval | RubiconMarketApproval | RubiconRouterApproval
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The built transaction.
        :rtype: TxParams
        """
        amount = self.network.tokens[approval.token].to_integer(approval.amount)
        spender = approval.spender

        if isinstance(approval, RubiconMarketApproval):
            spender = self.network.rubicon_market.address
        elif isinstance(approval, RubiconRouterApproval):
            spender = self.network.rubicon_router.address
        elif spender is None:
            raise Exception("A spender must be provided for an approval")

        return self.network.tokens[approval.token].approve(
            spender=spender,
            amount=amount,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    def transfer(
        self,
        transfer: Transfer,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """
        Construct a transfer transaction.

        :param transfer: The transfer of an ERC20 to a certain address
        :type transfer: Transfer
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The built transaction.
        :rtype: TxParams
        """
        amount = self.network.tokens[transfer.token].to_integer(transfer.amount)

        return self.network.tokens[transfer.token].transfer(
            recipient=transfer.recipient,
            amount=amount,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

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
        base_asset, quote_asset = pair_name.split("/")

        rubicon_offer_book = self.network.rubicon_router.get_book_from_pair(
            asset=self.network.tokens[base_asset].address,
            quote=self.network.tokens[quote_asset].address,
        )

        return OrderBook.from_rubicon_offer_book(
            offer_book=rubicon_offer_book,
            base_asset=self.network.tokens[base_asset],
            quote_asset=self.network.tokens[quote_asset],
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
            raise Exception(
                "Orderbook poller is configured to place messages on the message queue. Message queue cannot be none"
            )

        base_asset, quote_asset = pair_name.split("/")
        if (
            base_asset not in self.network.tokens.keys()
            or quote_asset not in self.network.tokens.keys()
        ):
            raise Exception(
                f"Cannot start orderbook poller for {base_asset}/{quote_asset} as these assets are not in"
                f"the clients token set: {self.network.tokens.keys()}"
            )

        thread = Thread(
            target=self._start_orderbook_poller,
            kwargs={"pair_name": pair_name, "poll_time": poll_time},
            daemon=True,
        )
        thread.start()

    # TODO: look at using a listener instead of poller (we will probably need to listen to events)
    def _start_orderbook_poller(self, pair_name: str, poll_time: int = 2) -> None:
        """The internal implementation of the order book poller. It continuously retrieves the order book for the
        specified pair and adds it to the message queue of the client.

        :param pair_name: Name of the pair to start the order book poller for.
        :type pair_name: str
        :param poll_time: Polling interval in seconds, defaults to 2 seconds.
        :type poll_time: int, optional
        """
        polling: bool = True
        while polling:
            try:
                self.message_queue.put(self.get_orderbook(pair_name=pair_name))
            except Exception as e:
                logger.error(e)
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
        poll_time: int = 2,
    ) -> None:
        """Starts a background event poller that continuously listens for events of the specified event type
        related to the specified pair. The retrieved events are processed by the event handler and added to the message
        queue of the client. The poller will run until the pair is removed from the client.

        :param pair_name: Name of the pair to start the event poller for.
        :type pair_name: str
        :param event_type: Type of the event to listen for.
        :type event_type: Type[BaseEvent]
        :param filters: Optional filters to apply when retrieving events, defaults to the events default filters
            (optional, default is None). These are added to the default filters for the event
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
            raise Exception(
                "Event poller is configured to place messages on the message queue. Message queue"
                "cannot be none."
            )

        base_asset, quote_asset = pair_name.split("/")

        bid_identifier = self.network.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[
                self.network.tokens[quote_asset].address,
                self.network.tokens[base_asset].address,
            ],
        ).hex()
        ask_identifier = self.network.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[
                self.network.tokens[base_asset].address,
                self.network.tokens[quote_asset].address,
            ],
        ).hex()

        argument_filters = event_type.default_filters(
            bid_identifier=bid_identifier, ask_identifier=ask_identifier
        )

        if filters is not None:
            # TODO: add check that filters are valid, if i remember correctly i think we can only filter on indexed
            #  params. i bet there is a function to check this
            argument_filters.update(filters)

        event_type.get_event_contract(
            market=self.network.rubicon_market, router=self.network.rubicon_router
        ).start_event_poller(
            pair_name=pair_name,
            event_type=event_type,
            argument_filters=argument_filters,
            event_handler=self._default_event_handler
            if event_handler is None
            else event_handler,
            poll_time=poll_time,
        )

    def _default_event_handler(
        self, pair_name: str, event_type: Type[BaseEvent], event_data: EventData
    ) -> None:
        """The default event handler function used by the event poller. It processes the retrieved events
        and adds the corresponding order events to the message queue of the client.

        :param pair_name: Name of the pair associated with the event.
        :type pair_name: str
        :param event_type: Type of the event.
        :type event_type: Type[BaseEvent]
        :param event_data: Data of the retrieved event.
        :type event_data: EventData
        """
        raw_event = event_type(
            block_number=event_data["blockNumber"], **event_data["args"]
        )

        if raw_event.client_filter(wallet=self.wallet):
            if isinstance(raw_event, EmitFeeEvent):
                asset = self.network.tokens[raw_event.asset]

                event = FeeEvent.from_event(
                    pair_name=pair_name, asset=asset, event=raw_event
                )
            else:
                base_asset, quote_asset = pair_name.split("/")

                event = OrderEvent.from_event(
                    base_asset=self.network.tokens[base_asset],
                    quote_asset=self.network.tokens[quote_asset],
                    event=raw_event,
                    wallet=self.wallet,
                )

            self.message_queue.put(event)

    ######################################################################
    # order methods
    ######################################################################

    def market_order(
        self,
        order: NewMarketOrder,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a new market order transaction. The corresponding market buy or sell method is called based on the
        order side.

        :param order: The market order to place.
        :type order: NewMarketOrder
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction to execute the market order.
        :rtype: TxParams
        """
        base_asset, quote_asset = order.pair_name.split("/")

        match order.order_side:
            case OrderSide.BUY:
                transaction = self.network.rubicon_market.buy_all_amount(
                    buy_gem=self.network.tokens[base_asset].address,
                    buy_amt=self.network.tokens[base_asset].to_integer(order.size),
                    pay_gem=self.network.tokens[quote_asset].address,
                    max_fill_amount=self.network.tokens[quote_asset].to_integer(
                        order.worst_execution_price * order.size
                    ),
                    wallet=self.wallet,
                    nonce=nonce,
                    gas=gas,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                )
            case OrderSide.SELL:
                transaction = self.network.rubicon_market.sell_all_amount(
                    pay_gem=self.network.tokens[base_asset].address,
                    pay_amt=self.network.tokens[base_asset].to_integer(order.size),
                    buy_gem=self.network.tokens[quote_asset].address,
                    min_fill_amount=self.network.tokens[quote_asset].to_integer(
                        order.worst_execution_price * order.size
                    ),
                    wallet=self.wallet,
                    nonce=nonce,
                    gas=gas,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                )
            case _:
                raise Exception("OrderSide must be BUY or SELL")

        transaction["pair_names"] = [order.pair_name]

        return transaction

    def limit_order(
        self,
        order: NewLimitOrder,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a new limit order transaction.

        :param order: The limit order to place.
        :type order: NewLimitOrder
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction to execute the limit order.
        :rtype: TxParams
        """
        base_asset, quote_asset = order.pair_name.split("/")

        match order.order_side:
            case OrderSide.BUY:
                transaction = self.network.rubicon_market.offer(
                    pay_amt=self.network.tokens[quote_asset].to_integer(
                        order.price * order.size
                    ),
                    pay_gem=self.network.tokens[quote_asset].address,
                    buy_amt=self.network.tokens[base_asset].to_integer(order.size),
                    buy_gem=self.network.tokens[base_asset].address,
                    wallet=self.wallet,
                    nonce=nonce,
                    gas=gas,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                )
            case OrderSide.SELL:
                transaction = self.network.rubicon_market.offer(
                    pay_amt=self.network.tokens[base_asset].to_integer(order.size),
                    pay_gem=self.network.tokens[base_asset].address,
                    buy_amt=self.network.tokens[quote_asset].to_integer(
                        order.price * order.size
                    ),
                    buy_gem=self.network.tokens[quote_asset].address,
                    wallet=self.wallet,
                    nonce=nonce,
                    gas=gas,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                )
            case _:
                raise Exception("OrderSide must be BUY or SELL")

        transaction["pair_names"] = [order.pair_name]

        return transaction

    def cancel_limit_order(
        self,
        order: NewCancelOrder,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a new limit order cancellation.

        :param order: The cancel order object.
        :type order: NewCancelOrder
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction to execute the limit order cancellation.
        :rtype: TxParams
        """
        transaction = self.network.rubicon_market.cancel(
            id=order.order_id,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        transaction["pair_names"] = [order.pair_name]

        return transaction

    def batch_limit_orders(
        self,
        orders: List[NewLimitOrder],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a transaction to place multiple limit orders in a batch.

        :param orders: The new limits orders to place.
        :type orders: List[NewLimitOrder]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: Transaction to execute the limit order batch.
        :rtype: TxParams
        """
        pay_amts = []
        pay_gems = []
        buy_amts = []
        buy_gems = []

        pair_names: List[str] = []
        for order in orders:
            base_asset, quote_asset = order.pair_name.split("/")
            pair_names.append(order.pair_name)

            match order.order_side:
                case OrderSide.BUY:
                    pay_amts.append(
                        self.network.tokens[quote_asset].to_integer(
                            order.price * order.size
                        )
                    )
                    pay_gems.append(self.network.tokens[quote_asset].address)
                    buy_amts.append(
                        self.network.tokens[base_asset].to_integer(order.size)
                    )
                    buy_gems.append(self.network.tokens[base_asset].address)
                case OrderSide.SELL:
                    pay_amts.append(
                        self.network.tokens[base_asset].to_integer(order.size)
                    )
                    pay_gems.append(self.network.tokens[base_asset].address)
                    buy_amts.append(
                        self.network.tokens[quote_asset].to_integer(
                            order.price * order.size
                        )
                    )
                    buy_gems.append(self.network.tokens[quote_asset].address)

        transaction = self.network.rubicon_market.batch_offer(
            pay_amts=pay_amts,
            pay_gems=pay_gems,
            buy_amts=buy_amts,
            buy_gems=buy_gems,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        if transaction:
            transaction["pair_names"] = pair_names

        return transaction

    def batch_update_limit_orders(
        self,
        orders: List[UpdateLimitOrder],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a transaction to update multiple limit orders in a batch.

        :param orders: The new limits orders to place.
        :type orders: List[NewLimitOrder]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction to execute the update limit order batch.
        :rtype: TxParams
        """
        order_ids = []
        pay_amts = []
        pay_gems = []
        buy_amts = []
        buy_gems = []

        pair_names: List[str] = []
        for order in orders:
            base_asset, quote_asset = order.pair_name.split("/")
            pair_names.append(order.pair_name)

            order_ids.append(order.order_id)

            match order.order_side:
                case OrderSide.BUY:
                    pay_amts.append(
                        self.network.tokens[quote_asset].to_integer(
                            order.price * order.size
                        )
                    )
                    pay_gems.append(self.network.tokens[quote_asset].address)
                    buy_amts.append(
                        self.network.tokens[base_asset].to_integer(order.size)
                    )
                    buy_gems.append(self.network.tokens[base_asset].address)
                case OrderSide.SELL:
                    pay_amts.append(
                        self.network.tokens[base_asset].to_integer(order.size)
                    )
                    pay_gems.append(self.network.tokens[base_asset].address)
                    buy_amts.append(
                        self.network.tokens[quote_asset].to_integer(
                            order.price * order.size
                        )
                    )
                    buy_gems.append(self.network.tokens[quote_asset].address)

        transaction = self.network.rubicon_market.batch_requote(
            ids=order_ids,
            pay_amts=pay_amts,
            pay_gems=pay_gems,
            buy_amts=buy_amts,
            buy_gems=buy_gems,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        transaction["pair_names"] = pair_names

        return transaction

    def batch_cancel_limit_orders(
        self,
        orders: List[NewCancelOrder],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TxParams:
        """Construct a transaction to cancel multiple limit orders in a batch.

        :param orders: List of cancel limit orders
        :type orders: List[NewCancelOrder]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction to execute the cancel limit orders batch.
        :rtype: TxParams
        """
        order_ids = []

        pair_names: List[str] = []
        for order in orders:
            pair_names.append(order.pair_name)

            order_ids.append(order.order_id)

        transaction = self.network.rubicon_market.batch_cancel(
            ids=order_ids,
            wallet=self.wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        transaction["pair_names"] = pair_names

        return transaction

    ######################################################################
    # data methods
    ######################################################################

    def get_offers(
        self,
        maker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        pair_names: Optional[List[str]] = None,
        book_side: Optional[
            OrderSide
        ] = None,  # TODO: decide if we should default to neutral
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        first: int = 10000000,
        order_by: str = "timestamp",
        order_direction: str = "desc",
        as_dataframe: bool = True,
    ) -> Optional[pd.DataFrame] | List[LimitOrder]:
        # TODO: add support for multiple pair_names
        if len(pair_names) == 1:
            base_asset, quote_asset = pair_names[0].split("/")

            match book_side:
                case OrderSide.BUY:
                    result = self.market_data.get_offers(
                        maker=maker,
                        from_address=from_address,
                        buy_gem=self.network.tokens[base_asset].address,
                        pay_gem=self.network.tokens[quote_asset].address,
                        side=book_side.value.lower(),
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                        as_dataframe=as_dataframe,
                    )
                case OrderSide.SELL:
                    result = self.market_data.get_offers(
                        maker=maker,
                        from_address=from_address,
                        buy_gem=self.network.tokens[quote_asset].address,
                        pay_gem=self.network.tokens[base_asset].address,
                        side=book_side.value.lower(),
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                        as_dataframe=as_dataframe,
                    )
                case _:
                    bids = self.market_data.get_offers(
                        maker=maker,
                        from_address=from_address,
                        buy_gem=self.network.tokens[base_asset].address,
                        pay_gem=self.network.tokens[quote_asset].address,
                        side=OrderSide.BUY.value.lower(),
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                        as_dataframe=as_dataframe,
                    )
                    asks = self.market_data.get_offers(
                        maker=maker,
                        from_address=from_address,
                        buy_gem=self.network.tokens[quote_asset].address,
                        pay_gem=self.network.tokens[base_asset].address,
                        side=OrderSide.SELL.value.lower(),
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                        as_dataframe=as_dataframe,
                    )

                    if as_dataframe:
                        result = pd.concat([bids, asks]).reset_index(drop=True)
                    else:
                        result = bids + asks

        else:
            result = self.market_data.get_offers(
                maker=maker,
                from_address=from_address,
                buy_gem=None,
                pay_gem=None,
                side=None,
                open=open,
                start_time=start_time,
                end_time=end_time,
                start_block=start_block,
                end_block=end_block,
                first=first,
                order_by=order_by,
                order_direction=order_direction,
                as_dataframe=as_dataframe,
            )

        if isinstance(result, List):
            limit_orders: List[LimitOrder] = []

            for offer in result:
                base_asset, quote_asset = self._get_base_and_quote_asset(
                    raw=offer, pair_names=pair_names
                )
                if not base_asset or not quote_asset:
                    continue

                limit_orders.append(
                    LimitOrder.from_subgraph_offer(
                        base_asset=base_asset, quote_asset=quote_asset, offer=offer
                    )
                )
            return limit_orders

        return result

    def get_trades(
        self,
        taker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        pair_names: Optional[List[str]] = None,
        book_side: Optional[OrderSide] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        maker: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
        maker_from_address: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
        first: int = 10000000,
        order_by: str = "timestamp",
        order_direction: str = "desc",
    ) -> pd.DataFrame:
        if len(pair_names) == 1:
            base_asset, quote_asset = pair_names[0].split("/")

            match book_side:
                case OrderSide.BUY:
                    return self.market_data.get_trades(
                        taker=taker,
                        from_address=from_address,
                        take_gem=self.network.tokens[base_asset].address,
                        give_gem=self.network.tokens[quote_asset].address,
                        side=book_side.value.lower(),
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        maker=maker,
                        maker_from_address=maker_from_address,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                    )
                case OrderSide.SELL:
                    return self.market_data.get_trades(
                        taker=taker,
                        from_address=from_address,
                        take_gem=self.network.tokens[quote_asset].address,
                        give_gem=self.network.tokens[base_asset].address,
                        side=book_side.value.lower(),
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        maker=maker,
                        maker_from_address=maker_from_address,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                    )
                case _:
                    buys = self.market_data.get_trades(
                        taker=taker,
                        from_address=from_address,
                        take_gem=self.network.tokens[base_asset].address,
                        give_gem=self.network.tokens[quote_asset].address,
                        side=OrderSide.BUY.value.lower(),
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        maker=maker,
                        maker_from_address=maker_from_address,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                    )
                    sells = self.market_data.get_trades(
                        taker=taker,
                        from_address=from_address,
                        take_gem=self.network.tokens[quote_asset].address,
                        give_gem=self.network.tokens[base_asset].address,
                        side=OrderSide.SELL.value.lower(),
                        start_time=start_time,
                        end_time=end_time,
                        start_block=start_block,
                        end_block=end_block,
                        maker=maker,
                        maker_from_address=maker_from_address,
                        first=first,
                        order_by=order_by,
                        order_direction=order_direction,
                    )

                    return pd.concat([buys, sells]).reset_index(drop=True)

        else:
            return self.market_data.get_trades(
                taker=taker,
                from_address=from_address,
                take_gem=None,
                give_gem=None,
                side=None,
                start_time=start_time,
                end_time=end_time,
                start_block=start_block,
                end_block=end_block,
                maker=maker,
                maker_from_address=maker_from_address,
                first=first,
                order_by=order_by,
                order_direction=order_direction,
            )

    ######################################################################
    # helper methods
    ######################################################################

    def _handle_transaction_receipt_raw_events(
        self,
        transaction_receipt: TransactionReceipt,
        pair_names: Optional[List[str]] = None,
    ) -> TransactionReceipt:
        """
        Transforms the raw transaction receipt events to human-readable events

        :param transaction_receipt:
        :type transaction_receipt: TransactionReceipt
        :return: The transaction receipt with human-readable events populated
        :rtype: TransactionReceipt
        """
        events: List[Any] = []
        for raw_event in transaction_receipt.raw_events:
            if (
                isinstance(raw_event, EmitOfferEvent)
                or isinstance(raw_event, EmitTakeEvent)
                or isinstance(raw_event, EmitCancelEvent)
            ):
                raw_event: Union[EmitOfferEvent, EmitTakeEvent, EmitCancelEvent]

                base_asset, quote_asset = self._get_base_and_quote_asset(
                    raw=raw_event, pair_names=pair_names
                )
                if not base_asset or not quote_asset:
                    continue

                events.append(
                    OrderEvent.from_event(
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        event=raw_event,
                        wallet=self.wallet,
                    )
                )
            if isinstance(raw_event, EmitApproval):
                try:
                    token = self.network.tokens[raw_event.address]
                except KeyError:
                    continue
                if raw_event.src == self.wallet or raw_event.guy == self.wallet:
                    events.append(
                        ApprovalEvent(
                            token=token.symbol,
                            amount=token.to_decimal(raw_event.wad),
                            spender=raw_event.guy,
                            source=raw_event.src,
                        )
                    )
            if isinstance(raw_event, EmitTransfer):
                try:
                    token = self.network.tokens[raw_event.address]
                except KeyError:
                    continue
                if raw_event.src == self.wallet or raw_event.dst == self.wallet:
                    events.append(
                        TransferEvent(
                            token=token.symbol,
                            amount=token.to_decimal(raw_event.wad),
                            recipient=raw_event.dst,
                            source=raw_event.src,
                        )
                    )
        # TODO: handle other events nicely

        transaction_receipt.set_events(events=events)

        return transaction_receipt

    def _get_base_and_quote_asset(
        self,
        raw: EmitOfferEvent | EmitTakeEvent | EmitCancelEvent | SubgraphOffer,
        pair_names: Optional[List[str]] = None,
    ) -> Tuple[Optional[ERC20], Optional[ERC20]]:
        """Get the base and quote asset of an event"""
        if pair_names is None:
            return None, None

        pay_gem = self.network.tokens[raw.pay_gem]
        buy_gem = self.network.tokens[raw.buy_gem]

        for pair_name in pair_names:
            base_asset, quote_asset = pair_name.split("/")

            if base_asset == pay_gem.symbol and quote_asset == buy_gem.symbol:
                return pay_gem, buy_gem
            elif base_asset == buy_gem.symbol and quote_asset == pay_gem.symbol:
                return buy_gem, pay_gem

        return None, None
