from typing import Optional, Dict, Union, List

import pandas as pd
from rubi import OrderSide, Trade, LimitOrder, DetailedOrderBook

class Cancel: 

    def __init__(
        self,
        id: Optional[int] = None,
        block_number: Optional[int] = None,
        block_index: Optional[int] = None,
        log_index: Optional[int] = None,
    ):
        
        self.id = id
        self.block_number = block_number
        self.block_index = block_index
        self.log_index = log_index

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))

class BookHistory: 

    def __init__(
        self, 
        client, # TODO: once erc20 is removed from limit order, we can remove this
        offers: List[LimitOrder], 
        trades: List[Trade], 
        cancels: List[Cancel], 
        history: Dict, # history: {block_number: {block_index : {log_index : Event}}}
        # indexes: List[str] # 'block_number-block_index-log_index # faster sort ?
        # fees: List[Fee]
        book: DetailedOrderBook = None,
    ): 
        self.client = client # TODO: we will want to remove this when we remove the ERC20 object from the limit order 
        self.offers = offers # should these be called limit_orders?
        self.trades = trades # market_orders? 
        self.cancels = cancels
        self.history = history
        # self.indexes = indexes

        if book == None:
            self.book = DetailedOrderBook(
                bids=None,
                asks=None,
            )
        else:
            self.book = book

    def from_df(
        self,
        pair_name: str,
        offers: List[pd.DataFrame],
        trades: List[pd.DataFrame],
        # cancels: List[pd.DataFrame], TODO: add this to the subgraph 
    ):
                
        limit_orders = []
        for offer in offers: 
            limit_orders.extend(self.dataframe_to_limit_orders(df=offer, pair_name=pair_name))

        market_orders = []
        for trade in trades: 
            market_orders.extend(self.dataframe_to_trades(df=trade, pair_name=pair_name)) # TODO: move to using market orders

        cancels = []
        for limit_order in limit_orders: 
            if limit_order.open == False:
                cancels.append(Cancel(
                    id=int(limit_order.id), 
                    block_number=int(limit_order.removed_block_number),
                    block_index=int(limit_order.removed_block_index),
                    log_index=int(limit_order.removed_log_index), 
                ))

        events = limit_orders + market_orders + cancels
        history = {}

        for event in events: 

            block_number = int(event.block_number)
            block_index = int(event.block_index)
            log_index = int(event.log_index)

            if history.get(block_number) == None:
                history[block_number] = {}
            if history[block_number].get(block_index) == None:
                history[block_number][block_index] = {}
            if history[block_number][block_index].get(log_index) == None:
                history[block_number][block_index][log_index] = {}

            history[block_number][block_index][log_index] = event
            
        self.offers = limit_orders, 
        self.trades = market_orders, 
        self.cancels = cancels
        self.history = history
    
    def build_history(
        self,
        #offers: List[LimitOrder], 
        #trades: List[Trade], 
        #cancels: List[Cancel], 
    ): 
        return 
        
    # TODO: there has to be a way to import this from the OrderQuery class
    def dataframe_to_limit_orders(
        self, df: pd.DataFrame, pair_name: str # TODO: this is a very hacky way of allowing this client object to be passed in before the class is initialized
    ) -> List[LimitOrder]:
        """Converts a DataFrame of order data into a list of LimitOrder objects."""

        def row_to_limitorder(row: pd.Series) -> LimitOrder:
            if row["side"] == "buy":  # TODO: there is probably a better way to do this
                base_asset = self.client.get_token(row["buy_gem"]) # TODO: once erc20 is removed from limit order, we can remove this
                quote_asset = self.client.get_token(row["pay_gem"]) # TODO: once erc20 is removed from limit order, we can remove this
 
                base_asset_amt = row["buy_amt"]
                quote_asset_amt = row["pay_amt"]
                base_asset_amt_filled = row["bought_amt"]
                quote_asset_amt_filled = row["paid_amt"]

                order_side = OrderSide.BUY
            else:
                base_asset = self.client.get_token(row["pay_gem"]) 
                quote_asset = self.client.get_token(row["buy_gem"])

                base_asset_amt = row["pay_amt"]
                quote_asset_amt = row["buy_amt"]
                base_asset_amt_filled = row["paid_amt"]
                quote_asset_amt_filled = row["bought_amt"]

                order_side = OrderSide.SELL

            return LimitOrder(
                pair_name=pair_name,
                order_side=order_side,
                id=row["id"],
                timestamp=row["timestamp"],
                block_number=row["transaction_block_number"],
                block_index=row["transaction_block_index"],
                log_index=row["index"],  # Assume 0 if 'log_index' column doesn't exist
                txn_hash=row["transaction"],
                maker=self.client.network.w3.to_checksum_address(row["maker"]),
                from_address=self.client.network.w3.to_checksum_address(row["from_address"]), 
                base_asset=base_asset,
                quote_asset=quote_asset,
                base_amt=base_asset_amt - base_asset_amt_filled,
                quote_amt=quote_asset_amt - quote_asset_amt_filled,
                base_amt_original=base_asset_amt,
                quote_amt_original=quote_asset_amt,
                base_amt_filled=base_asset_amt_filled,
                quote_amt_filled=quote_asset_amt_filled,
                open=row["open"],
                price=None,  # we want to calculate this on the fly based on direction
                removed_timestamp=row.get("removed_timestamp", None),  
                removed_block_number=row.get("removed_block", None),
                removed_block_index=row.get("removed_block_index", None), # offers.removed_block_index,
                removed_log_index=row.get("removed_log_index", None),    # offers.removed_log_index,
            )

        return df.apply(row_to_limitorder, axis=1).tolist()
        
    # TODO: update this to be a market order 
    def dataframe_to_trades(
        self, 
        df: pd.DataFrame, 
        pair_name: str,
    ) -> List[Trade]: 
        
        # TODO: update this to be a market order
        def row_to_trade(row: pd.Series) -> Trade:

            # TODO: make sure this can handle both the formatted query and the unformatted query options
            return Trade(
                pair_name=pair_name,
                # order_side=OrderSide,
                block_number=row['block_number'],
                block_index=row['block_index'],
                log_index=row['log_index'],
                #txn_hash=row['txn_hash'],
                taker=row['taker'],
                from_address=row['from_address'],
                take_gem=row['take_gem_address'], # TODO: this should be handled based on formatted or unformatted query
                give_gem=row['give_gem_address'], # TODO: this should be handled based on formatted or unformatted query
                take_amt=row['take_amt_raw'], # TODO: this should be handled based on formatted or unformatted query
                give_amt=row['give_amt_raw'], # TODO: this should be handled based on formatted or unformatted query
                order_id=row['offer'],
            )

        return df.apply(row_to_trade, axis=1).tolist()
    
    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
'''
# the goal here is to build an order book history for a given pair
def get_book_history(
    client, 
    pair_name, 
    start_block, 
    # end_block, TODO: need to either handle nested filtering or add a block_number to the subgraph offer entity
    ):

    # we will create a dictionary of blocks : block index : log index : event
    ordering = {}

    # get the closed offers
    closed_offers = client.market_data.get_limit_orders(
        pair_name=pair_name, # "WETH/USDC",
        book_side=OrderSide.NEUTRAL,
        open=False,
        first=10000000000,
        removed_block_start=start_block,
    )

    # get any open offers
    open_offers = client.market_data.get_limit_orders(
        pair_name=pair_name, # "WETH/USDC",
        book_side=OrderSide.NEUTRAL,
        open=True,
        first=10000000000,
        # TODO: need to either handle nested filtering or add a block_number to the subgraph offer entity
    )

    # combine the offers
    offers = []
    offers.extend(closed_offers[0])
    offers.extend(closed_offers[1])
    offers.extend(open_offers[0])
    offers.extend(open_offers[1])

    for offer in offers:
        block = offer.block_number
        block_index = offer.block_index
        log_index = offer.log_index

        # if the block does not exist in the dictionary, add it 
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = offer

    # get the smallest block number
    smallest_block = min(ordering.keys())

    # get the smallest block index
    smallest_block_index = min(ordering[smallest_block].keys())

    # get the smallest log index
    smallest_log_index = min(ordering[smallest_block][smallest_block_index].keys())

    # get the first offer
    first_offer = ordering[smallest_block][smallest_block_index][smallest_log_index]
    start_time = first_offer.timestamp - 2

    # get any trades
    trade_objects = client.market_data.get_trades_objects(
        pair_name=pair_name, 
        book_side=OrderSide.NEUTRAL, 
        first=10000000000, 
        start_time=start_time, # TODO: either extend the trade entity to contain the block number or resolve nested filtering (subgrounds issue)
        # end_time=end_time
    )

    # TODO: add cancel entity to subgraph and its query 
    # build the cancels from the closed offers
    cancels = []
    for offer in offers: 
        if offer.removed_block_number==None: 
            continue
        cancels.append(Cancel(
            id=offer.id,
            block_number=offer.removed_block_number,
            block_index=offer.removed_block_index,
            log_index=offer.removed_log_index,
        ))

    # sort them by block number, block_index, log_index
    for trade in trade_objects: 
        block = trade.block_number
        block_index = trade.block_index
        log_index = trade.log_index

        # if the block does not exist in the dictionary, add it
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = trade

    for cancel in cancels: 
        block = cancel.block_number
        block_index = cancel.block_index
        log_index = cancel.log_index

        # if the block does not exist in the dictionary, add it
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = cancel

    # return the list of events
    return ordering
'''