import logging
from _decimal import Decimal
from typing import List, Tuple
from .........users.denver.documents.open.rubi-py.rubi.rubi.rubicon_types.order import OrderSide

from rubi import ERC20
from rubi.rubi.rubicon_types.orderbook import BookLevel
from rubi.rubicon_types.order import OrderSide, LimitOrder


class BookLevel:
    """Class representing a level in the order book.

    :param price: The price of the level.
    :type price: Decimal
    :param size: The size of the level.
    :type size: Decimal
    """

    def __init__(
        self,
        price: Decimal,
        size: Decimal
    ):
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

    def __init__(
        self,
        book_side: OrderSide,
        levels: List[BookLevel]
    ):
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
        quote_asset: ERC20
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

                    if levels and levels[-i].price == price:
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

        return cls(
            book_side=book_side,
            levels=levels
        )

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
        quote_asset: ERC20
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
                quote_asset=quote_asset
            ),
            asks=BookSide.from_rubicon_offers(
                book_side=OrderSide.SELL,  # Corresponds to ASKS
                offers=offer_book[0],
                base_asset=base_asset,
                quote_asset=quote_asset
            )
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

class DetailedBookLevel(BookLevel):
    """Class representing a level in the detailed order book.
    
    :param price: The price of the level.
    :type price: Decimal
    :param size: The size of the level.
    :type size: Decimal # TODO: determine if we really want to use a decimal here, or if we want to just make a new type that doesn't extend BookLevel
    :param orders: The list of orders at the level.
    :type orders: List[LimitOrder] # TODO: determine if we really need to order these, i believe the order book follows a FIFO model
    """

    # TODO: may be worth checking out something like sortedcontainers to make this more efficient
    
    def __init__(
        self, 
        price: Decimal,
        size: Decimal,
        orders: List[LimitOrder]
    ): 
        """constructor method."""
        super().__init__(price, size)
        
        if not all(order.price == price for order in orders):
            raise ValueError("Order price does not match level price.") # TODO: maybe an unecessary check, but it's good to be safe
        
        # Sort orders by block number, block index, and transaction index
        self.orders = sorted(
            orders, 
            key=lambda order: (order.block_number, order.block_index, order.log_index)
        )

    @classmethod
    def from_rubicon_offers(
        cls,
        orders: List[LimitOrder]
    ):
        
        price = orders[0].price
        size = sum(order.get_size() for order in orders)
        
        return cls(price, size, orders)
    
    def add_order(
        self, 
        order: LimitOrder,
        sort: bool = False
    ): 
        """Add an order to the level.
        
        :param order: The order to add to the level.
        :type order: LimitOrder
        :param sort: Whether or not to sort the orders after adding the new order.
        :type sort: bool
        """
        if order.price != self.price:
            raise ValueError("Order price does not match level price.")
        
        self.orders.append(order)
        self.size += order.get_size()
        
        if sort:
            self.orders = sorted(
                self.orders, 
                key=lambda order: (order.block_number, order.block_index, order.log_index)
            )

    def remove_order(
            self, 
            id: int
        ):
        """Remove an order from the level.

        :param id: The id of the order to remove.
        :type id: int
        """
        
        for i, order in enumerate(self.orders):
            if order.id == id:
                
                self.size -= self.orders[i].get_size()

                del self.orders[i]
                return
        
        # If we didn't find the order, raise an error
        raise ValueError(f"Order with id {id} not found.") # TODO: maybe we should just log an error here instead of raising an exception
    
    def update_order(
        self, 
        id: int,
        base_amt_filled: int, 
        quote_amt_filled: int
    ): 
        """Update an order in the level.
        
        :param id: The id of the order to update.
        :type id: int
        :param base_amt_filled: The amount of the base asset that has been filled.
        :type base_amt_filled: int
        :param quote_amt_filled: The amount of the quote asset that has been filled.
        :type quote_amt_filled: int
        """

        for i, order in enumerate(self.orders):
            if order.id == id: 
                self.orders[i].update_fill(base_amt_filled, quote_amt_filled)
                self.size -= self.orders[i].get_size()
                return
        
        # If we didn't find the order, raise an error
        raise ValueError(f"Order with id {id} not found.") # TODO: maybe we should just log an error here instead of raising an exception

class DetailedBookSide(BookSide): 
    """Class representing a side of the detailed order book. Either bids or asks.
    
    :param book_side: The side of the order book (BUY or SELL).
    :type book_side: OrderSide
    :param levels: The list of levels on the side.
    :type levels: List[DetailedBookLevel]
    """

    def __init__(
        self, 
        book_side: OrderSide, 
        levels: List[DetailedBookLevel]
    ):
        """constructor method."""
        super().__init__(book_side, levels)

        # TODO: decide if this is the best path forward
        # for ease of use, we will store a dictionary that maps the id of the offer to the level it is in
        self.offer_to_level = {}
        for level in self.levels:
            for order in level.orders:
                self.offer_to_level[order.id] = level

        # TODO: decide if this is the best path forward
        # for ease of use, we will store a dictionary that maps every price to the level it is in
        self.price_to_level = {}
        for level in self.levels:
            self.price_to_level[level.price] = level

        @classmethod
        def from_rubicon_offers(
            cls,
            book_side: OrderSide,
            offers: List[LimitOrder]
        ):
            """Creates a DetailedBookSide instance from a list of LimitOrders.
            
            :param book_side: The side of the order book (BUY or SELL).
            :type book_side: OrderSide
            :param offers: The list of offers retrieved from the Rubicon for an asset pair pay_gem/buy_gem.
            """

            # go through and get every price level that we will need
            levels = {}

            for order in offers:
                if order.price in levels:
                    levels[order.price].append(order)
                else:
                    levels[order.price] = []

            # construct the levels list
            levels_list = []
            for price, orders in levels.items():
                levels_list.append(DetailedBookLevel.from_rubicon_offers(orders))

            # sort the levels list based on the book side
            match book_side:
                case OrderSide.BUY:
                    levels_list = sorted(
                        levels_list, 
                        key=lambda level: level.price, 
                        reverse=True
                    )
                case OrderSide.SELL:
                    levels_list = sorted(
                        levels_list, 
                        key=lambda level: level.price
                    )

            return cls(
                book_side=book_side,
                levels=levels_list
            )
        
        def add_order(
            self, 
            order: LimitOrder
        ):
            """Add an order to the detailed book side.
            
            :param order: The order to add to the detailed book side.
            :type order: LimitOrder
            """

            if order.price in self.price_to_level:
                self.price_to_level[order.price].add_order(order)
                self.offer_to_level[order.id] = self.price_to_level[order.price]
            else:
                self.price_to_level[order.price] = DetailedBookLevel.from_rubicon_offers([order])
                self.offer_to_level[order.id] = self.price_to_level[order.price]

        # remove_liquidity_from_book is inherited from BookSide
        # def remove_liquidity_from_book(self, price: Decimal, size: Decimal):

        # best_price is inherited from BookSide
        # def best_price(self) -> Decimal: