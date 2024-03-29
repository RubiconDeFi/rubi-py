from _decimal import Decimal
from enum import Enum
from typing import Optional, Union

from eth_typing import ChecksumAddress
from web3 import Web3

from rubi.data.helpers import SubgraphOffer
from rubi.contracts import (
    ERC20,
    BaseEvent,
    EmitOfferEvent,
    EmitCancelEvent,
    EmitTakeEvent,
    EmitDeleteEvent,
    EmitFeeEvent,
)


class OrderSide(Enum):
    """Enumeration representing the order side."""

    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"

    def sign(self) -> int:
        """
        :return: Numerical value of the side.
        :rtype: int
        """
        match self:
            case OrderSide.NEUTRAL:
                return 0

            case OrderSide.BUY:
                return 1

            case OrderSide.SELL:
                return -1

    def opposite(self) -> "OrderSide":
        match self:
            case OrderSide.NEUTRAL:
                return OrderSide.NEUTRAL

            case OrderSide.BUY:
                return OrderSide.SELL

            case OrderSide.SELL:
                return OrderSide.BUY


class OrderType(Enum):
    """Enumeration representing the order type."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"

    # Only used for events coming from the RubiconMarket
    LIMIT_TAKEN = "LIMIT_TAKEN"
    LIMIT_DELETED = "LIMIT_DELETED"
    CANCEL = "CANCEL"


class BaseOrder:
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
        self.pair_name = pair_name
        self.order_side = order_side
        self.order_type = order_type


class NewMarketOrder(BaseOrder):
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
            self.worst_execution_price = (
                Decimal("0") if order_side.SELL else Decimal("10") ** Decimal("7")
            )
        else:
            self.worst_execution_price = worst_execution_price


class NewLimitOrder(BaseOrder):
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
        self, pair_name: str, order_side: OrderSide, size: Decimal, price: Decimal
    ):
        """constructor method."""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.size = size
        self.price = price

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class UpdateLimitOrder(BaseOrder):
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
        price: Decimal,
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


class LimitOrder(BaseOrder):
    """Class representing an existing limit order

    :param pair_name: The name of the pair being traded e.g. WETH/USDC.
    :type pair_name: str
    :param order_side: The side of the order (BUY or SELL).
    :type order_side: OrderSide
    :param order_id: The ID of the order to update.
    :type order_id: int
    :param order_owner: The address of the owner of the order
    :type order_owner: ChecksumAddress
    :param size: The updated size of the order.
    :type size: Decimal
    :param price: The updated price of the order.
    :type price: Decimal
    :param filled_size: The amount of the order that has been filled
    :type filled_size: Decimal
    """

    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        order_id: int,
        order_owner: ChecksumAddress,
        size: Decimal,
        price: Decimal,
        filled_size: Decimal = Decimal("0"),
        open: bool = True,
    ):
        """constructor method"""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.order_id = order_id
        self.order_owner = order_owner
        self.size = size
        self.price = price
        self.filled_size = filled_size
        self.open = open

    @property
    def remaining_size(self) -> Decimal:
        return self.size - self.filled_size

    @classmethod
    def from_order_event(cls, order_event: "OrderEvent") -> "LimitOrder":
        if order_event.order_type != OrderType.LIMIT:
            raise Exception("event must have LIMIT as order_type.")

        return cls(
            pair_name=order_event.pair_name,
            order_side=order_event.order_side,
            order_id=order_event.limit_order_id,
            order_owner=order_event.limit_order_owner,
            size=order_event.size,
            price=order_event.price,
        )

    @classmethod
    def from_subgraph_offer(
        cls, base_asset: ERC20, quote_asset: ERC20, offer: SubgraphOffer
    ) -> "LimitOrder":
        if base_asset.address == offer.buy_gem:
            size = base_asset.to_decimal(offer.buy_amt)
            price = quote_asset.to_decimal(offer.pay_amt) / size
            filled_size = base_asset.to_decimal(offer.bought_amt)

            return cls(
                pair_name=f"{base_asset.symbol}/{quote_asset.symbol}",
                order_side=OrderSide.BUY,
                order_id=offer.order_id,
                order_owner=offer.order_owner,
                size=size,
                price=price,
                filled_size=filled_size,
            )
        else:
            size = base_asset.to_decimal(offer.pay_amt)
            price = quote_asset.to_decimal(offer.buy_amt) / size
            filled_size = base_asset.to_decimal(offer.paid_amt)

            return cls(
                pair_name=f"{base_asset.symbol}/{quote_asset.symbol}",
                order_side=OrderSide.SELL,
                order_id=offer.order_id,
                order_owner=offer.order_owner,
                size=size,
                price=price,
                filled_size=filled_size,
            )

    def update_with_take(self, order_event: "OrderEvent"):
        self.filled_size += order_event.size

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class NewCancelOrder(BaseOrder):
    """Class representing a limit order cancellation

    :param pair_name: The name of the trading pair.
    :type pair_name: str
    :param order_id: The ID of the order to cancel.
    :type order_id: int
    """

    def __init__(self, pair_name: str, order_id: int):
        """constructor method"""
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=OrderSide.NEUTRAL,
        )

        self.order_id = order_id


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
    :param order_type: The type of the order (MARKET, LIMIT, LIMIT_TAKEN, LIMIT_DELETED, or CANCEL).
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
        order_side: Optional[OrderSide],
        order_type: OrderType,
        price: Optional[Decimal],
        size: Optional[Decimal],
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
    def from_event(
        cls,
        base_asset: ERC20,
        quote_asset: ERC20,
        event: BaseEvent,
        wallet: ChecksumAddress,
    ) -> "OrderEvent":
        """Create an OrderEvent from a BaseEvent emitted by the Rubicon Market.

        :param base_asset: The base asset associated with the event.
        :type base_asset: ERC20
        :param quote_asset: The quote asset associated with the event.
        :type quote_asset: ERC20
        :param event: The event to convert.
        :type event: BaseEvent
        :param wallet: The wallet address associated with the event.
        :type wallet: ChecksumAddress
        :return: The created OrderEvent.
        :rtype: OrderEvent
        :raises Exception: If the event cannot be converted into an OrderEvent. This occurs if the Base event has a type
            other than EmitOfferEvent, EmitCancelEvent, EmitTakeEvent or EmitDeleteEvent
        """
        bid_identifier = cls._bid_identifier(
            base_asset=base_asset, quote_asset=quote_asset
        )

        if isinstance(event, EmitOfferEvent):
            if bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    base_amt=event.buy_amt,
                    quote_amt=event.pay_amt,
                )
            else:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    base_amt=event.pay_amt,
                    quote_amt=event.buy_amt,
                )
        elif isinstance(event, EmitCancelEvent):
            if bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.BUY,
                    order_type=OrderType.CANCEL,
                    base_amt=event.buy_amt,
                    quote_amt=event.pay_amt,
                )
            else:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.SELL,
                    order_type=OrderType.CANCEL,
                    base_amt=event.pay_amt,
                    quote_amt=event.buy_amt,
                )
        elif isinstance(event, EmitTakeEvent):
            # This is nuanced as we can either receive a take event for a market order or limit order we placed. When
            # we take the bid_identifier indicates selling into the bids while the ask identifier indicates buying
            # into the asks. While the reverse is true for when we make.
            if bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.BUY if wallet == event.maker else OrderSide.SELL,
                    order_type=OrderType.LIMIT_TAKEN
                    if wallet == event.maker
                    else OrderType.MARKET,
                    base_amt=event.give_amt,
                    quote_amt=event.take_amt,
                )
            else:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=OrderSide.SELL if wallet == event.maker else OrderSide.BUY,
                    order_type=OrderType.LIMIT_TAKEN
                    if wallet == event.maker
                    else OrderType.MARKET,
                    base_amt=event.take_amt,
                    quote_amt=event.give_amt,
                )
        elif isinstance(event, EmitDeleteEvent):
            if bid_identifier == event.pair:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=None,
                    order_type=OrderType.LIMIT_DELETED,
                    base_amt=None,
                    quote_amt=None,
                )
            else:
                return cls._build_order(
                    event=event,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    side=None,
                    order_type=OrderType.LIMIT_DELETED,
                    base_amt=None,
                    quote_amt=None,
                )

        else:
            Exception(f"{event.__class__} cannot be converted into an OrderEvent")

    @classmethod
    def _build_order(
        cls,
        event: Union[EmitOfferEvent, EmitCancelEvent, EmitTakeEvent, EmitDeleteEvent],
        base_asset: ERC20,
        quote_asset: ERC20,
        side: Optional[OrderSide],
        order_type: OrderType,
        base_amt: Optional[int],
        quote_amt: Optional[int],
    ) -> "OrderEvent":
        """Build an OrderEvent from event data.

        :param event: The event data.
        :type event: Union[EmitOfferEvent, EmitCancelEvent, EmitTakeEvent]
        :param base_asset: The base asset associated with the event.
        :type base_asset: ERC20
        :param quote_asset: The quote asset associated with the event.
        :type quote_asset: ERC20
        :param side: The order side.
        :type side: Optional[OrderSide]
        :param order_type: The order type.
        :type order_type: OrderType
        :param base_amt: The base amount of the order.
        :type base_amt: Optional[int]
        :param quote_amt: The quote amount of the order.
        :type quote_amt: Optional[int]
        :return: The constructed OrderEvent.
        :rtype: OrderEvent
        """
        size = base_asset.to_decimal(base_amt) if base_amt else None
        price = quote_asset.to_decimal(quote_amt) / size if quote_amt else None

        return cls(
            limit_order_id=event.id,
            limit_order_owner=event.maker,
            market_order_owner=event.taker
            if isinstance(event, EmitTakeEvent)
            else None,
            pair_name=f"{base_asset.symbol}/{quote_asset.symbol}",
            order_side=side,
            order_type=order_type,
            size=size,
            price=price,
        )

    @staticmethod
    def _bid_identifier(base_asset: ERC20, quote_asset: ERC20) -> str:
        return Web3.solidity_keccak(
            abi_types=["address", "address"],
            values=[
                quote_asset.address,
                base_asset.address,
            ],
        ).hex()

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class FeeEvent:
    def __init__(
        self,
        id: int,
        pair_name: str,
        fee_to: ChecksumAddress,
        market_order_owner: ChecksumAddress,
        fee: Decimal,
        fee_asset: str,
    ):
        self.id = id
        self.pair_name = pair_name
        self.fee_to = fee_to
        self.market_order_owner = market_order_owner
        self.fee = fee
        self.fee_asset = fee_asset

    @classmethod
    def from_event(
        cls,
        pair_name: str,
        asset: ERC20,
        event: EmitFeeEvent,
    ) -> "FeeEvent":
        return cls(
            id=event.id,
            pair_name=pair_name,
            fee_to=event.fee_to,
            market_order_owner=event.taker,
            fee=asset.to_decimal(event.fee_amt),
            fee_asset=asset.symbol,
        )

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
