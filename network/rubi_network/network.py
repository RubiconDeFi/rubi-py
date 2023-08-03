from typing import Optional, Dict, Union, List

import pandas as pd

from .data import BookHistory



# TODO: this should contain everything needed to spin up a PyEVMBackend preconfigured per network 
class Network: # TODO: i feel like this may have conflict with networkx naming somewhere

    def __init__(
        self, 
        graph, # TODO: not sure what type this is from networkx
        client, # TODO: we will want to uncouple this dependence upon the rubi-client, but for now need it for the ERC20 objects.
        pair_names: List[str],
        book_histories: Dict[str, BookHistory],
        # TODO: we will probably end up supporting multiple graph versions as we progress in the level of detail contained in each 
    ): 
        
        #self.graph = graph
        self.pair_names = pair_names
        self.book_histories = book_histories

    # TODO: assumes that pair_name, period, etc. align on the same index
    @classmethod
    def from_df(
        cls, 
        client,
        pair_names: List[str],
        offers: List[pd.DataFrame],
        trades: List[pd.DataFrame],
    ): 
        
        # check that they all match
        # TODO: we could also check the dataframes
        if len(pair_names) != len(offers) != len(trades): 
            raise Exception("Error: array lengths do not match")
        
        book_histories = {} 
        for i in range(len(pair_names)):
            book_history = BookHistory(
                client=client,
                offers=[],
                trades=[],
                cancels=[],
                history={}
            )

            book_history.from_df(
                pair_name=[pair_names[i]],
                offers=[offers[i]],
                trades=[trades[i]]
            )

            book_histories[pair_names[i]] = book_history

        return cls(
            graph=None,
            client=client,
            pair_names=pair_names, 
            book_histories=book_histories
        )
    
    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    
