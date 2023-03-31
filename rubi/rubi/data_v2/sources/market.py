from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy
from typing import List, Optional
import polars as pl

from rubi.data_v2.sources.helper import Rolodex, TokenList
from typing import List, Optional

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
        self.op_main_token_list = self.token_list.get_token_list(network='optimism')

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
                    network: str = 'optimism',
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

        # handle the conditional parameters
        where = []
        if maker:
            where.append(subgraph.Offer.maker == maker.lower())
        if start_block:
            where.append(subgraph.Offer.block_number >= start_block)
        if end_block:
            where.append(subgraph.Offer.block_number <= end_block)
        if start_time:
            where.append(subgraph.Offer.timestamp >= start_time)
        if end_time:
            where.append(subgraph.Offer.timestamp <= end_time)
        if pay_gem:
            where.append(subgraph.Offer.pay_gem == pay_gem.lower())
        if buy_gem:
            where.append(subgraph.Offer.buy_gem == buy_gem.lower())
        if open is not None:
            where.append(subgraph.Offer.open == open)

        # set the offer query
        offers = subgraph.Query.offers(
            orderBy = order_by,
            orderDirection = order_direction,
            first=first,
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
        if data_frame.empty:
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

        # drop the 'address_right' and 'address_left' columns
        data_frame = data_frame.drop(["address_right", "address_left"])

        return data_frame