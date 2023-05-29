from _decimal import Decimal
from enum import Enum
from typing import Optional, Union, List

from eth_typing import ChecksumAddress

from rubi import BaseEvent, EmitOfferEvent, EmitCancelEvent, EmitTakeEvent
from rubi.types.conversion_helper import _price_and_size_from_asset_amounts
from rubi.types.pair import Pair


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

    # Only used for events coming from the RubiconMarket
    LIMIT_TAKEN = "LIMIT_TAKEN"
    CANCEL = "CANCEL"


class BaseNewOrder:
    def __init__(
        self,
        pair_name: str,
        order_type: OrderType,
        order_side: OrderSide,
    ):
        self.pair = pair_name
        self.order_side = order_side
        self.order_type = order_type


class NewMarketOrder(BaseNewOrder):
    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        size: Decimal,
        # TODO: think about allowable_slippage
        allowable_slippage: Optional[Decimal] = Decimal("0.005"),
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.MARKET,
            order_side=order_side,

        )

        self.size = size,
        self.allowable_slippage = allowable_slippage


class NewLimitOrder(BaseNewOrder):
    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        size: Decimal,
        price: Decimal
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.size = size
        self.price = price


class UpdateLimitOrder(BaseNewOrder):
    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        order_id: int,
        size: Decimal,
        price: Decimal
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.order_id = order_id
        self.size = size
        self.price = price


class NewCancelOrder(BaseNewOrder):
    def __init__(
        self,
        pair_name: str,
        order_side: OrderSide,
        order_id: int
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
        )

        self.order_id = order_id


class Transaction:
    def __init__(
        self,
        orders: List[BaseNewOrder],
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        if len(orders) < 1:
            raise Exception("Transaction cannot be instantiated with an empty order list")

        self.orders = orders
        self.nonce = nonce
        self.gas = gas
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee_per_gas = max_priority_fee_per_gas


class OrderEvent:
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
        self.market_order_owner = market_order_owner
        self.pair_name = pair_name
        self.order_side = order_side
        self.order_type = order_type
        self.price = price
        self.size = size

    @classmethod
    def from_event(cls, pair: Pair, event: BaseEvent, wallet: ChecksumAddress) -> "OrderEvent":
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
        price, size = _price_and_size_from_asset_amounts(
            base_asset=pair.base_asset,
            quote_asset=pair.quote_asset,
            base_amount=base_amt,
            quote_amount=quote_amt
        )

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
