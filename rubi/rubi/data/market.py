import pandas as pd
import logging as log
from datetime import datetime
from subgrounds import Subgrounds
from subgrounds.subgraph import SyntheticField
from subgrounds.pagination import ShallowStrategy
from typing import Union, List, Optional, Dict, Type, Any, Callable

from rubi.rubicon_types.order import (
    OrderSide,
)

from rubi.network import (
    Network,
)

from rubi.contracts import (
    ERC20,
)

class MarketData: 
    """This class represents the RubiconV2 Subgraph, which contains data primarily related to the RubiconMarket.sol contract.
    If a Network object is not passed in instantiation then this class will only be used to query data related to the subgraph.
    
    :param subgrounds: a Subgrounds instance 
    :type subgrounds: Subgrounds
    param subgraph_url: a RubiconV2 Subgraph url endpoint that should be utilized for this class
    :type subgraph_url: str
    :param network: a Network object, native to the package
    :type network: Network
    """

    def __init__(
        self, 
        subgrounds: Subgrounds,
        subgraph_url: str,
        network: Optional[Network] = None # we could just require a web3 connection, but this is more convenient 
    ): 
        """constructor method"""
        self.sg = subgrounds
        self.subgraph_url = subgraph_url
        self.network = network # type: Network | None

        # TODO: we probably won't do this here, but we should figure out where to store the token's for the class
        self.tokens = self.get_network_tokens(self.network) if self.network else None

        # create a token map that maps the token address (lowercase) to the token object
        self.token_map = {token.address.lower(): token for token in self.tokens} if self.tokens else None

        # initialize the subgraph 
        try: 
            self.data = self.sg.load_subgraph(self.subgraph_url)
            # TODO: we should add a check here to guarantee the schema matches what we expect to be receiving
        except: 
            # TODO: not sure exactly what error we should be throwing here, this is if the url does not work 
            raise ValueError(f"subgraph_url: {subgraph_url} failed when attempting to load.")
        
    @classmethod
    def from_network(
        cls,
        network: Network
    ) -> "MarketData": 
        
        """Initialize a MarketData object using a Network object."""
        return cls(
            subgrounds=network.subgrounds,
            subgraph_url=network.market_data_url,
            network=network
        )
    
    #####################################
    # General Helper Methods             # TODO: we will want to move this somewhere else most likely
    #####################################

    # TODO: FIGURE OUT WHERE THIS GOES, i think we probably want all of the token addresses initialized as a class object somewhere, but i also 
    # think that when people start building extremely long token lists that we may not want to do this by default
    # maybe it goes on the network object? or the client?

    def get_network_tokens(
            self, 
            network: Optional[Network] = None 
    ) -> List[ERC20] : # TODO: determine what type to return here, probably a list of ERC20 objects
        
        """Returns a list of ERC20 objects for all tokens on the network."""
        if network: 
            token_addresses = network.token_addresses
        elif self.network:
            token_addresses = self.network.token_addresses
        else:
            raise ValueError("No network object passed and no network object initialized on the class.")
        
        tokens = [ERC20.from_network(name=address, network=self.network) for address in token_addresses]

        return tokens
    
    def get_token(
            self,
            token_address: str
    ) -> ERC20:
        """Returns an ERC20 object for the token address passed from the token_map if it exists or add it to the token_map if it does not exist."""

        if not self.network:
            raise ValueError("No network object initialized on the class.")
        else: 

            try: 
                token_address = self.network.w3.to_checksum_address(token_address)
                token_address = token_address.lower()

                if token_address not in self.token_map:
                    self.token_map[token_address] = ERC20.from_network(address=token_address, network=self.network)
                
                return self.token_map[token_address]

            except:
                raise ValueError(f"Token address: {token_address} is invalid.")
    
    #####################################
    # Query Helper Methods              # # TODO: we will want to move these to their own class most likely
    #####################################

    # TODO: we will probably actually want to move this to the class constructor if it behaves as expected
    def offer_entity(
        self,  
    ): # TODO: return a typed object (see subgrounds documentation for more info)
        
        Offer = self.data.Offer

        # if we have a network object we can get all the token information we need
        if self.network: 

            Offer.pay_amt_formatted = SyntheticField(
                f=lambda pay_amt, pay_gem: self.get_token(pay_gem).to_decimal(pay_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.pay_amt, Offer.pay_gem],
            )

            Offer.buy_amt_formatted = SyntheticField(
                f=lambda buy_amt, buy_gem: self.get_token(buy_gem).to_decimal(buy_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.buy_amt, Offer.buy_gem],
            )

            Offer.paid_amt_formatted = SyntheticField(
                f=lambda paid_amt, pay_gem: self.get_token(pay_gem).to_decimal(paid_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.paid_amt, Offer.pay_gem],
            )

            Offer.bought_amt_formatted = SyntheticField(
                f=lambda bought_amt, buy_gem: self.get_token(buy_gem).to_decimal(bought_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.bought_amt, Offer.buy_gem],
            )

            Offer.pay_gem_symbol = SyntheticField(
                f=lambda pay_gem: self.get_token(pay_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Offer.pay_gem],
            )

            Offer.buy_gem_symbol = SyntheticField(
                f=lambda buy_gem: self.get_token(buy_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Offer.buy_gem],
            )

            Offer.datetime = SyntheticField(
                f=lambda timestamp: str(datetime.fromtimestamp(timestamp)),
                type_=SyntheticField.STRING,
                deps=[Offer.timestamp],
            )
        
        return Offer

    def offers_query(
        self,
        offer, # TODO: determine what type this should be (subgrounds may have types that we can utilize here)
        order_by: str, 
        order_direction: str,
        first: int,
        maker: Optional[str] = None,
        from_address: Optional[str] = None,
        pay_gem: Optional[str] = None, 
        buy_gem: Optional[str] = None, 
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        # TODO: there is definitely a clear way to pass these parameters in a more concise way, prolly **kargs   
    ): # TODO: return a typed object (see subgrounds documentation for more info)
        
        # determine that the parameters are valid
        error_messages = []

        # check the order_by parameter
        if order_by.lower() not in ('timestamp', 'price'):
            error_messages.append("Invalid order_by, must be 'timestamp' or 'price' (default: timestamp)")
        elif order_by.lower() == 'timestamp':
            order_by = offer.timestamp
        elif order_by.lower() == 'price':
            order_by = offer.price
        
        # check the order_direction parameter
        if order_direction.lower() not in ('asc', 'desc'):
            error_messages.append("Invalid order_direction, must be 'asc' or 'desc' (default: desc)")
        else:
            order_direction = order_direction.lower()

        # check the first parameter
        if first < 1:
            error_messages.append("Invalid first, must be greater than 0 (default: 1000)")
        if not isinstance(first, int):
            error_messages.append("Invalid first, must be an integer (default: 1000)")
        
        # raise an error if there are any
        if error_messages:
            raise ValueError('\n'.join(error_messages))
        
        # build the list of where conditions
        where = [
            offer.maker == maker.lower() if maker else None,
            offer.from_address == from_address.lower() if from_address else None,
            offer.pay_gem == pay_gem.lower() if pay_gem else None,
            offer.buy_gem == buy_gem.lower() if buy_gem else None,
            offer.open == open if open is not None else None,
            offer.timestamp >= start_time if start_time else None,
            offer.timestamp <= end_time if end_time else None
        ]
        where = [condition for condition in where if condition is not None]
    
        """Helper method to build a query for the offers subgraph entity."""
        offers = self.data.Query.offers(
            orderBy = order_by,
            orderDirection = order_direction,
            first=first,
            where = where if where else {}
        )

        return offers
    
    def offers_fields(
        self,
        offers: Any, # TODO: check that this is the correct type (subgrounds may have types that we can utilize here)
        formatted: bool = False
    ): # TODO: return a typed object (see subgrounds documentation for more info)
        
        """Helper method to build a list of fields for the offers subgraph entity."""
        fields = [
            offers.id,
            offers.timestamp,
            offers.index,
            offers.maker.id,
            offers.from_address.id,
            offers.pay_gem,
            offers.buy_gem,
            offers.pay_amt,
            offers.buy_amt,
            offers.paid_amt,
            offers.bought_amt,
            offers.price,
            offers.open,
            offers.removed_timestamp,
            offers.removed_block,
            offers.transaction.id,
            offers.transaction.block_number,
            offers.transaction.block_index
        ]

        if formatted:
            fields.append(offers.pay_amt_formatted)
            fields.append(offers.buy_amt_formatted)
            fields.append(offers.paid_amt_formatted)
            fields.append(offers.bought_amt_formatted)
            fields.append(offers.pay_gem_symbol)
            fields.append(offers.buy_gem_symbol)
            fields.append(offers.datetime)

        return fields
    
    def query_offers(
            self,
            fields: List, 
            formatted: bool = False,
            # TOOD: maybe we give the user the option to define a custom pagination strategy?
    ): # TODO: return a typed object (see subgrounds documentation for more info)
        """Helper method to query the offers subgraph entity."""
        df =  self.sg.query_df(
            fields,
            pagination_strategy=ShallowStrategy
        ) 

        # if the dataframe is empty, return an empty dataframe with the correct columns
        if df.empty and not formatted:
            cols = ['id', 'timestamp', 'index', 'maker', 'from_address', 'pay_gem',
                'buy_gem', 'pay_amt', 'buy_amt', 'paid_amt', 'bought_amt', 'price',
                'open', 'removed_timestamp', 'removed_block', 'transaction', 
                'transaction_block_number', 'transaction_block_index']
            df = pd.DataFrame(columns=cols)

        elif df.empty and formatted:
            cols = ['id', 'maker', 'from_address', 'pay_gem', 'buy_gem', 'pay_amt', 'buy_amt', 'paid_amt', 'bought_amt']
            df = pd.DataFrame(columns=cols)
        
        else: 
            df.columns = [col.replace('offers_', '') for col in df.columns]
            df.columns = [col.replace('_id', '') for col in df.columns]
            
            # convert the id to an integer
            df['id'] = df['id'].apply(lambda x: int(x, 16)) # TODO: i don't love the lambda (cc pickling, but it appears we are forced to use them in sythetic fields regardless)

            # TODO: decide whether we should return the unformatted fields or not
            if formatted:
                print('the formmatkalkakdklj')
                df = df.drop(columns=['pay_amt', 'buy_amt', 'paid_amt', 'bought_amt', 'pay_gem', 'buy_gem', 'timestamp', 'index', 'price', 'removed_timestamp', 'removed_block', 'transaction_block_number', 'transaction_block_index'])
                df = df.rename(columns={'pay_amt_formatted': 'pay_amt', 'buy_amt_formatted': 'buy_amt', 'paid_amt_formatted': 'paid_amt', 'bought_amt_formatted': 'bought_amt', 'pay_gem_symbol': 'pay_gem', 'buy_gem_symbol': 'buy_gem', 'datetime': 'timestamp'})
                # TODO: we could also get smart with displaying price dependent upon the pair_name and direction of the order
            
        # TODO: apply any data type conversions to the dataframe - possibly converting unformatted values to integers   
        return df
    
    #####################################
    # Subgraph Query Methods (raw data) #
    #####################################

    # TODO: refractor using a decorator to handle the parameter validation
    def get_offers(
        self, 
        maker: Optional[str] = None,
        from_address: Optional[str] = None,
        pair_name: Optional[str] = None,
        book_side: Optional[OrderSide] = None,
        pay_gem: Optional[str] = None, # TODO: maybe we should allow the user to pass in an address here?
        buy_gem: Optional[str] = None, # TODO: maybe we should allow the user to pass in an address here?
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        first: Optional[int] = 1000,
        order_by: Optional[str] = 'timestamp',
        order_direction: Optional[str] = 'desc',
        formatted: Optional[bool] = False
        ) -> pd.DataFrame: 
        """Returns a dataframe of offers placed on the market contract, with the option to pass in filters.

        :param maker: the address of the maker of the offer
        :type maker: str
        :param from_address: the address that originated the transaction that created the offer
        :type from_address: str
        :param pay_gem: the address of the token that the maker is offering (will override pair_name if both are passed)
        :type pay_gem: str
        :param buy_gem: the address of the token that the maker is requesting (will override pair_name if both are passed)
        :type buy_gem: str
        :param open: whether or not the offer is still active
        :type open: bool
        :param start_time: the timestamp of the earliest offer to return
        :type start_time: int
        :param end_time: the timestamp of the latest offer to return
        :type end_time: int
        :param first: the number of offers to return
        :type first: int
        :param order_by: the field to order the offers by (default: timestamp, options: timestamp, price) TODO: expand this list
        :type order_by: str
        :param order_direction: the direction to order the offers by (default: desc, options: asc, desc)
        :type order_direction: str
        :param formatted: whether or not to return the formatted fields (default: False, requires a network object to be passed)
        :return: a dataframe of offers placed on the market contract
        :rtype: pd.DataFrame 
        """

        # set the offer entity 
        Offer = self.offer_entity()

        # if we want formatted fields, make sure we have a network object
        # TODO: we could pass this to the offers_query method and handle it there - if we start to utilize something like **kargs lets do that
        if formatted and not self.network:
            raise ValueError("Cannot return formatted fields without a network object initialized on the class.")

        # handle the pair_name parameter
        if pair_name:
            base, quote = pair_name.split("/")
            base_asset = ERC20.from_network(name=base, network=self.network)
            quote_asset = ERC20.from_network(name=quote, network=self.network)

        # handle the book_side parameter
        if book_side and pair_name:
            
            match book_side:
                case OrderSide.BUY:
                    buy_query = self.offers_query(Offer, order_by, order_direction, first, maker, from_address, pay_gem = quote_asset.address, buy_gem = base_asset.address, open = open, start_time = start_time, end_time = end_time)
                    buy_fields = self.offers_fields(buy_query, formatted)
                    buy_df = self.query_offers(buy_fields, formatted)
                    buy_df['side'] = 'buy' # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    return buy_df

                case OrderSide.SELL:
                    sell_query = self.offers_query(Offer, order_by, order_direction, first, maker, from_address, pay_gem = base_asset.address, buy_gem = quote_asset.address, open = open, start_time = start_time, end_time = end_time)
                    sell_fields = self.offers_fields(sell_query, formatted)
                    sell_df = self.query_offers(sell_fields, formatted)
                    sell_df['side'] = 'sell' # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    return sell_df

                case OrderSide.NEUTRAL:
                    buy_query = self.offers_query(Offer, order_by, order_direction, first, maker, from_address, pay_gem = quote_asset.address, buy_gem = base_asset.address, open = open, start_time = start_time, end_time = end_time)
                    buy_fields = self.offers_fields(buy_query, formatted)
                    buy_df = self.query_offers(buy_fields, formatted)
                    buy_df['side'] = 'buy' # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    sell_query = self.offers_query(Offer, order_by, order_direction, first, maker, from_address, pay_gem = base_asset.address, buy_gem = quote_asset.address, open = open, start_time = start_time, end_time = end_time)
                    sell_fields = self.offers_fields(sell_query, formatted)
                    sell_df = self.query_offers(sell_fields, formatted)
                    sell_df['side'] = 'sell' # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    # TODO: decide what we want to do here, maybe we just return both dataframes?

                    # reset the index  # need to pass a somewhat more complicated ordering here to comply with what happened in the same block time
                    return pd.concat([buy_df, sell_df]).reset_index(drop=True)

        # handle the pay_gem and buy_gem parameters
        elif pay_gem and buy_gem:

            query = self.offers_query(Offer, order_by, order_direction, first, maker, from_address, pay_gem = pay_gem, buy_gem = buy_gem, open = open, start_time = start_time, end_time = end_time)
            fields = self.offers_fields(query)
            df = self.query_offers(fields)

            return df
