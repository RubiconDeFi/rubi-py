import pandas as pd
from .helper import Process
from ..sources import AidData, SuperAidData
from ..sources.helper import Gas, Price, networks

class AidProcessing: 
    """this class is used to process the data from the aid datasource"""

    def __init__(self, subgrounds, chain_id):
        """constructor method to initialize the data source class"""

        self.price = Price()
        self.process = Process()
        self.network = networks[chain_id]()
        self.market_aid = AidData(subgrounds, chain_id)
        
    # TODO: clean this function and make it more efficient
    def build_aid_history(self, aid, bin_size=60):
        """this function serves as an easy way to build back the entire asset history of the aid contract along with price support for the assets.
        it relies heavily upon the marke-aid subgraph as a source of data and applies the necessary transformations to the data to format it in 
        a way that allows for granularity of asset balances and relevant price data to the minute."""

        # get the aid history
        data = self.market_aid.get_aid_history(aid, bin_size)

        # get all of the relevant tokens
        tokens = list(data['aids_balances_token_symbol'].unique())

        # get the min and max timestamps
        min_timestamp = data['aids_balances_history_timestamp'].min()
        max_timestamp = data['aids_balances_history_timestamp'].max()

        # get the tickers needed to retrieve coinbase price data
        tickers = [self.network.coinbase_tickers[token] for token in tokens]

        # group the data and get the cumulative balance changes for each timestamp
        history = data.groupby(['aids_id', 'aids_balances_token_id', 'aids_balances_token_symbol', 'aids_balances_history_time_bin'])
        history = history[['aids_balances_history_balance_change_formatted']].sum() 
        history.reset_index(inplace=True)
        asset_grouping = history.groupby('aids_balances_token_symbol')

        # for each asset, create a seperate dataframe that can be used to get the relevant balance changes for that asset
        asset_changes = {}
        for name, group in asset_grouping:
            asset_changes[name] = dict(zip(group['aids_balances_history_time_bin'], group['aids_balances_history_balance_change_formatted']))

        # collect price data for each asset of interest over the given time period of interest
        price_data = {}

        for token, ticker in zip(tokens, tickers):
            price_data[token] = self.price.get_price_in_range(start = min_timestamp, end = max_timestamp, pair = ticker)

        # create a datarame that is every timestamp (bin_size is the period of interest) and map the relevant price data to each timestamp
        longest_key = max(price_data, key=lambda k: len(price_data[k]))
        price_df = pd.DataFrame.from_dict(price_data[longest_key], orient='index', columns=[f'{longest_key}_price'])

        # reset the index and set the symbol column to the longest key
        price_df.index.name = 'timestamp'
        price_df.reset_index(inplace=True)
        price_df[f'{longest_key}'] = longest_key

        # now go through the tokens and add the price data and balance changes to the dataframe
        for symbol in tokens: 
            if symbol == longest_key:
                price_df[f'{symbol}_balance_change'] = price_df.apply(lambda x: asset_changes[symbol].get(x['timestamp']),  axis=1)
                continue
            price_df[f'{symbol}_price'] = price_df.apply(lambda x: self.process.get_closest_timestamp_value(price_data[symbol], x['timestamp']), axis=1) 
            price_df[f'{symbol}'] = symbol
            price_df[f'{symbol}_balance_change'] = price_df.apply(lambda x: asset_changes[symbol].get(x['timestamp']),  axis=1)

        # fill in any zeros that did not have values
        price_df = price_df.fillna(0)

        # now forwad fill the price data, token change data, and compute running balances for each token
        for symbol in tokens: 
            price_df[f'{symbol}_balance'] = price_df[f'{symbol}_balance_change'].cumsum()
            price_df[f'{symbol}_balance_usd'] = price_df[f'{symbol}_balance'] * price_df[f'{symbol}_price']

        # return the dataframe and the tokens in a dictionary 
        return {'data': price_df, 'tokens': tokens}