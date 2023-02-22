import rubi as Rubi
from datetime import datetime, timedelta

# TODO: there is a lot that can be done to improve the performance of this function, mainly in the form of caching and only querying for new data and then updating the existing data
def data_pull(rubi, aid, bin_size, asset_mix):

    # get the aid gas spend data
    gas = rubi.data.market_aid_optimism.get_aid_gas_spend_binned(aid)
    
    # get the aid history
    op_aid_history = rubi.data.market_aid_optimism_processing.build_aid_history(aid = aid, bin_size = bin_size)
    full_data = op_aid_history['data']
    tokens = op_aid_history['tokens']
    tickers = op_aid_history['tickers']

    # parse the aid history by timestamp 
    trailing_six_hour_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(hours=6)).timestamp())]
    trailing_twelve_hour_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(hours=12)).timestamp())]
    trailing_day_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(days=1)).timestamp())]
    trailing_three_day_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(days=3)).timestamp())]
    trailing_week_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(days=7)).timestamp())]
    trailing_two_week_data = full_data[full_data['timestamp'] > int((datetime.now() - timedelta(days=14)).timestamp())]

    # evaluate the performance of the aid over the trailing time periods
    trailing_six_hour_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_six_hour_data, tokens, asset_mix = asset_mix)
    trailing_twelve_hour_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_twelve_hour_data, tokens, asset_mix = asset_mix)
    trailing_day_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_day_data, tokens, asset_mix = asset_mix)
    trailing_three_day_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_three_day_data, tokens, asset_mix = asset_mix)
    trailing_week_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_week_data, tokens, asset_mix = asset_mix)
    trailing_two_week_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_two_week_data, tokens, asset_mix = asset_mix)
    full_history_performance = rubi.data.market_aid_optimism_processing.aid_performance_evaluation(full_data, tokens, asset_mix = asset_mix)

    # add the gas spend data to each dataframe and then cumsum to do the gas spend calcs
    trailing_six_hour_performance['gas_spend_usd'] = trailing_six_hour_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    trailing_twelve_hour_performance['gas_spend_usd'] = trailing_twelve_hour_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    trailing_day_performance['gas_spend_usd'] = trailing_day_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    trailing_three_day_performance['gas_spend_usd'] = trailing_three_day_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    trailing_week_performance['gas_spend_usd'] = trailing_week_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    trailing_two_week_performance['gas_spend_usd'] = trailing_two_week_performance['timestamp'].apply(lambda x: gas.get(x, 0))
    full_history_performance['gas_spend_usd'] = full_history_performance['timestamp'].apply(lambda x: gas.get(x, 0))

    trailing_six_hour_performance['total_gas_spend_usd'] = trailing_six_hour_performance['gas_spend_usd'].cumsum()
    trailing_twelve_hour_performance['total_gas_spend_usd'] = trailing_twelve_hour_performance['gas_spend_usd'].cumsum()
    trailing_day_performance['total_gas_spend_usd'] = trailing_day_performance['gas_spend_usd'].cumsum()
    trailing_three_day_performance['total_gas_spend_usd'] = trailing_three_day_performance['gas_spend_usd'].cumsum()
    trailing_week_performance['total_gas_spend_usd'] = trailing_week_performance['gas_spend_usd'].cumsum()
    trailing_two_week_performance['total_gas_spend_usd'] = trailing_two_week_performance['gas_spend_usd'].cumsum()
    full_history_performance['total_gas_spend_usd'] = full_history_performance['gas_spend_usd'].cumsum()

    # add gas spend data to delta calcs
    trailing_six_hour_performance['hodl_strat_performance_delta_net_gas'] = trailing_six_hour_performance['hodl_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_twelve_hour_performance['hodl_strat_performance_delta_net_gas'] = trailing_twelve_hour_performance['hodl_strat_performance_delta'] - trailing_twelve_hour_performance['total_gas_spend_usd']
    trailing_day_performance['hodl_strat_performance_delta_net_gas'] = trailing_day_performance['hodl_strat_performance_delta'] - trailing_day_performance['total_gas_spend_usd']
    trailing_three_day_performance['hodl_strat_performance_delta_net_gas'] = trailing_three_day_performance['hodl_strat_performance_delta'] - trailing_three_day_performance['total_gas_spend_usd']
    trailing_week_performance['hodl_strat_performance_delta_net_gas'] = trailing_week_performance['hodl_strat_performance_delta'] - trailing_week_performance['total_gas_spend_usd']
    trailing_two_week_performance['hodl_strat_performance_delta_net_gas'] = trailing_two_week_performance['hodl_strat_performance_delta'] - trailing_two_week_performance['total_gas_spend_usd']
    full_history_performance['hodl_strat_performance_delta_net_gas'] = full_history_performance['hodl_strat_performance_delta'] - full_history_performance['total_gas_spend_usd']

    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    trailing_six_hour_performance['asset_mix_strat_performance_delta_net_gas'] = trailing_six_hour_performance['asset_mix_strat_performance_delta'] - trailing_six_hour_performance['total_gas_spend_usd']
    full_history_performance['asset_mix_strat_performance_delta_net_gas'] = full_history_performance['asset_mix_strat_performance_delta'] - full_history_performance['total_gas_spend_usd']

    # convert the unix timestamps to datetime objects
    trailing_six_hour_performance['timestamp'] = trailing_six_hour_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_twelve_hour_performance['timestamp'] = trailing_twelve_hour_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_day_performance['timestamp'] = trailing_day_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_three_day_performance['timestamp'] = trailing_three_day_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_week_performance['timestamp'] = trailing_week_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_two_week_performance['timestamp'] = trailing_two_week_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))
    full_history_performance['timestamp'] = full_history_performance['timestamp'].apply(lambda x: datetime.fromtimestamp(x))

    # save the performance data to a dictionary
    performance_data = {
        'trailing_six_hour_performance': trailing_six_hour_performance,
        'trailing_twelve_hour_performance': trailing_twelve_hour_performance,
        'trailing_day_performance': trailing_day_performance,
        'trailing_three_day_performance': trailing_three_day_performance,
        'trailing_week_performance': trailing_week_performance,
        'trailing_two_week_performance': trailing_two_week_performance,
        'full_history_performance': full_history_performance,
        'tokens': tokens,
        'tickers': tickers
    }

    return performance_data

def fill_tracking(rubi, aid, asset, quote, bin_size=None):
    # TODO: add in the ability to both bin_size and start_time/end_time 

    # get the fill tracking history for the aid
    fill = rubi.data.market_aid_optimism_processing.aid_fill_tracking(aid = aid, asset = asset, quote = quote)

    # to create the bar chart we want, convert the ask data to be negative, indicating the asset is being sold
    fill['sell_amount'] = fill.apply(lambda x: -x['offers_pay_amt_formatted'] if x['direction'] == 'ask' else 0, axis = 1)
    fill['sold_amount'] = fill.apply(lambda x: -x['offers_paid_amt_formatted'] if x['direction'] == 'ask' else 0, axis = 1)
    fill['buy_amount'] = fill.apply(lambda x: x['offers_buy_amt_formatted'] if x['direction'] == 'bid' else 0, axis = 1)
    fill['bought_amount'] = fill.apply(lambda x: x['offers_bought_amt_formatted'] if x['direction'] == 'bid' else 0, axis = 1)

    # group the data by time_bin and sum the relevant numberical columns
    fill = fill.groupby('time_bin').sum(numeric_only = True)

    # reset the index to a column called time_bin
    fill = fill.reset_index()#.rename(columns={'index': 'time_bin'})

    # now drop and keep only the relevant columns
    fill = fill[['time_bin', 'sell_amount', 'sold_amount', 'buy_amount', 'bought_amount', 'offers_live']]

    # get the min and max time_bin values
    min_time_bin = int(fill['time_bin'].min())
    max_time_bin = int(fill['time_bin'].max())

    # get the relenvant price data for the asset 
    try:
        ticker = rubi.data.market_aid_optimism_processing.network.coinbase_tickers[asset]
        price_data = rubi.data.market_aid_optimism_processing.price.get_price_in_range(start = min_time_bin, end = max_time_bin, pair = ticker)
    except:
        ticker = rubi.data.market_aid_optimism_processing.network.coinbase_tickers['WETH']
        price_data = rubi.data.market_aid_optimism_processing.price.get_price_in_range(start = min_time_bin, end = max_time_bin, pair = ticker)

    # add a column for the price data
    fill['price'] = fill['time_bin'].apply(lambda x: price_data.get(x))
    fill['price'] = fill['price'].ffill()
    fill['price'] = fill['price'].bfill()

    # add a column for asset values as usd
    fill['sell_amount_usd'] = fill['sell_amount'] * fill['price']
    fill['sold_amount_usd'] = fill['sold_amount'] * fill['price']
    fill['buy_amount_usd'] = fill['buy_amount'] * fill['price']
    fill['bought_amount_usd'] = fill['bought_amount'] * fill['price']

    # parse the dataset by time_bin
    trailing_one_hour_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(hours=1)).timestamp())]
    trailing_three_hour_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(hours=3)).timestamp())]
    trailing_six_hour_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(hours=6)).timestamp())]
    trailing_twelve_hour_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(hours=12)).timestamp())]
    trailing_day_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(days=1)).timestamp())]
    trailing_three_day_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(days=3)).timestamp())]
    trailing_week_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(days=7)).timestamp())]
    trailing_two_week_fill = fill[fill['time_bin'] > int((datetime.now() - timedelta(days=14)).timestamp())]

    # convert the time_bin to datetime objects
    fill['time_bin'] = fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_one_hour_fill['time_bin'] = trailing_one_hour_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_three_hour_fill['time_bin'] = trailing_three_hour_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_six_hour_fill['time_bin'] = trailing_six_hour_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_twelve_hour_fill['time_bin'] = trailing_twelve_hour_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_day_fill['time_bin'] = trailing_day_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_three_day_fill['time_bin'] = trailing_three_day_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_week_fill['time_bin'] = trailing_week_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))
    trailing_two_week_fill['time_bin'] = trailing_two_week_fill['time_bin'].apply(lambda x: datetime.fromtimestamp(x))

    # create the fill tracking data dictionary
    fill_tracking_data = {
        'full_history_fill_tracking': fill,
        'trailing_one_hour_fill_tracking': trailing_one_hour_fill,
        'trailing_three_hour_fill_tracking': trailing_three_hour_fill,
        'trailing_six_hour_fill_tracking': trailing_six_hour_fill,
        'trailing_twelve_hour_fill_tracking': trailing_twelve_hour_fill,
        'trailing_day_fill_tracking': trailing_day_fill,
        'trailing_three_day_fill_tracking': trailing_three_day_fill,
        'trailing_week_fill_tracking': trailing_week_fill,
        'trailing_two_week_fill_tracking': trailing_two_week_fill
    }

    # return the fill tracking data
    return fill_tracking_data