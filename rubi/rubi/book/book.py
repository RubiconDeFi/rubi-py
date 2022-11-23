# an order book manager for the world order book
# this will be improved by hands more skilled than mine, but i hope it will be useful until that day comes 

import logging as log

class Book: 
    """this class represents an order book for a single pair of tokens. it is initialized with the token pair and can be populated with orders. it can also be updated with new orders, order fills, and order removals. it is intended to be used as a data structure to facilitate the in memory representation of the world order book.

    :param token0: the address of the pay token
    :type token0: str
    :param token1: the address of the buy token
    :type token1: str
    """

    # the basic idea here is that we will keep a list of sorted order ids that map to a dictionary of order details

    # initialize the book
    def __init__(self, token0, token1):
        """constructor method"""

        # set the token pair
        self.token0 = token0
        self.token1 = token1

        # initialize the order list
        self.orders = []

        # initialize the order details dictionary
        self.details = {}

    # a function to populate the book with orders for the pair from the market
    def populate(self, book):
        """populates the book class with orders and order details 

        :param book: an array of order objects, in the format of [[token0_amount, token1_amount, order_id], ...]
        :type book: list
        """

        # iterate through the list of orders to populate the list and details dictionary
        for order in book[0]:

            # add the order id to the list 
            self.orders.append(order[2])

            # populate the details dictionary with the order details
            self.details[order[2]] = [order[0], order[1]]

    # a function to add a new order to the book 
    def add(self, order_id, token0_amt, token1_amt): 
        """adds a new order to the book class 

        :param order_id: the id of the order to add
        :type order_id: int
        :param token0_amt: the amount the order is willing to pay in token0
        :type token0_amt: int
        :param token1_amt: the amount the order is willing to pay in token1
        :type token1_amt: int
        :returns: True if the update was successful, False otherwise
        :rtype: bool
        """

        # add the order details to the dictionary 
        self.details[order_id] = [token0_amt, token1_amt]

        # now determine where to insert the order id in the sorted list 
        for i in range(len(self.orders)):

            # if the order is a better price insert it before the current order
            if ((token0_amt / token1_amt) * (self.details[self.orders[i]][1] / self.details[self.orders[i]][0])) >= 1:

                self.orders.insert(i, order_id)
                return True

        # if the order is the worst price insert it at the end of the list
        self.orders.append(order_id)

        log.info('adding order %s to book', order_id)

        return True

    # a function to update fill on an order
    def fill(self, order_id, token0_fill, token1_fill):
        """updates an order in the book class with a fill

        :param order_id: the id of the order to update
        :type order_id: int
        :param token0_fill: the amount of token0 that was payed 
        :type token0_fill: int
        :param token1_fill: the amount of token1 that was received 
        :type token1_fill: int
        :returns: True if the update was successful, False otherwise
        :rtype: bool
        """

        # update the order details
        try: 
            self.details[order_id][0] -= token0_fill
            self.details[order_id][1] -= token1_fill
        except Exception as e:
            log.error('unable to fill order %s', e)
            return False

        # if the order is filled remove it from the book
        if self.details[order_id][0] == 0 and self.details[order_id][1] == 0:

            try:
                self.remove(order_id, 0, 0)
            except Exception as e:
                log.error('unable to remove order %s after fill', e)
                return False

        log.info('filling order %s in book', order_id)

        return True

    # a function to remove an order from the book
    # TODO: the token amounts are not needed here, but they are currently here to ensure consistency with the other functions and data structures in the repo
    def remove(self, order_id, token0_amt, token1_amt):
        """removes an order from the book class

        :param order_id: the id of the order to remove
        :type order_id: int
        :param token0_amt: the pay amount remaining on the order
        :type token0_amt: int
        :param token1_amt: the buy amount remaining on the order
        :type token1_amt: int
        :returns: True if the update was successful, False otherwise
        :rtype: bool
        """

        # remove the order
        try:
            self.orders.remove(order_id)
            self.details.pop(order_id)
        except Exception as e:
            log.error('unable to remove order %s', e)
            return False

        log.info('removing order %s from book', order_id)

        return True

    # a function to take a parsed order and update the book accordingly
    # TODO: i think this could be better, specifically i think we should be able to pass the book object throughout the function calls to be updated
    # determining the structure of this book object in the larger context of the repo will be a problem to solve later
    # a current shortcoming of the market contract is offer deleted does not return any details on the pair, just the order id - because of this we are only checking to delted filled orders through checks on fill 
    def stream_update(self, parsed):
        """updates the book class with a parsed order object
        
        :param parsed: a parsed order object, each dictionary contains at the mininum the event type, order id, pay token amount, and buy token amount
        :type parsed: dict
        :returns: True if the update was successful, False otherwise
        :rtype: bool
        """

        # set the dictionary to determine the function to call based on the event type
        event_dict = {
            'LogMake' : self.add,
            'LogTake' : self.fill,
            'LogKill' : self.remove
        }
        
        try: 
            event_dict[parsed['event']](parsed['id'], parsed['pay_amt'], parsed['buy_amt'])
        except Exception as e:
            log.error('something has gone wrong in our stream update: %s', e)
            return False

        log.info('updating book with %s: %s', parsed['event'], parsed['id'])
        
        return True