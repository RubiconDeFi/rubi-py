import logging as log
from subgrounds import Subgrounds
from typing import Union, List, Optional, Dict, Type, Any, Callable

from rubi.data.sources import (
    MarketData,
)

from rubi.network import (
    Network,
)

# TODO: in the future, we will need to handle the need to query the decentralized network, requiring a wallet + GRT

class Data: 
    """This class is meant to be a data access layer for the Rubicon protocol and its associated subgraphs.
    It aims to provide a simple and understandable interface when retreiving both live and historical data.
    
    """

    def __init__(
        self, 
        market_data_url: str,
        network: Optional[Network] = None
    ): 
        
        """constructor method"""
        self.sg = Subgrounds()
        self.market_data_url = market_data_url
        self.network = network # type: Network | None

        #####################################
        # Initialize Subgraph Query Methods #
        #####################################
        self.market = MarketData(self.sg, self.market_data_url, self.network)

    @classmethod
    def from_network(
        cls, 
        network: Network
    ):
        """Initialize a Data object using a Network object."""
        return cls(
            market_data_url=network.market_data_url,
            network=network
        )