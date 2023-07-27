from _decimal import Decimal
from typing import List, Tuple

from rubi import ERC20
from rubi.rubicon_types.order import OrderSide


class BookLevel:
    """Class representing a level in the order book.

    :param price: The price of the level.
    :type price: Decimal
    :param size: The size of the level.
    :type size: Decimal
    """

    def __init__(self, price: Decimal, size: Decimal):
        """constructor method."""
        self.price = price
        self.size = size

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class BookSide:
    """Class Representing a side of the order book. Either bids or asks.

    :param book_side: The side of the order book (BUY or SELL).
    :type book_side: OrderSide
    :param levels: The list of levels on the side.
    :type levels: List[BookLevel]
    """

    def __init__(self, book_side: OrderSide, levels: List[BookLevel]):
        """constructor method."""
        self.book_side = book_side
        self.levels = levels

    def best_price(self) -> Decimal:
        """Returns the price of the best level on the book side.

        :return: The price of the best level.
        :rtype: Decimal
        """
        return self.levels[0].price

    def remove_liquidity_from_book(self, price: Decimal, size: Decimal):
        for i, level in enumerate(self.levels):
            if price == level.price:
                if size == level.size:
                    del self.levels[i]
                else:
                    self.levels[i] = BookLevel(price=price, size=level.size - size)
                return

    @classmethod
    def from_rubicon_offers(
        cls,
        book_side: OrderSide,
        offers: List[List[int]],
        base_asset: ERC20,
        quote_asset: ERC20,
    ) -> "BookSide":
        """Creates a BookSide instance from a list of Rubicon offers.

        :param book_side: The side of the order book (BUY or SELL).
        :type book_side: OrderSide
        :param offers: The list of offers retrieved from the Rubicon for an asset pair pay_gem/buy_gem.
        :type offers: List[List[int]]
        :param base_asset: The base asset of the order book.
        :type base_asset: ERC20
        :param quote_asset: The quote asset of the order book.
        :type quote_asset: ERC20
        :return: The BookSide instance representing the order book side.
        :rtype: BookSide
        """
        levels: List[BookLevel] = []

        match book_side:
            case OrderSide.SELL:
                for i, order in enumerate(offers):
                    size = base_asset.to_decimal(order[0])
                    price = quote_asset.to_decimal(order[1]) / size

                    if levels and levels[-1].price == price:
                        levels[-1].size += size
                    else:
                        levels.append(BookLevel(price=price, size=size))
            case OrderSide.BUY:
                for i, order in enumerate(offers):
                    size = base_asset.to_decimal(order[1])
                    price = quote_asset.to_decimal(order[0]) / size

                    if levels and levels[-1].price == price:
                        levels[-1].size += size
                    else:
                        levels.append(BookLevel(price=price, size=size))

        return cls(book_side=book_side, levels=levels)

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class OrderBook:
    """Class represents an OrderBook.

    :param bids: BookSide representing the bid orders.
    :type bids: BookSide
    :param asks: BookSide representing the ask orders.
    :type asks: BookSide
    """

    def __init__(self, bids: BookSide, asks: BookSide):
        """constructor method."""
        self.bids = bids
        self.asks = asks

    @classmethod
    def from_rubicon_offer_book(
        cls,
        offer_book: Tuple[List[List[int]], List[List[int]]],
        base_asset: ERC20,
        quote_asset: ERC20,
    ) -> "OrderBook":
        """Create an OrderBook from Rubicon offer book.

        :param offer_book: Rubicon offer book containing bid and ask offers.
        :type offer_book: Tuple[List[List[int]], List[List[int]]]
        :param base_asset: An ERC20 instance representing the base asset.
        :type base_asset: ERC20
        :param quote_asset: An ERC20 instance representing the quote asset.
        :type quote_asset: ERC20
        :return: OrderBook instance.
        :rtype: OrderBook
        """
        return cls(
            bids=BookSide.from_rubicon_offers(
                book_side=OrderSide.BUY,  # Corresponds to BIDS
                offers=offer_book[1],
                base_asset=base_asset,
                quote_asset=quote_asset,
            ),
            asks=BookSide.from_rubicon_offers(
                book_side=OrderSide.SELL,  # Corresponds to ASKS
                offers=offer_book[0],
                base_asset=base_asset,
                quote_asset=quote_asset,
            ),
        )

    def best_bid(self) -> Decimal:
        """Get the best bid price from the order book.

        :return: Best bid price.
        :rtype: Decimal
        """
        return self.bids.best_price()

    def best_ask(self) -> Decimal:
        """Get the best ask price from the order book.

        :return: Best ask price.
        :rtype: Decimal
        """
        return self.asks.best_price()

    def mid_price(self) -> Decimal:
        """Calculate the mid-price of the order book.

        :return: mid-price.
        :rtype: Decimal
        """
        return (self.best_bid() + self.best_ask()) / 2

    def spread(self) -> Decimal:
        """Calculate the current bid ask spread of the order book.

        :return: spread
        :rtype: Decimal
        """

        return self.best_ask() - self.best_bid()

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


# TODO: add a DetailedOrderBook class that contains the full order book composed of LimitOrder instances
