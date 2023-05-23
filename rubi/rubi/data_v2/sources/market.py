from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy
from typing import List, Optional
import polars as pl

from rubi.data_v2.sources.helper import Rolodex, TokenList

class MarketData: 
    """this class acts as an access point for data from the RubiconMarket.sol contract"""

    def __init__(self, subgrounds): 
        """constructor method, handles the initialization of the subgraph objects across various networks"""

        # set common class objects
        self.subgrounds = subgrounds
        self.rolodex = Rolodex()
        self.token_list = TokenList()

        # set the v2 subgraph objects
        self.op_main_v2 = self.subgrounds.load_subgraph(self.rolodex.optimism_mainnet_rubicon_v2)
        self.op_goerli_v2 = self.subgrounds.load_subgraph(self.rolodex.optimism_goerli_rubicon_v2)
        self.arb_goerli_v2 = self.subgrounds.load_subgraph(self.rolodex.arbitrum_goerli_rubicon_v2)
        self.polygon_mumbai_v2 = self.subgrounds.load_subgraph(self.rolodex.polygon_mumbai_rubicon_v2)

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
    def get_offers(self, 
                    network: str = 'optimism', # TODO: we may not want to set this as a default, but instead require it to be set
                    maker: Optional[str] = None,
                    start_block: Optional[int] = None,
                    end_block: Optional[int] = None,
                    start_time: Optional[int] = None,
                    end_time: Optional[int] = None,
                    pay_gem: Optional[str] = None,
                    buy_gem: Optional[str] = None,
                    open: Optional[bool] = None,
                    order_by: str = 'timestamp',
                    order_direction: str = 'asc', 
                    first: int = 1000000000):
        
        # handle the network parameter
        if network not in ('optimism', 'optimism_goerli', 'arbitrum_goerli', 'polygon_mumbai'):
            raise ValueError("Invalid network, must be 'optimism', 'optimism_goerli', 'arbitrum_goerli', or 'polygon_mumbai'")
        else: 
            subgraph = self.subgraphs[network]
            token_list_df = self.token_lists[network]
        
        # handle the order_by parameter
        if order_by.lower() not in ('timestamp', 'block_number'):
            raise ValueError("Invalid order_by, must be 'timestamp' or 'block_number'")
        elif order_by.lower() == 'timestamp':
            order_by = subgraph.Offer.timestamp
        elif order_by.lower() == 'block_number':
            order_by = subgraph.Offer.block_number
        
        # handle the order_direction parameter
        if order_direction.lower() not in ('asc', 'desc'):
            raise ValueError("Invalid order_direction, must be 'asc' or 'desc'")

        # Build the list of where conditions
        where = [
            subgraph.Offer.maker == maker.lower() if maker else None,
            subgraph.Offer.block_number >= start_block if start_block else None,
            subgraph.Offer.block_number <= end_block if end_block else None,
            subgraph.Offer.timestamp >= start_time if start_time else None,
            subgraph.Offer.timestamp <= end_time if end_time else None,
            subgraph.Offer.pay_gem == pay_gem.lower() if pay_gem else None,
            subgraph.Offer.buy_gem == buy_gem.lower() if buy_gem else None,
            subgraph.Offer.open == open if open is not None else None
        ]
        where = [condition for condition in where if condition is not None]

        # set the offer query
        # TODO: this can be cleaned up a bit
        if where:
            offers = subgraph.Query.offers(
                orderBy = order_by,
                orderDirection = order_direction,
                first=first,
                where = where
            )
        else:
            offers = subgraph.Query.offers(
                orderBy = order_by,
                orderDirection = order_direction,
                first=first
            )

        # set the paths to the data we want to query
        paths = [
            offers.id, 
            offers.transaction.timestamp,
            offers.transaction.block_number,
            offers.transaction.block_index,
            offers.index,
            offers.maker.id,
            offers.pay_gem,
            offers.buy_gem,
            offers.pay_amt,
            offers.buy_amt,
            offers.paid_amt, 
            offers.bought_amt,
            offers.open,
            offers.removed_timestamp,
            offers.removed_block
        ]

        # query the subgraph for the data and return it as a json object
        json_data = self.subgrounds.query_json(paths, pagination_strategy=ShallowStrategy)

        # Flatten the nested JSON data
        flattened_data = [
            {
                'id': entry['id'],
                'timestamp': entry['transaction']['timestamp'],
                'block_number': entry['transaction']['block_number'],
                'block_index': entry['transaction']['block_index'],
                'index': entry['index'],
                'maker_id': entry['maker']['id'],
                'pay_gem': entry['pay_gem'],
                'buy_gem': entry['buy_gem'],
                'pay_amt': entry['pay_amt'],
                'buy_amt': entry['buy_amt'],
                'paid_amt': entry['paid_amt'],
                'bought_amt': entry['bought_amt'],
                'open': entry['open'],
                'removed_timestamp': entry['removed_timestamp'],
                'removed_block': entry['removed_block'],
            }
            for item in json_data
            for key, value in item.items()
            for entry in value
        ]

        # Convert the flattened JSON data to a Polars DataFrame
        data_frame = pl.DataFrame(flattened_data)

        # if the dataframe is empty, return an empty dataframe
        if data_frame.shape[0] == 0:
            return data_frame

        # Create a temporary DataFrame for joining
        temp_df = token_list_df["address", "symbol", "decimals"].with_columns(
            pl.col("address").alias("buy_gem"),
            pl.col("symbol").alias("buy_gem_symbol"),
            pl.col("decimals").alias("buy_gem_decimals"),
        )

        # Join the data_frame with token_list_df on the pay_gem and buy_gem columns
        data_frame = (
            data_frame.join(token_list_df["address", "symbol", "decimals"].with_columns(
                pl.col("address").alias("pay_gem"),
                pl.col("symbol").alias("pay_gem_symbol"),
                pl.col("decimals").alias("pay_gem_decimals"),
            ), on="pay_gem", how="left")
            .join(temp_df, on="buy_gem", how="left")
        )

        # Create new columns for the pay amount and buy amount in decimal format
        data_frame = data_frame.with_columns(
            (data_frame["pay_amt"] / (10 ** data_frame["pay_gem_decimals"])).alias("pay_amt_decimal"),
            (data_frame["buy_amt"] / (10 ** data_frame["buy_gem_decimals"])).alias("buy_amt_decimal"),
        )

        # drop the duplicate columns caused by the join
        data_frame = data_frame.drop(["address_right", "symbol_right", "decimals_right"])

        return data_frame
    
    def get_trades(self, 
              network: str = 'optimism',
              taker: Optional[str] = None,
              start_block: Optional[int] = None,
              end_block: Optional[int] = None,
              start_time: Optional[int] = None,
              end_time: Optional[int] = None,
              take_gem: Optional[str] = None,
              give_gem: Optional[str] = None,
              order_by: str = 'timestamp',
              order_direction: str = 'asc', 
              first: int = 1000000000):
    
        # Handle the network parameter
        if network not in ('optimism', 'optimism_goerli', 'arbitrum_goerli', 'polygon_mumbai'):
            raise ValueError("Invalid network, must be 'optimism', 'optimism_goerli', 'arbitrum_goerli', or 'polygon_mumbai'")
        else: 
            subgraph = self.subgraphs[network]
            token_list_df = self.token_lists[network]
        
        # Handle the order_by parameter
        if order_by.lower() not in ('timestamp', 'block_number'):
            raise ValueError("Invalid order_by, must be 'timestamp' or 'block_number'")
        elif order_by.lower() == 'timestamp':
            order_by = subgraph.Take.timestamp
        elif order_by.lower() == 'block_number':
            order_by = subgraph.Take.transaction.block_number
        
        # Handle the order_direction parameter
        if order_direction.lower() not in ('asc', 'desc'):
            raise ValueError("Invalid order_direction, must be 'asc' or 'desc'")

        # Build the list of where conditions
        where = [
            subgraph.Take.taker.id == taker.lower() if taker else None,
            subgraph.Take.transaction.block_number >= start_block if start_block else None,
            subgraph.Take.transaction.block_number <= end_block if end_block else None,
            subgraph.Take.timestamp >= start_time if start_time else None,
            subgraph.Take.timestamp <= end_time if end_time else None,
            subgraph.Take.take_gem == take_gem.lower() if take_gem else None,
            subgraph.Take.give_gem == give_gem.lower() if give_gem else None
        ]
        where = [condition for condition in where if condition is not None]

        # Set the take query
        if where:
            takes = subgraph.Query.takes(
                orderBy = order_by,
                orderDirection = order_direction,
                first=first,
                where = where
            )
        else:
            takes = subgraph.Query.takes(
                orderBy = order_by,
                orderDirection = order_direction,
                first=first
            )

        # Set the paths to the data we want to query
        paths = [
            takes.id,
            takes.transaction.timestamp,
            takes.transaction.block_number,
            takes.transaction.block_index,
            takes.index,
            takes.taker.id,
            takes.take_gem,
            takes.give_gem,
            takes.take_amt,
            takes.give_amt
        ]

        # Query the subgraph for the data and return it as a JSON object
        json_data = self.subgrounds.query_json(paths, pagination_strategy=ShallowStrategy)

        flattened_data = [
            {
                'id': entry['id'],
                'timestamp': entry['transaction']['timestamp'],
                'block_number': entry['transaction']['block_number'],
                'block_index': entry['transaction']['block_index'],
                'index': entry['index'],
                'taker_id': entry['taker']['id'],
                'take_gem': entry['take_gem'],
                'give_gem': entry['give_gem'],
                'take_amt': entry['take_amt'],
                'give_amt': entry['give_amt'],
            }
            for item in json_data
            for key, value in item.items()
            for entry in value
        ]

        # Convert the flattened JSON data to a Polars DataFrame
        data_frame = pl.DataFrame(flattened_data)

        # If the dataframe is empty, return an empty dataframe
        if data_frame.shape[0] == 0:
            return data_frame

        # Create a temporary DataFrame for joining
        temp_df = token_list_df["address", "symbol", "decimals"].with_columns(
            pl.col("address").alias("give_gem"),
            pl.col("symbol").alias("give_gem_symbol"),
            pl.col("decimals").alias("give_gem_decimals"),
        )

        # Join the data_frame with token_list_df on the take_gem and give_gem columns
        data_frame = (
            data_frame.join(token_list_df["address", "symbol", "decimals"].with_columns(
                pl.col("address").alias("take_gem"),
                pl.col("symbol").alias("take_gem_symbol"),
                pl.col("decimals").alias("take_gem_decimals"),
            ), on="take_gem", how="left")
            .join(temp_df, on="give_gem", how="left")
        )

        # Create new columns for the take amount and give amount in decimal format
        data_frame = data_frame.with_columns(
            (data_frame["take_amt"] / (10 ** data_frame["take_gem_decimals"])).alias("take_amt_decimal"),
            (data_frame["give_amt"] / (10 ** data_frame["give_gem_decimals"])).alias("give_amt_decimal"),
        )

        # drop the duplicate columns caused by the join
        data_frame = data_frame.drop(["address_right", "symbol_right", "decimals_right"])

        return data_frame
