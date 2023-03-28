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
        self.market_aid = AidData 

    def recreate_aid_history(self, aid, bin_size = 60, raw=False): 
        """this method takes an aid address and builds a dataframe of that aid balance over time. its precision is to the second. it does this by taking the ending assset balance at each second.
        
        :param aid: the address of the aid instance
        :type aid: str
        :param bin_size: the bin size of the analysis (for now this only adjusts the price data precision)
        :type bin_size: int
        :return: a dataframe that shows the various asset balances of the aid instance over a period of time
        :rtype: pandas.DataFrame (columns: )
        """

        # get the aid history
        df = self.market_aid.get_aid_history(aid = aid, bin_size = bin_size)

        # create a dataframe the encompasses the period of the aid history 
        min_timestamp = int(df['timestamp'].min())
        max_timestamp = int(df['timestamp'].max())
        timestamp_range = list(range(min_timestamp, max_timestamp))
        history = pd.DataFrame(timestamp_range, columns=['timestamp'])

        # group by asset 
        aid_history_grouped = df.groupby('asset')

        # iterate through each group and get the balance at the max index position for every timestamp
        for asset, group in aid_history_grouped:
            
            # make sure the group is sorted by: block, block_index, timestamp
            group = group.sort_values(by = ['block', 'block_index', 'timestamp']).reset_index(drop = True)

            # set this sorted index as a column so we can identify the end balance of an asset 
            group['sorted_index'] = group.index

            # get the sum of the credits and debits for each timestamp
            credits = group.groupby(['timestamp']).agg({'credits_debits' : 'sum'}).reset_index()
            credits_raw = group.groupby(['timestamp']).agg({'credits_debits_raw' : 'sum'}).reset_index()

            # fill in the credits and debits for each timestamp
            history[f'{asset}_credits'] = history['timestamp'].map(credits.set_index('timestamp')['credits_debits'].to_dict()).fillna(0)
            history[f'{asset}_credits_raw'] = history['timestamp'].map(credits_raw.set_index('timestamp')['credits_debits_raw'].to_dict()).fillna(0)

            # go through and get the max sorted_index for each timestamp
            idx = group.groupby(['timestamp'])['sorted_index'].idxmax()
            filtered_group = group.loc[idx]

            # fill in the balance for each asset at the end of each timestamp
            history[f'{asset}_balance'] = history['timestamp'].map(filtered_group.set_index('timestamp')['balance'].to_dict()).fillna(method='ffill').fillna(0)
            history[f'{asset}_balance_raw'] = history['timestamp'].map(filtered_group.set_index('timestamp')['balance_raw'].to_dict()).fillna(method='ffill').fillna(0)

            # get coinbase ticker for the pair and retrieve the price data
            ticker = self.network.coinbase_tickers[asset]
            prices = self.price.get_price_in_range(start = min_timestamp, end = max_timestamp, pair = ticker)

            # fill in the price for each asset at the beginning of each minute period
            history[f'{asset}_price'] = history['timestamp'].map(prices).fillna(method='ffill').fillna(method='bfill').fillna(0)

        assets = [asset for asset, group in aid_history_grouped]

        return {'data' : history, 'assets' : assets}

    def evaluate_aid_performance(self, data, assets, start_time=None, end_time=None):
        """this function simply takes an aid history, truncates the dataframe by a start and end time (if given), and compares the book value of holding the asset balance at the beginning of the period (adjusting for any deposits / withdrawals during the period) against the actual aid balances. this function is intended to be used with dataframes created by the function `recreate_aid_history`
        
        :param data: a dataframe (ideally returned by the function recreate_aid_history) 
        :type data: pandas.DataFrame
        :param assets: an array of relevant assests for the dataframe (ideally returned by the function recreate_aid_history) 
        :type assets: array 
        :param start_time: the start time of which to conduct an analysis for (this determines what asset mix is used in comparison against the aids real book value / real asset mix)
        :type start_time: int
        :param end_time: the end time of which to conduct the analysis through 
        :param end_time: int
        """

        if start_time:
            data = data[data['timestamp'] >= start_time].reset_index(drop = True)
        if end_time: 
            data = data[data['timestamp'] <= end_time].reset_index(drop = True)

        # set the credits equal to the balance of each asset at index 0
        for asset in assets:
            data[f'{asset}_credits'].iloc[0] = data[f'{asset}_balance'].iloc[0]
            data[f'{asset}_credits_raw'].iloc[0] = data[f'{asset}_balance_raw'].iloc[0]

            # create a cumulative sum of the credits and debits
            data[f'{asset}_credits_total'] = data[f'{asset}_credits'].cumsum()
            data[f'{asset}_credits_total_raw'] = data[f'{asset}_credits_raw'].cumsum()

            # calculate the delta from the credits totals
            data[f'{asset}_balance_delta'] = data[f'{asset}_balance'] - data[f'{asset}_credits_total']
            data[f'{asset}_balance_delta_raw'] = data[f'{asset}_balance_raw'] - data[f'{asset}_credits_total_raw']

            # calculate the usd value of the balance, credits, and delta
            data[f'{asset}_balance_usd'] = data[f'{asset}_balance'] * data[f'{asset}_price']
            data[f'{asset}_credits_total_usd'] = data[f'{asset}_credits_total'] * data[f'{asset}_price']
            data[f'{asset}_balance_delta_usd'] = data[f'{asset}_balance_delta'] * data[f'{asset}_price']

        data['total_balance_usd'] = data[[f'{asset}_balance_usd' for asset in assets]].sum(axis = 1)
        data['total_credits_usd'] = data[[f'{asset}_credits_total_usd' for asset in assets]].sum(axis = 1)
        data['total_balance_delta_usd'] = data[[f'{asset}_balance_delta_usd' for asset in assets]].sum(axis = 1) 

        return {'data' : data, 'assets' : assets}

    def analyze_aid_history(self, aid, start_time=None, end_time=None, bin_size=60, raw=False):
        """this method takes the aid history entities and composes a dataframe that shows the various asset balances of the aid instance over a period of time, the entire aid history if no start and end time are provided. one caveat, when a dataframe begins after the aid instance was created, the first row has a credit of the balance at that point in time.
        
        :param aid: the address of the aid instance
        :type aid: str
        :param start_time: the start time of the analysis
        :type start_time: int
        :param end_time: the end time of the analysis
        :type end_time: int
        :param bin_size: the bin size of the analysis
        :type bin_size: int
        :return: a dataframe that shows the various asset balances of the aid instance over a period of time
        :rtype: pandas.DataFrame (columns: )
        """

        # get the aid history
        df = self.market_aid.get_aid_history(aid = aid, start_time = start_time, end_time = end_time, bin_size = bin_size)

        # get the unique assets and the tickers needed to retrieve coinbase price data
        assets = list(df['asset'].unique())
        tickers = [self.network.coinbase_tickers[asset] for asset in assets]

        # get the time range
        min_timestamp = int(df['timestamp'].min())
        max_timestamp = int(df['timestamp'].max())
        timestamp_range = list(range(min_timestamp, max_timestamp))

        # get the price data
        price_data = {}
        for asset, ticker in zip(assets, tickers):
            price_data[asset] = self.price.get_price_in_range(start = min_timestamp, end = max_timestamp, pair = ticker)

        # go through each asset and get the relevant balance and price data
        df_grouped = df.groupby('asset', as_index=False)
        asset_deltas = {}
        asset_balances = {}
        credits_debits = {}
        for asset, group in df_grouped:
            
            if group.empty:
                print(f'no data for {asset}')
                continue

            # reset the index
            group = group.reset_index(drop=True)

            # set the initial value as a credit to the account for any previous activity 
            group.loc[0, 'credits_debits'] = group.loc[0, 'balance']
            group.loc[0, 'credis_debits_raw'] = group.loc[0, 'balance_raw']

            # now, within the same column, create the cumulative sum of the credits and debits
            group['credits_debits'] = group['credits_debits'].cumsum()
            group['credits_debits_raw'] = group['credits_debits_raw'].cumsum()

            # now, we can calculate the delta of the credits_debits and credits_debits_raw columns
            group['delta'] = group['balance'] - group['credits_debits'] 
            group['delta_raw'] = group['balance_raw'] - group['credits_debits_raw']

            # now we get the data at each timestamp
            if raw: 
                asset_deltas[asset] = group.set_index('timestamp').to_dict()['delta_raw']
                asset_balances[asset] = group.set_index('timestamp').to_dict()['balance_raw']
                credits_debits[asset] = group.set_index('timestamp').to_dict()['credits_debits_raw']
            else:
                asset_deltas[asset] = group.set_index('timestamp').to_dict()['delta']
                asset_balances[asset] = group.set_index('timestamp').to_dict()['balance']
                credits_debits[asset] = group.set_index('timestamp').to_dict()['credits_debits']

        # build the dataframe
        history = pd.DataFrame(timestamp_range, columns=['timestamp'])
    
        # add in the data for each asset
        for asset in assets:
            history[f'{asset}_balance'] = history['timestamp'].map(asset_balances[asset]).fillna(method='ffill').fillna(0)

        for asset in assets: 
            history[f'{asset}_hodl_balance'] = history['timestamp'].map(credits_debits[asset]).fillna(method='ffill').fillna(0)
        
        for asset in assets:
            history[f'{asset}_delta'] = history['timestamp'].map(asset_deltas[asset]).fillna(method='ffill').fillna(0)

        # add in the price data
        for asset in assets:
            history[f'{asset}_price'] = history['timestamp'].map(price_data[asset]).fillna(method='ffill').fillna(method='bfill')

        # compute values based on the price data
        for asset in assets:
            history[f'{asset}_balance_usd'] = history[f'{asset}_balance'] * history[f'{asset}_price']
        
        for asset in assets:
            history[f'{asset}_hodl_balance_usd'] = history[f'{asset}_hodl_balance'] * history[f'{asset}_price']

        for asset in assets:
            history[f'{asset}_delta_usd'] = history[f'{asset}_delta'] * history[f'{asset}_price']

        # compute the total balance and delta
        history['total_balance_usd'] = history[[f'{asset}_balance_usd' for asset in assets]].sum(axis=1)
        history['total_hodl_balance_usd'] = history[[f'{asset}_hodl_balance_usd' for asset in assets]].sum(axis=1)
        history['total_delta_usd'] = history[[f'{asset}_delta_usd' for asset in assets]].sum(axis=1)
        
        return {'data' : history, 'tokens' : assets, 'tickers' : tickers}
    
    def idealized_mix_analysis(self, data, tokens, asset_mix, rebalance_interval = 60):
        """this function is intended so simulate the performance of a market aid instance against its "idealized mix", that is, a portfolio holding the same assets in a pre-defined proportion. the rebalancing of the idealized mix is done on an interval basis 

        :param data: the dataframe containing the data to analyze. pulled from the analyze_aid_history function
        :type data: pd.DataFrame
        :param tokens: the assets that the aid held during the period
        :type tokens: list
        :param asset_mix: the idealized mix of the assets held by the aid, a dictionary with the asset as the key and the proportion as the value (i.e. {'eth' : 0.5, 'usdc' : 0.5})
        :type asset_mix: dict
        """

        # sanity check and ensure the data is timestamp sorted in ascending order
        data = data.sort_values('timestamp', ascending=True)
        data.reset_index(inplace=True)

        # iterate through the data and compute the idealized mix at every interval
        for index, row in data.iterrows():

            if index == 0:
                usd_balance = row['total_balance_usd']

                # set the initial idealized mix 
                for token in tokens: 
                    return 'TODO'
        #for token in tokens: 
        #    data[f'{token}_idealized_mix_balance_usd'] = data[f'{token}_balance_usd'] * asset_mix[token]

        #return TODO

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
        
        # if the dataframe is empty, return an empty dataframe with the correct columns
        if len(offers) == 0:
            return pd.DataFrame(columns=['time_bin', 'direction', 'offers_pay_amt_formatted', 'offers_paid_amt_formatted', 'offers_buy_amt_formatted', 'offers_bought_amt_formatted', 'price', 'offers_live'])

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

        