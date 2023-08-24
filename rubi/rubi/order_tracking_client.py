import logging
from _decimal import Decimal
from multiprocessing import Queue
from typing import Optional, Dict, List, Any, Type, Union

from eth_typing import ChecksumAddress
from web3.types import TxParams, EventData

from rubi import (
    Client,
    Network,
    LimitOrder,
    OrderEvent,
    OrderType,
    EmitTakeEvent,
    EmitDeleteEvent,
    TransactionReceipt,
    BaseEvent,
    EmitFeeEvent,
    FeeEvent,
    EmitCancelEvent,
    EmitOfferEvent,
)

logger = logging.getLogger(__name__)


class OrderTrackingClient(Client):
    """This class is a client for Rubicon that tracks orders on Rubicon for you.

    :param network: A Network instance
    :type network: Network
    :param pair_names: The list of pair names that the client is going to track.
    :type pair_names: List[str]
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
        pair_names: List[str],
        message_queue: Optional[Queue] = None,
        wallet: Optional[Union[ChecksumAddress, str]] = None,
        key: Optional[str] = None,
    ):
        super().__init__(
            network=network, message_queue=message_queue, wallet=wallet, key=key
        )

        limit_orders_from_subgraph = self.get_offers(
            maker=self.wallet, open=True, as_dataframe=False, pair_names=pair_names
        )

        self.open_limit_orders: Dict[int, LimitOrder] = {}
        if limit_orders_from_subgraph:
            for limit_order in limit_orders_from_subgraph:
                self.open_limit_orders[limit_order.order_id] = limit_order

        self.pairs_with_registered_event_listeners: List[str] = []
        self._register_listeners(pair_names=pair_names)

    @classmethod
    def from_http_node_url(
        cls,
        http_node_url: str,
        pair_names: List[str] = None,
        message_queue: Optional[Queue] = None,
        wallet: Optional[Union[ChecksumAddress, str]] = None,
        key: Optional[str] = None,
        custom_token_addresses_file: Optional[str] = None,
        **kwargs,
    ):
        """Initialize a Client using a http_node_url.

        :param http_node_url: URL of the HTTP node.
        :type http_node_url: str
        :param pair_names: The list of pair names that the client is going to track.
        :type pair_names: List[str]
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
        if pair_names is None:
            raise Exception(
                "OrderTrackingClient cannot be instantiated without a list of pair_names."
            )

        network = Network.from_http_node_url(
            http_node_url=http_node_url,
            custom_token_addresses_file=custom_token_addresses_file,
        )

        return cls(
            network=network,
            pair_names=pair_names,
            message_queue=message_queue,
            wallet=wallet,
            key=key,
        )

    ######################################################################
    # overridden methods
    ######################################################################

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

        if pair_names:
            self._update_active_limit_orders(
                events=processed_transaction_receipt.events
            )

        return processed_transaction_receipt

    ######################################################################
    # order tracking methods
    ######################################################################

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

                self._update_active_limit_orders(events=[event])

            self.message_queue.put(event)

    def _update_active_limit_orders(self, events: List[Any]) -> None:
        """Update active limit order based on incoming events"""
        for event in events:
            if not isinstance(event, OrderEvent):
                continue

            event: OrderEvent
            if event.limit_order_owner != self.wallet:
                continue

            match event.order_type:
                case OrderType.LIMIT:
                    if self.open_limit_orders.get(event.limit_order_id):
                        # If we are already tracking the order then don't add it again
                        continue

                    self.open_limit_orders[
                        event.limit_order_id
                    ] = LimitOrder.from_order_event(order_event=event)
                case OrderType.LIMIT_TAKEN:
                    taken_order = self.open_limit_orders[event.limit_order_id]

                    if taken_order.remaining_size - event.size <= Decimal("0"):
                        self._delete_active_limit_order(order_id=event.limit_order_id)
                    else:
                        self.open_limit_orders[event.limit_order_id].update_with_take(
                            order_event=event
                        )
                case OrderType.CANCEL:
                    self._delete_active_limit_order(order_id=event.limit_order_id)
                case OrderType.LIMIT_DELETED:
                    self._delete_active_limit_order(order_id=event.limit_order_id)

    def _delete_active_limit_order(self, order_id: int) -> None:
        """Delete active limit order"""
        try:
            del self.open_limit_orders[order_id]
        except KeyError:
            logger.debug(
                f"Limit order {order_id} already removed from active limit orders."
            )

    def _register_listeners(self, pair_names: List[str]) -> None:
        """Register event listeners"""
        new_pair_names = [
            pair_name
            for pair_name in pair_names
            if pair_name not in self.pairs_with_registered_event_listeners
        ]

        self.pairs_with_registered_event_listeners.extend(new_pair_names)

        for pair_name in new_pair_names:
            self.start_event_poller(
                pair_name=pair_name,
                event_type=EmitOfferEvent,
                filters={"maker": self.wallet},
            )
            self.start_event_poller(
                pair_name=pair_name,
                event_type=EmitTakeEvent,
                filters={"maker": self.wallet},
            )
            self.start_event_poller(
                pair_name=pair_name,
                event_type=EmitCancelEvent,
                filters={"maker": self.wallet},
            )
            self.start_event_poller(
                pair_name=pair_name,
                event_type=EmitDeleteEvent,
                filters={"maker": self.wallet},
            )
