import logging as log
from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy
from typing import Union, List, Optional, Dict, Type, Any, Callable

from rubi.network import (
    Network,
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
        network: Optional[Network] = None
    ): 
        """constructor method"""
        self.sg = subgrounds
        self.subgraph_url = subgraph_url
        self.network = network # type: Network | None

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
        subgrounds: Subgrounds, 
        network: Network
    ): 
        
        """Initialize a MarketData object using a Network object."""
        return cls(
            subgrounds=subgrounds,
            subgraph_url=network.market_data_url,
            network=network
        )
    
    #####################################
    # Subgraph Query Methods (raw data) #
    #####################################

    # TODO: refractor using a decorator to handle the parameter validation
    def get_offers_raw(
        self, 
        maker: Optional[str] = None,
        from_address: Optional[str] = None,
        pay_gem: Optional[str] = None,
        buy_gem: Optional[str] = None,
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        first: Optional[int] = 1000,
        order_by: Optional[str] = 'timestamp',
        order_direction: Optional[str] = 'desc'
        ): 
        """Returns a dataframe of offers placed on the market contract, with the option to pass in filters.

        :param maker: the address of the maker of the offer
        :type maker: str
        :param from_address: the address that originated the transaction that created the offer
        :type from_address: str
        :param pay_gem: the address of the token that the maker is offering
        :type pay_gem: str
        :param buy_gem: the address of the token that the maker is requesting
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
        :return: a dataframe of offers placed on the market contract
        :rtype: pd.DataFrame 
        """

        # set the offer entity 
        Offer = self.data.Offer

        # set the order_by parameter
        if order_by.lower() not in ('timestamp', 'price'):
            raise ValueError("Invalid order_by, must be 'timestamp' or 'price'")
        elif order_by.lower() == 'timestamp':
            order_by = Offer.timestamp
        elif order_by.lower() == 'price':
            order_by = Offer.price

        # set the order_direction parameter
        if order_direction.lower() not in ('asc', 'desc'):
            raise ValueError("Invalid order_direction, must be 'asc' or 'desc'")
        else: 
            order_direction = order_direction.lower()

        # build the list of where conditions
        where = [
            Offer.maker == maker.lower() if maker else None,
            # TODO: rename the subgraph field from 'from' to 'from_address' to avoid python keyword conflict (https://github.com/RubiconDeFi/rubi-subgraphs/issues/11)
            # Offer.from == from_address.lower() if from_address else None,
            Offer.pay_gem == pay_gem.lower() if pay_gem else None,
            Offer.buy_gem == buy_gem.lower() if buy_gem else None,
            Offer.live == open if open is not None else None,
            Offer.timestamp >= start_time if start_time else None,
            Offer.timestamp <= end_time if end_time else None
        ]
        where = [condition for condition in where if condition is not None]

        offers = self.data.Query.offers(
            orderBy = order_by,
            orderDirection = order_direction,
            first=first,
            where = where if where else {}
        )

        fields = [
            offers.id,
            offers.timestamp,
            offers.index,
            offers.maker.id,
            # offers.from.id,
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

        df = self.sg.query_df(
            fields,
            pagination_strategy=ShallowStrategy
        )

        # TODO: handle an empty dataframe
        # TODO: standardize the column names
        
        return df