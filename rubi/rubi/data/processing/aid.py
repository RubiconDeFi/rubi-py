import time
import pandas as pd
from .helper import Process
from ..sources import AidData, SuperAidData
from ..sources.helper import Gas, Price, networks

class AidProcessing: 
    """this class is used to process the data from the aid datasource"""

    def __init__(self, subgrounds, chain_id, AidData):
        """constructor method to initialize the data source class"""

        self.price = Price()
        self.process = Process()
        self.network = networks[chain_id]()
        self.market_aid = AidData #AidData(subgrounds, chain_id)

    def build_aid_history(self, aid, bin_size=60, max_timestamp=None):
        # TODO: this has some problems, namely dealing with deposits and withdrawals. 

        # get the aid history 
        df = self.market_aid.get_aid_history(aid, bin_size)

        # get all unique tokens
        tokens = list(df['aidTokenHistories_aid_token_token_symbol'].unique())

        # get the tickers needed to retrieve coinbase price data
        tickers = [self.network.coinbase_tickers[token] for token in tokens]

        # get the time range 
        min_timestamp = df['aidTokenHistories_timestamp'].min()
        
        if max_timestamp is None:
            max_timestamp = int(time.time())

        # TODO: we could let this be dynamically set by the bin size, then we could build dataframes for a variety of granularities
        timestamp_range = list(range(min_timestamp, max_timestamp))

        # group the data and sum within the timestamp
        df = df[['aidTokenHistories_aid_token_token_symbol', 'aidTokenHistories_timestamp', 'aidTokenHistories_balance_change_formatted']]
        df = df.groupby(['aidTokenHistories_aid_token_token_symbol', 'aidTokenHistories_timestamp'])
        df = df[['aidTokenHistories_balance_change_formatted']].sum()
        df.reset_index(inplace=True)
        assets_grouped = df.groupby('aidTokenHistories_aid_token_token_symbol')

        # split out the data by token
        token_balances = {}
        for name, group in assets_grouped:
            group['balance'] = group['aidTokenHistories_balance_change_formatted'].cumsum()
            token_balances[name] = group.set_index('aidTokenHistories_timestamp').to_dict()['balance']    

        # get the price data for this time range 
        price_data = {}
        for token, ticker in zip(tokens, tickers):
            price_data[token] = self.price.get_price_in_range(start = min_timestamp, end = max_timestamp, pair = ticker)
        
        # build the dataframe
        history = pd.DataFrame(timestamp_range, columns=['timestamp'])
        history['total_balance_usd'] = 0
        for token in tokens:
            history[f'{token}_balance'] = history.apply(lambda x: token_balances[token].get(x['timestamp']), axis=1)
            history[f'{token}_balance'] = history[f'{token}_balance'].ffill()
            history[f'{token}_balance'] = history[f'{token}_balance'].fillna(0)

            history[f'{token}_price'] = history.apply(lambda x: price_data[token].get(x['timestamp']), axis=1)
            history[f'{token}_price'] = history[f'{token}_price'].ffill()
            history[f'{token}_price'] = history[f'{token}_price'].bfill()

            history[f'{token}_balance_usd'] = history[f'{token}_balance'] * history[f'{token}_price']
            history['total_balance_usd'] += history[f'{token}_balance_usd']

        # get the usd relative proportions of each token
        for token in tokens:
            history[f'{token}_balance_usd_relative'] = history[f'{token}_balance_usd'] / history['total_balance_usd']

        return {'data' : history, 'tokens' : tokens, 'tickers' : tickers}
    
    def aid_performance_evaluation(self, data, tokens, asset_mix = None):
        """this function is intended to take a dataframe with a set of tokens and determine the performance of the aid over the given time period. it does this in two ways: 
            1. hodl strat comp: compare the performance of aid activity over the period to the performance of simply holding the assets (in the same proportions) as the beginning of the period
            2. asset mix comp: compare the performance of the aid activity to the performance of the holding the assets at a set proprtion (asset mix) as determined by the beginning of the period
        """

        # sanity check and ensure the data is timestamp sorted in ascending order
        data = data.sort_values('timestamp', ascending=True)
        data.reset_index(inplace=True)

        # get the initial asset balances at the beginning of the period
        initial_asset_balances = {}
        data['total_balance_initial_usd'] = 0
        for token in tokens:
            initial_asset_balances[token] = data[f'{token}_balance'].iloc[0]
            data[f'{token}_balance_initial'] = initial_asset_balances[token]
            data[f'{token}_balance_initial_usd'] = data[f'{token}_balance_initial'] * data[f'{token}_price']
            data['total_balance_initial_usd'] += data[f'{token}_balance_initial_usd']
        
        # compute the hodl strat performance delta 
        data['hodl_strat_performance_delta'] = data['total_balance_usd'] - data['total_balance_initial_usd']

        # if there is an asset mix, get the initial prices as well and compute the specific asset mix
        if asset_mix: 
            initial_usd_balance = data['total_balance_usd'].iloc[0]
            initial_asset_prices = {}
            ideal_asset_balances = {}
            data['total_balance_ideal_usd'] = 0
            for token in tokens:
                initial_asset_prices[token] = data[f'{token}_price'].iloc[0]
                ideal_asset_balances[token] = (initial_usd_balance) * asset_mix[token] / initial_asset_prices[token]
                data[f'{token}_balance_ideal'] = ideal_asset_balances[token]
                data[f'{token}_balance_ideal_usd'] = data[f'{token}_balance_ideal'] * data[f'{token}_price']
                data['total_balance_ideal_usd'] += data[f'{token}_balance_ideal_usd']
            
            # compute the asset mix strat performance delta
            data['asset_mix_strat_performance_delta'] = data['total_balance_usd'] - data['total_balance_ideal_usd']

        return data

    def aid_fill_tracking(self, aid, asset, quote, start_time=None, end_time=None, bin_size=60, first=1000000000):
        """this function is intended to track the fills of an aid contract over time. specifically, it takes the offers for a set pair and tracks the fill the occurred within
        a series of "time bins" (this can be as granular as a second and arbitrarily large (seconds)) for a set pair. this is denominated by an asset and quote, with the 
        denomination deciding the direction of trades
         
        :param aid: the aid contract to track
        :type aid: str
        :param asset: the asset to track
        :type asset: str
        :param quote: the quote to track 
        :type quote: str
        :param start_time: the start time of the tracking period
        :type start_time: int
        :param end_time: the end time of the tracking period
        :type end_time: int
        :param bin_size: the size of the time bins
        :type bin_size: int
        :param first: the amount of offers to get from the contract
        """

        # get the offers from the contract
        # TODO: this needs to be updated to add additional filtering as soon as its supported in the low level api
        offers = self.market_aid.get_aid_offers(aid.lower())

        # filter the offers for the desired asset quote pair, the offers_pay_gem_id and offers_buy_gem_id can be either the asset or the quote, so we need to check both
        if len(quote) < 6:
            asks = offers[(offers['offers_pay_gem_symbol'] == asset.upper()) & (offers['offers_buy_gem_symbol'] == quote.upper())]
            bids = offers[(offers['offers_pay_gem_symbol'] == quote.upper()) & (offers['offers_buy_gem_symbol'] == asset.upper())]
        else:
            asks = offers[(offers['offers_pay_gem_id'] == asset.lower()) & (offers['offers_buy_gem_id'] == quote.lower())]
            bids = offers[(offers['offers_pay_gem_id'] == quote.lower()) & (offers['offers_buy_gem_id'] == asset.lower())]

        # group the offers by the time bin they occurred in
        asks['time_bin'] = asks['offers_transaction_timestamp'].apply(lambda x: int((x // bin_size) * bin_size))
        bids['time_bin'] = bids['offers_transaction_timestamp'].apply(lambda x: int((x // bin_size) * bin_size))

        # group the offers by the time bin they occurred in
        asks = asks.groupby('time_bin').sum(numeric_only=True)
        bids = bids.groupby('time_bin').sum(numeric_only=True)

        # add a direction column 
        asks['direction'] = 'ask' # selling the asset
        bids['direction'] = 'bid' # buying the asset

        # transform the index into a column
        asks = asks.reset_index().rename(columns={'index': 'time_bin'})
        bids = bids.reset_index().rename(columns={'index': 'time_bin'})

        # calculate the ask and bid prices 
        asks['price'] =  asks['offers_buy_amt_formatted'] / asks['offers_pay_amt_formatted'] # price to buy the asset from the seller
        bids['price'] =  bids['offers_pay_amt_formatted'] / bids['offers_buy_amt_formatted'] # price to sell the asset to the buyer
        
        # subset the data to the relevant information
        asks = asks[['time_bin', 'direction', 'offers_pay_amt_formatted', 'offers_paid_amt_formatted', 'offers_buy_amt_formatted', 'offers_bought_amt_formatted', 'price', 'offers_live']]
        bids = bids[['time_bin', 'direction', 'offers_pay_amt_formatted', 'offers_paid_amt_formatted', 'offers_buy_amt_formatted', 'offers_bought_amt_formatted', 'price', 'offers_live']]
        
        df = pd.concat([asks, bids]).sort_values('time_bin', ascending=True)
        df.reset_index(inplace=True)
        
        return df

        