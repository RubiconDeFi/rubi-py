from _decimal import Decimal
from enum import Enum
from typing import Optional, Union, List

from eth_typing import ChecksumAddress

from rubi.contracts.types.events import BaseEvent, EmitOfferEvent, EmitCancelEvent, EmitTakeEvent
from rubi.types.pair import Pair


class OrderSide(Enum):
    """Enumeration representing the order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Enumeration representing the order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"

    # Only used for events coming from the RubiconMarket
    LIMIT_TAKEN = "LIMIT_TAKEN"
    CANCEL = "CANCEL"


class BaseNewOrder:
    """Base class for representing a new order.

    :param pair_name: The name of the trading pair.
    :type pair_name: str
    :param order_type: The type of the order.
    :type order_type: OrderType
    :param order_side: The side of the order (buy or sell).
    :type order_side: OrderSide
    """

    def __init__(
        self,
        pair_name: str,
        order_type: OrderType,
        order_side: OrderSide,
    ):
        """constructor method."""
        self.pair = pair_name
        self.order_side = order_side
        self.order_type = order_type


class NewMarketOrder(BaseNewOrder):
    """Class representing a new market order.

    :param pair_name: The name of the pair being traded e.g. WETH/USDC.
    :type pair_name: str
    :param order_side: The side of the order (BUY or SELL).
    :type order_side: OrderSide
    :param size: The size of the order.
    :type size: Decimal
    :param worst_execution_price: The worst execution price for the order (optional). Defaults to 0 if selling and
        10 million if buying as random bounds.
    :type worst_execution_price: Decimal
    """

    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        size: Decimal,
        worst_execution_price: Optional[Decimal],
    ):
        """constructor method."""

        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.MARKET,
            order_side=order_side,

        )
        self.size = size

        if worst_execution_price is None:
            self.worst_execution_price = Decimal("0") if order_side.SELL else Decimal("10") ** Decimal("7")
        else:
            self.worst_execution_price = worst_execution_price


class NewLimitOrder(BaseNewOrder):
    """Class representing a new limit order

    :param pair_name: The name of the pair being traded e.g. WETH/USDC.
    :type pair_name: str
    :param order_side: The side of the order (buy or sell).
    :type order_side: OrderSide
    :param size: The size of the order.
    :type size: Decimal
    :param price: The price of the order.
    :type price: Decimal
    """

    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        size: Decimal,
        price: Decimal
    ):
        """constructor method."""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.size = size
        self.price = price


class UpdateLimitOrder(BaseNewOrder):
    """Class representing an update to an existing limit order

    :param pair_name: The name of the pair being traded e.g. WETH/USDC.
    :type pair_name: str
    :param order_side: The side of the order (BUY or SELL).
    :type order_side: OrderSide
    :param order_id: The ID of the order to update.
    :type order_id: int
    :param size: The updated size of the order.
    :type size: Decimal
    :param price: The updated price of the order.
    :type price: Decimal
    """

    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        order_id: int,
        size: Decimal,
        price: Decimal
    ):
        """constructor method"""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.order_id = order_id
        self.size = size
        self.price = price


class NewCancelOrder(BaseNewOrder):
    """Class representing a limit order cancellation

    :param pair_name: The name of the trading pair.
    :type pair_name: str
    :param order_side: The side of the order (buy or sell).
    :type order_side: OrderSide
    :param order_id: The ID of the order to cancel.
    :type order_id: int
    """

    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        order_id: int
    ):
        """constructor method"""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.order_id = order_id


class Transaction:
    """
    Class representing a transaction to be executed on chain

    :param orders: The list of orders to include in the transaction.
    :type orders: List[BaseNewOrder]
    :param nonce: The nonce for the transaction (optional).
    :type nonce: int
    :param gas: The gas limit for the transaction.
    :type gas: int
    :param max_fee_per_gas: The maximum fee per gas for the transaction (optional).
    :type max_fee_per_gas: int
    :param max_priority_fee_per_gas: The maximum priority fee per gas for the transaction (optional).
    :type max_priority_fee_per_gas: int
    """

    def __init__(
        self,
        orders: List[BaseNewOrder],
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        """constructor method"""
        if len(orders) < 1:
            raise Exception("Transaction cannot be instantiated with an empty order list")

        self.orders = orders
        self.nonce = nonce
        self.gas = gas
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee_per_gas = max_priority_fee_per_gas


class OrderEvent:
    """Class to represent Rubicon Market events as an order

    :param limit_order_id: The ID of the limit order.
    :type limit_order_id: int
    :param limit_order_owner: The owner of the limit order.
    :type limit_order_owner: ChecksumAddress
    :param market_order_owner: The owner of the market order (optional). Only has a value if event is an emitTakeEvent.
    :type market_order_owner: Optional[ChecksumAddress]
    :param pair_name: The name of the pair being traded e.g. WETH/USDC.
    :type pair_name: str
    :param order_side: The side of the order (BUY or SELL).
    :type order_side: OrderSide
    :param order_type: The type of the order (MARKET, LIMIT, LIMIT_TAKEN, or CANCEL).
    :type order_type: OrderType
    :param price: The price of the order.
    :type price: Decimal
    :param size: The size of the order.
    :type size: Decimal
    """

    def __init__(
        self,
        limit_order_id: int,
        limit_order_owner: ChecksumAddress,
        market_order_owner: Optional[ChecksumAddress],
        pair_name: str,
        order_side: OrderSide,
        order_type: OrderType,
        price: Decimal,
        size: Decimal,
    ):
        self.limit_order_id = limit_order_id
        self.limit_order_owner = limit_order_owner
        self.market_order_owner: Optional[ChecksumAddress] = market_order_owner
        self.pair_name = pair_name
        self.order_side = order_side
        self.order_type = order_type
        self.price = price
        self.size = size

    @classmethod
    def from_event(cls, pair: Pair, event: BaseEvent, wallet: ChecksumAddress) -> "OrderEvent":
        """Create an OrderEvent from a BaseEvent emitted by the Rubicon Market.

        :param pair: The asset pair associated with the event.
        :type pair: Pair
        :param event: The event to convert.
        :type event: BaseEvent
        :param wallet: The wallet address associated with the event.
        :type wallet: ChecksumAddress
        :return: The created OrderEvent.
        :rtype: OrderEvent
        :raises Exception: If the event cannot be converted into an OrderEvent. This occurs if the Base event has a type
            other than EmitOfferEvent, EmitCancelEvent or EmitTakeEvent
        """
        if isinstance(event, EmitOfferEvent):
            if pair.bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    base_amt=event.buy_amt,
                    quote_amt=event.pay_amt
                )
            else:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    base_amt=event.pay_amt,
                    quote_amt=event.buy_amt
                )
        elif isinstance(event, EmitCancelEvent):
            if pair.bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.BUY,
                    order_type=OrderType.CANCEL,
                    base_amt=event.buy_amt,
                    quote_amt=event.pay_amt
                )
            else:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.SELL,
                    order_type=OrderType.CANCEL,
                    base_amt=event.pay_amt,
                    quote_amt=event.buy_amt
                )
        elif isinstance(event, EmitTakeEvent):
            # This is nuanced as we can either receive a take event for a market order or limit order we placed. When
            # we take the bid_identifier indicates selling into the bids while the ask identifier indicates buying
            # into the asks. While the reverse is true for when we make.
            if pair.bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.BUY if wallet == event.maker else OrderSide.SELL,
                    order_type=OrderType.LIMIT_TAKEN if wallet == event.maker else OrderType.MARKET,
                    base_amt=event.give_amt,
                    quote_amt=event.take_amt
                )
            else:
                return cls._build_order(
                    event=event,
                    pair=pair,
                    side=OrderSide.SELL if wallet == event.maker else OrderSide.BUY,
                    order_type=OrderType.LIMIT_TAKEN if wallet == event.maker else OrderType.MARKET,
                    base_amt=event.take_amt,
                    quote_amt=event.give_amt
                )
        else:
            Exception(f"{event.__class__} cannot be converted into an OrderEvent")

    @classmethod
    def _build_order(
        cls,
        event: Union[EmitOfferEvent, EmitCancelEvent, EmitTakeEvent],
        pair: Pair,
        side: OrderSide,
        order_type: OrderType,
        base_amt: int,
        quote_amt: int
    ) -> "OrderEvent":
        """Build an OrderEvent from event data.

        :param event: The event data.
        :type event: Union[EmitOfferEvent, EmitCancelEvent, EmitTakeEvent]
        :param pair: The asset pair associated with the event.
        :type pair: Pair
        :param side: The order side.
        :type side: OrderSide
        :param order_type: The order type.
        :type order_type: OrderType
        :param base_amt: The base amount of the order.
        :type base_amt: int
        :param quote_amt: The quote amount of the order.
        :type quote_amt: int
        :return: The constructed OrderEvent.
        :rtype: OrderEvent
        """
        size = pair.base_asset.to_decimal(base_amt)
        price = pair.quote_asset.to_decimal(quote_amt) / size

        return cls(
            limit_order_id=event.id,
            limit_order_owner=event.maker,
            market_order_owner=event.taker if isinstance(event, EmitTakeEvent) else None,
            pair_name=pair.name,
            order_side=side,
            order_type=order_type,
            size=size,
            price=price
        )

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
