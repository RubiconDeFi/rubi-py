import json
import logging as log
from web3 import Web3
from attributedict.collections import AttributeDict

from rubi.book import Book
import rubi.contracts as contracts
from rubi.contracts.helper import networks
from rubi.data import Data, SuperData

class RubiconData:
    """this class serves to tie in the various data sources and tooling for the Rubicon protocol that can be collected without a node connection. the Rubicon class inherits the functionality of this data class while adding the ability to interact with the contracts. more to come soon!
    """

    def __init__(self, w3=None):
        """initializes the data class, if a web3 instance is provided, it will also initialize the super data class. more to come soon!"""
        if w3:
            self.data = SuperData(w3)
        else:
            self.data = Data()


class Rubicon(RubiconData):
    """this class serves as a the main entry point to the repository. it acts as the initialization of multiple contract instances, and give access to the various functions of the contracts. it also provides a few helper functions to make interacting with the contracts easier. more to come soon!
    
    :param w3: a web3 instance
    :type w3: Web3
    :param wallet: the wallet address of the user, defaults to None
    :type wallet: str, optional
    :param key: the private key of the user, defaults to None
    :type key: str, optional
    :param market: a market contract object, defaults to None
    :type market: str, optional
    :param router: a router contract object, defaults to None
    :type router: str, optional
    :param factory: a factory contract object, defaults to None
    :type factory: str, optional
    """

    def __init__(self, w3, wallet=None, key=None, market=None, router=None, factory=None):
        
        # initialize the data class
        super().__init__(w3)

        # load required variables
        chain = w3.eth.chain_id

        try:
            network = networks[chain]()
        except:
            network = 'unknown'

        # set class variables 
        self.w3 = w3
        self.chain = chain
        self.network = network

        self.key = key
        self.wallet = wallet

        # if wallet and key are provided then create signer instances 
        if wallet and key:
            self.market = contracts.RubiconMarketSigner(w3, wallet, key, contract=market)
            self.router = contracts.RubiconRouterSigner(w3, wallet, key, contract=router)
            self.factory = contracts.FactoryAidSigner(w3, wallet, key, contract=factory)
        else:
            self.market = contracts.RubiconMarket(w3, contract=market)
            self.router = contracts.RubiconRouter(w3, contract=router)
            self.factory = contracts.FactoryAid(w3, contract=factory)

        # set the hashes of the event emits
        self.log_make_hash = self.market.get_log_make_hash()
        self.log_take_hash = self.market.get_log_take_hash()
        self.log_kill_hash = self.market.get_log_kill_hash()
        self.offer_deleted_hash = self.market.get_offer_deleted_hash()
        self.log_swap_hash = self.router.get_log_swap_hash()

        # create a dictionary to map market event emits to their respective functions
        self.market_events = {
            self.log_make_hash : self.market.stream_log_make,
            self.log_take_hash : self.market.stream_log_take,
            self.log_kill_hash : self.market.stream_log_kill
        }

        # create a dictionary to store the market books that are being tracked 
        self.books = {}

    ######################################################################
    # read calls
    ######################################################################

    # a function that will identify the event topic and call the appropriate function
    def parse_market_events(self, event): 
        """a function to parse event emits from the market contract and call the appropriate function to handle the event

        :param event: the event emit from the market contract
        :type event: dict
        :return: the parsed event
        :rtype: dict
        """

        data = AttributeDict(json.loads(event))

        try: 
            parsed = self.market_events[data.params.result.topics[0]](data)
        except:
            return None

        return parsed

    # a function to return all offers for a given token pair, at the depth of the direction specified
    def get_offers(self, token0, token1):
        """a function to return all offers for a given token pair, at the depth of the direction specified

        :param token0: the address of the pay token in the offer pair
        :type token0: str
        :param token1: the address of the buy token in the offer pair
        :type token1: str
        :return: a double array of offers, the first being the offers for token0 = pay token and token1 = buy token, the second being the offers for token0 = buy token and token1 = pay token. [[[token0_amount, token_1_amount, offer_id]], [[token1_amount, token0_amount, offer_id]], depth]
        :rtype: list
        """

        # get the number of orders in the book for the given token pair
        offer_count = self.market.get_offer_count(token0, token1)

        # get the sorted orders in the book for the given token pair
        book = self.router.get_book_from_pair(token0, token1, offer_count)

        return book 

    # a function that will either create a new book or return an existing book based upon the pair 
    def get_book(self, token0, token1): 
        """a function that will either create a new book or return an existing book that is being tracked for the pair
        
        :param token0: the address of the pay token in the offer pair
        :type token0: str
        :param token1: the address of the buy token in the offer pair
        :type token1: str
        :return: a book object
        :rtype: Book
        """

        # create the pair key 
        key = str(token0) + '/' + str(token1)

        # check if the book exists
        if key in self.books:
            return self.books[key]
        else:
            book = Book(token0, token1)
            book.populate(self.get_offers(token0, token1)[0])
            self.books[key] = book
            return book
        
    def populate_book(self, token0, token1):
        """a function to populate a book with the current offers in the market

        :param token0: the address of the pay token in the offer pair
        :type token0: str
        :param token1: the address of the buy token in the offer pair
        :type token1: str
        """

        book = self.get_book(token0, token1)
        book.populate(self.get_offers(token0, token1)[0])

        return book

    ######################################################################
    # write calls
    ######################################################################

    # a function to create and pass back an ERC20 token instance
    # TODO: add support for a contract instance
    def token(self, token_address):
        """a function to create and pass back an ERC20 token instance

        :param token_address: the address of the token
        :type token_address: str
        :return: an ERC20 token instance
        :rtype: token.Token
        """

        if self.wallet and self.key:
            return contracts.helper.ERC20Signer(self.w3, token_address, self.wallet, self.key, contract=None)
        else:
            return contracts.helper.ERC20(self.w3, token_address, contract=None)

    # a function to create and pass back a market aid instance
    def aid(self, address, contract=None):
        """a function to create and pass back a market aid instance

        :param address: the address of the market aid contract
        :type address: str
        :param contract: a market aid contract instance, defaults to None
        :type contract: class, optional
        :return: a market aid instance
        :rtype: aid.Aid
        """

        if self.wallet and self.key:
            return contracts.MarketAidSigner(self.w3, address, self.wallet, self.key, contract=contract)
        else:
            return contracts.MarketAid(self.w3, address, contract=contract)