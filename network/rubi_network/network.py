from typing import Optional, Dict, Union, List

import pandas as pd
import networkx as nx

from .data import BookHistory, Cancel, TraderNode, Edge

from rubi import LimitOrder, Trade

# TODO: this should contain everything needed to spin up a PyEVMBackend preconfigured per network 
class Network: # TODO: i feel like this may have conflict with networkx naming somewhere

    def __init__(
        self, 
        client, # TODO: we will want to uncouple this dependence upon the rubi-client, but for now need it for the ERC20 objects.
        graphs, # TODO: not sure what type this is from networkx
        pair_names: List[str],
        book_histories: Dict[str, BookHistory],
        # TODO: we will probably end up supporting multiple graph versions as we progress in the level of detail contained in each 
    ): 
        
        self.graphs = {} # TODO: we will probably want to support multiple graph types
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
            graphs=None,
            client=client,
            pair_names=pair_names, 
            book_histories=book_histories
        )
    
    def add_graph(
        self, 
        pair_name: str,
        # graph_type
    ): 
        
        self.graphs[pair_name] = nx.Graph() # TODO: we will probably want to support multiple graph types

    def build_graph(
        self, 
        pair_name: str,
        # graph_type
        # book_history
    ):
        
        # try to get the book history
        book_history = self.book_histories.get(pair_name)
        if book_history is None:
            raise Exception("Error: book history not found")
        
        book = book_history.book
        history = book_history.history
        
        # try to get the graph
        graph = self.graphs.get(pair_name)
        if graph is None:
            self.add_graph(pair_name=pair_name)
            graph = self.graphs.get(pair_name)

        # get the blocks and sort them 
        blocks = list(history.keys())
        blocks.sort()

        # go through and handle each scenario 
        for block in blocks: 

            # get the block indexes and sort them
            block_indexes = list(history[block].keys())
            block_indexes.sort()

            for block_index in block_indexes:

                # get the event indexes and sort them
                event_indexes = list(history[block][block_index].keys())
                event_indexes.sort()

                for event_index in event_indexes:

                    event = history[block][block_index][event_index]

                    if isinstance(event, LimitOrder):
                        maker = event.from_address
                        
                        if maker not in graph:
                            graph.add_node(maker, data=TraderNode(
                                trader_id=maker,
                                book=book,
                            ))
                        graph.nodes[maker]['data'].add_order(event)

                    elif isinstance(event, Trade):
                        taker = event.from_address
                        # maker = event.offer_from_address
                        order = book.get_order(event.order_id)
                        maker = order.from_address

                        # update the taker node
                        if taker not in graph:
                            graph.add_node(taker, data=TraderNode(
                                trader_id=taker,
                                book=book,
                            ))
                        graph.nodes[taker]['data'].add_market_order(event)

                        # update the maker node
                        if maker not in graph:
                            graph.add_node(maker, data=TraderNode(
                                trader_id=maker,
                                book=book,
                            ))
                        graph.nodes[maker]['data'].add_fill_trade(event)

                        # update the edge
                        if not graph.has_edge(maker, taker):
                            graph.add_edge(maker, taker, data=Edge())
                        graph.edges[maker, taker]['data'].add_market_order(event)

                    elif isinstance(event, Cancel):
                        book.remove_order(event.id)
        
    
    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    
