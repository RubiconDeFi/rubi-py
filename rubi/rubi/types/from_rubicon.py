from _decimal import Decimal
from typing import Tuple, List

from eth_typing import ChecksumAddress

from rubi import ERC20, EmitCancelEvent, EmitTakeEvent, EmitOfferEvent, BaseEvent
# circular imports otherwise
from .order import Side, OrderType
from .pair import Pair


# TODO: rethink the things in this file and the general structure of the types directory
def _price_and_size_from_asset_amounts(
    base_asset: ERC20,
    quote_asset: ERC20,
    base_amount: int,
    quote_amount: int
) -> Tuple[Decimal, Decimal]:
    price = (
                Decimal(quote_amount) / Decimal(10 ** quote_asset.decimal)
            ) / (
                Decimal(base_amount) / Decimal(10 ** base_asset.decimal)
            )
    size = Decimal(base_amount) / Decimal(10 ** base_asset.decimal)

    return price, size


class OrderEvent:
    def __init__(
        self,
        order_id: int,
        owner: ChecksumAddress,
        pair_name: str,
        order_side: Side,
        order_type: OrderType,
        price: Decimal,
        size: Decimal,
    ):
        self.order_id = order_id
        self.owner = owner
        self.pair_name = pair_name
        self.order_side = order_side
        self.order_type = order_type
        self.price = price
        self.size = size

    # TODO: break out commonality here
    @classmethod
    def from_event(cls, pair: Pair, event: BaseEvent) -> "OrderEvent":
        if isinstance(event, EmitOfferEvent):
            if pair.bid_identifier == event.pair:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.buy_amt,
                    quote_amount=event.pay_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.BID,
                    order_type=OrderType.LIMIT,
                    size=size,
                    price=price
                )
            else:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.pay_amt,
                    quote_amount=event.buy_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.ASK,
                    order_type=OrderType.LIMIT,
                    size=size,
                    price=price
                )
        elif isinstance(event, EmitCancelEvent):
            if pair.bid_identifier == event.pair:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.buy_amt,
                    quote_amount=event.pay_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.BID,
                    order_type=OrderType.CANCEL,
                    size=size,
                    price=price
                )
            else:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.buy_amt,
                    quote_amount=event.pay_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.BID,
                    order_type=OrderType.CANCEL,
                    size=size,
                    price=price
                )
        elif isinstance(event, EmitTakeEvent):
            if pair.bid_identifier == event.pair:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.take_amt,
                    quote_amount=event.give_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.BID,
                    order_type=OrderType.MARKET,
                    size=size,
                    price=price
                )
            else:
                price, size = _price_and_size_from_asset_amounts(
                    pair.base_asset,
                    pair.quote_asset,
                    base_amount=event.give_amt,
                    quote_amount=event.take_amt
                )

                return cls(
                    order_id=event.id,
                    owner=event.maker,
                    pair_name=pair.name,
                    order_side=Side.BID,
                    order_type=OrderType.MARKET,
                    size=size,
                    price=price
                )
        else:
            Exception(f"{event.__class__} cannot be converted into an OrderEvent")

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class BookLevel:
    def __init__(
        self,
        price: Decimal,
        size: Decimal
    ):
        self.price = price
        self.size = size

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class BookSide:
    def __init__(
        self,
        book_side: Side,
        levels: List[BookLevel]
    ):
        self.book_side = book_side
        self.levels = levels

    def best_price(self) -> Decimal:
        return self.levels[0].price

    @classmethod
    def from_rubicon_side(
        cls,
        book_side: Side,
        orders: List[List[int]],
        base_asset: ERC20,
        quote_asset: ERC20
    ) -> "BookSide":
        levels: List[BookLevel] = []

        match book_side:
            case Side.ASK:
                for i, order in enumerate(orders):
                    price, size = _price_and_size_from_asset_amounts(
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        base_amount=order[0],
                        quote_amount=order[1]
                    )

                    if levels and levels[-i].price == price:
                        levels[-1].size += size
                    else:
                        levels.append(BookLevel(price=price, size=size))
            case Side.BID:
                for i, order in enumerate(orders):
                    price, size = _price_and_size_from_asset_amounts(
                        base_asset=base_asset,
                        quote_asset=quote_asset,
                        base_amount=order[1],
                        quote_amount=order[0]
                    )

                    if levels and levels[-1].price == price:
                        levels[-1].size += size
                    else:
                        levels.append(BookLevel(price=price, size=size))

        return cls(
            book_side=book_side,
            levels=levels
        )

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class OrderBook:
    def __init__(self, bids: BookSide, asks: BookSide):
        self.bids = bids
        self.asks = asks

    @classmethod
    def from_rubicon_book(
        cls,
        rubicon_book: Tuple[List[List[int]], List[List[int]]],
        base_asset: ERC20,
        quote_asset: ERC20
    ) -> "OrderBook":
        return cls(
            bids=BookSide.from_rubicon_side(
                book_side=Side.BID,
                orders=rubicon_book[1],
                base_asset=base_asset,
                quote_asset=quote_asset
            ),
            asks=BookSide.from_rubicon_side(
                book_side=Side.ASK,
                orders=rubicon_book[0],
                base_asset=base_asset,
                quote_asset=quote_asset
            )
        )

    def best_bid(self) -> Decimal:
        return self.bids.best_price()

    def best_ask(self) -> Decimal:
        return self.asks.best_price()

    def mid_price(self) -> Decimal:
        return (self.best_bid() + self.best_ask()) / 2

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
