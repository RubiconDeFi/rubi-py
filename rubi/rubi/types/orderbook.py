from _decimal import Decimal
from typing import List, Tuple

from rubi import ERC20
from rubi.types.conversion_helper import _price_and_size_from_asset_amounts
from rubi.types.order import OrderSide


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
        book_side: OrderSide,
        levels: List[BookLevel]
    ):
        self.book_side = book_side
        self.levels = levels

    def best_price(self) -> Decimal:
        return self.levels[0].price

    @classmethod
    def from_rubicon_side(
        cls,
        book_side: OrderSide,
        orders: List[List[int]],
        base_asset: ERC20,
        quote_asset: ERC20
    ) -> "BookSide":
        levels: List[BookLevel] = []

        match book_side:
            case OrderSide.SELL:
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
            case OrderSide.BUY:
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
                book_side=OrderSide.BUY,  # Corresponds to BIDS
                orders=rubicon_book[1],
                base_asset=base_asset,
                quote_asset=quote_asset
            ),
            asks=BookSide.from_rubicon_side(
                book_side=OrderSide.SELL,  # Corresponds to ASKS
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
