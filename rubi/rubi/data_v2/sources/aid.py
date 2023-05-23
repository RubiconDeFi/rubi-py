from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy
from typing import List, Optional
import polars as pl
import pandas as pd

from rubi.data_v2.sources.helper import Rolodex, TokenList

class MarketAid:
    """this class acts as an access point for data from MarketAid.sol contracs"""

    def __initi__(self, subgrounds):
        """constructor method, handles the initialization of the subgraph objects across various networks"""

        # set common class objects 
        self.subgrounds = subgrounds
        self.rolodex = Rolodex()
        self.token_list = TokenList()

        # set the market aid subgraph objects
        self.op_main_market_aid = self.subgrounds.load_subgraph()

        # create token lists for each network 
        # TODO: this is a temporary solution, we will want to handle this in a more scalable way in the future
        self.op_main_token_list = self.token_list.get_optimism_token_list('optimism')

        # a dictionary to easily access the subgraph objects
        self.subgraphs = {
            'optimism': self.op_main_v2,
            'optimism_goerli': self.op_goerli_v2,
            'arbitrum_goerli': self.arb_goerli_v2,
            'polygon_mumbai': self.polygon_mumbai_v2
        }

        self.token_lists = {
            'optimism': self.op_main_token_list
        }

    # TODO: for today, we are only going to focus on doing a single network query at a time. in the future, we will want to be able to query multiple networks at once (in parallel) and then merge the results together 
    def get_balances(
            self, 
            network: str = 'optimism', # TODO: we may not want to set this as a default, but instead require it to be set
            aid: Optional[str] = None,
    )
