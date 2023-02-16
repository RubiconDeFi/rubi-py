# the purpose of this dashboard is to serve as a monitoring dashboard for a specific market aid instance
# in its initial version, it will do the following: 
    # 1. show the current status of the market aid instance: (it is important to note that today this will be established in a polling fashion, in the future it should be a websocket connection to enable live data support)
        # a. the current token balances of the market aid instance
        # b. the current outstanding orders of the market aid instance
    # 2. show the historical balance of assets on the market aid instance (this will be a line chart)
    # 3. show the historical offers and fills for a market aid instance (this will be a bar chart)

import os
import dash
import rubi as Rubi
from web3 import Web3
from dotenv import load_dotenv
from datetime import datetime, timedelta

from dash import html, dcc
import dash_bootstrap_components as dbc

from subgrounds.dash_wrappers import Graph
from subgrounds.plotly_wrappers import Figure, Scatter, Indicator

print("hello, DeFi Cowboy!")

load_dotenv()

# get the node url
BNF_HTTP = os.getenv('BNF_HTTP')
GOERLI_HTTP = os.getenv('OP_GOERLI_NODE')

# create a web3 instance
w3_op = Web3(Web3.HTTPProvider(BNF_HTTP))
w3_goerli = Web3(Web3.HTTPProvider(GOERLI_HTTP))

# create a rubicon instance
rubi_goerli = Rubi.Rubicon(w3_goerli)
rubi_op = Rubi.Rubicon(w3_op)

aid_goerli = os.getenv('MARKET_AID_OPTIMISM_GOERLI')
aid_op = os.getenv('MARKET_AID_OPTIMISM')

bin_size = 60

asset_mix = {
    'WETH' : .5,
    'USDC' : .25,
    'USDT' : .25
}

op_asset_mix = {
    'WETH' : .5,
    'USDC' : .5
}

# TODO: there is a lot that can be done to improve the performance of this function, mainly in the form of caching and only querying for new data and then updating the existing data
def data_pull(aid, bin_size):

    # get the aid gas spend data
    gas = rubi_op.data.market_aid_optimism.get_aid_gas_spend_binned(aid = aid_op)
    
    # get the aid history
    op_aid_history = rubi_op.data.market_aid_optimism_processing.build_aid_history(aid = aid, bin_size = bin_size)
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
    trailing_six_hour_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_six_hour_data, tokens, asset_mix = op_asset_mix)
    trailing_twelve_hour_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_twelve_hour_data, tokens, asset_mix = op_asset_mix)
    trailing_day_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_day_data, tokens, asset_mix = op_asset_mix)
    trailing_three_day_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_three_day_data, tokens, asset_mix = op_asset_mix)
    trailing_week_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_week_data, tokens, asset_mix = op_asset_mix)
    trailing_two_week_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(trailing_two_week_data, tokens, asset_mix = op_asset_mix)
    full_history_performance = rubi_op.data.market_aid_optimism_processing.aid_performance_evaluation(full_data, tokens, asset_mix = op_asset_mix)

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

def fill_tracking(aid, asset, quote, bin_size=None):
    # TODO: add in the ability to both bin_size and start_time/end_time 

    # get the fill tracking history for the aid
    fill = rubi_op.data.market_aid_optimism_processing.aid_fill_tracking(aid = aid, asset = asset, quote = quote)

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
        ticker = rubi_op.data.market_aid_optimism_processing.network.coinbase_tickers[asset]
        price_data = rubi_op.data.market_aid_optimism_processing.price.get_price_in_range(start = min_time_bin, end = max_time_bin, pair = ticker)
    except:
        ticker = rubi_op.data.market_aid_optimism_processing.network.coinbase_tickers['WETH']
        price_data = rubi_op.data.market_aid_optimism_processing.price.get_price_in_range(start = min_time_bin, end = max_time_bin, pair = ticker)

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

# get the performance data
performance_data = data_pull(aid = aid_op, bin_size = bin_size)

# get the fill tracking data
# TODO: we need some type of error handling here and the ability to load in from the token list
asset = 'WETH'
quote = 'USDC'
fill_tracking_data = fill_tracking(aid = aid_op, asset = asset, quote = quote)

# get the available columns to use as secondary y axis
secondary_y = list(performance_data['full_history_performance'].columns)
secondary_y.remove('timestamp')
secondary_y.remove('index')

# get the available assets
tokens = performance_data['tokens']

# print the performance data
print(performance_data['full_history_performance'].head())

# dash app 
app = dash.Dash(__name__)

# set the theme components to use
app.title = "Market Aid Analytics"

# Define the style for the dark background color
dark_style = {
    'background-color': '#1a1a1a',
    'color': '#ffffff'
}

# dash layout
app.layout = html.Div(style = dark_style, children = [

    # drop down menus for over all performance data
    dcc.Dropdown(
        id = 'secondary_y',
        options = [{'label': i, 'value': i} for i in secondary_y],
        value = secondary_y[0]
    ),

    dcc.Dropdown(
        id = 'dataframe-dropdown',
        options = [
            {'label': 'Trailing Six Hour', 'value': 'trailing_six_hour_performance'},
            {'label': 'Trailing Twelve Hour', 'value': 'trailing_twelve_hour_performance'},
            {'label': 'Trailing Day', 'value': 'trailing_day_performance'},
            {'label': 'Trailing Three Day', 'value': 'trailing_three_day_performance'},
            {'label': 'Trailing Week', 'value': 'trailing_week_performance'},
            {'label': 'Trailing Two Week', 'value': 'trailing_two_week_performance'},
            {'label': 'Full History', 'value': 'full_history_performance'},
        ],
        value = 'full_history_performance'
    ),

    # track the historical balance of the aid contract
    dcc.Graph(id = 'aid_history'),

    # track the performance vs hodl benchmark
    dcc.Graph(id = 'aid_performance_vs_hodl'),

    # track the performance vs asset mix benchmark
    dcc.Graph(id = 'aid_performance_vs_asset_mix'),

    # set the interval to 15 minute
    dcc.Interval(id = 'update-interval', interval = 15 * 60 * 1000, n_intervals = 0),

    # set an interval to 5 minutes for the fill tracking
    dcc.Interval(id = 'fill-tracking-interval', interval = 5 * 60 * 1000, n_intervals = 0),

    # add drop down menu to select the asset and quote for fill tracking
    dcc.Dropdown(
        id = 'asset-dropdown',
        options = [{'label': i, 'value': i} for i in tokens],
        value = tokens[0]
    ),

    dcc.Dropdown(
        id = 'quote-dropdown',
        options = [{'label': i, 'value': i} for i in tokens],
        value = tokens[1]
    ),

    # add a dropdown menu to select the time frame for fill tracking
    dcc.Dropdown(
        id = 'fill-timeframe-dropdown',
        options = [
            {'label': 'Trailing One Hour', 'value': 'trailing_one_hour_fill_tracking'},
            {'label': 'Trailing Three Hour', 'value': 'trailing_three_hour_fill_tracking'},
            {'label': 'Trailing Six Hour', 'value': 'trailing_six_hour_fill_tracking'},
            {'label': 'Trailing Twelve Hour', 'value': 'trailing_twelve_hour_fill_tracking'},
            {'label': 'Trailing Day', 'value': 'trailing_day_fill_tracking'},
            {'label': 'Trailing Three Day', 'value': 'trailing_three_day_fill_tracking'},
            {'label': 'Trailing Week', 'value': 'trailing_week_fill_tracking'},
            {'label': 'Trailing Two Week', 'value': 'trailing_two_week_fill_tracking'},
            {'label': 'Full History', 'value': 'full_history_fill_tracking'},
        ],
        value = 'full_history_fill_tracking'
    ),

    # add a graph to track the fill tracking data
    dcc.Graph(id = 'fill_tracking'),
])

@app.callback(
    [dash.dependencies.Output('aid_history', 'figure'),
    dash.dependencies.Output('aid_performance_vs_hodl', 'figure'),
    dash.dependencies.Output('aid_performance_vs_asset_mix', 'figure')],
        [dash.dependencies.Input('dataframe-dropdown', 'value'),
        dash.dependencies.Input('secondary_y', 'value'),
        dash.dependencies.Input('update-interval', 'n_intervals')]
)
def update_graph(selected_df, secondary_y, n_intervals):

    global performance_data
    global aid_op
    global bin_size

    # see which callback was triggered
    ctx = dash.callback_context

    if ctx.triggered:
        trigger = ctx.triggered[0]['prop_id']
        if trigger == 'update-interval.n_intervals':
            print('routine update')
            performance_data = data_pull(aid = aid_op, bin_size = bin_size)
        elif trigger == 'dataframe-dropdown.value':
            print('dataframe-dropdown.value')
        elif trigger == 'secondary_y.value':
            print('secondary_y.value')

    df = performance_data[selected_df]

    return {
        'data': [
            {
                "x": df['timestamp'],
                "y": df['total_balance_usd'],
                "type": "lines",
                "name": "Total Balance USD",
                "yaxis": "y1"
            },
            {
                "x": df['timestamp'],
                "y": df[secondary_y],
                "type": "lines",
                "name": secondary_y,
                "yaxis": "y2"
            },
        ],
        'layout': {
            "title": "Market Aid USD Balance History " + selected_df,
            "yaxis": {"title": "Total Balance USD", "side": "left"},
            "yaxis2": {"title": secondary_y, "side": "right", "overlaying": "y"},
        },
    }, {
        'data': [
            {
                "x": df['timestamp'],
                "y": df['hodl_strat_performance_delta'],
                "type": "lines",
                "name": "Performance Delta vs. HODL Strat (USD)",
                "yaxis": "y1"
            },
            {
                "x": df['timestamp'],
                "y": df[secondary_y],
                "type": "lines",
                "name": secondary_y,
                "yaxis": "y2"
            },
        ],
        'layout': {
            "title": " Market Aid Performance Delta vs. HODL Strat " + selected_df,
            "yaxis": {"title": "Performance Delta USD", "side": "left"},
            "yaxis2": {"title": secondary_y, "side": "right", "overlaying": "y"},
        },
    }, {
        'data': [
            {
                "x": df['timestamp'],
                "y": df['asset_mix_strat_performance_delta'],
                "type": "lines",
                "name": "Performance Delta vs. Ideal Mix (USD)",
                "yaxis": "y1"
            },
            {
                "x": df['timestamp'],
                "y": df[secondary_y],
                "type": "lines",
                "name": secondary_y,
                "yaxis": "y2"
            },
        ],
        'layout': {
            "title": " Market Aid Performance Delta vs. Asset Mix Strat " + selected_df,
            "yaxis": {"title": "Performance Delta USD", "side": "left"},
            "yaxis2": {"title": secondary_y, "side": "right", "overlaying": "y"},
        },
    }

@app.callback(
    dash.dependencies.Output('fill_tracking', 'figure'),
    [dash.dependencies.Input('asset-dropdown', 'value'),
    dash.dependencies.Input('quote-dropdown', 'value'),
    dash.dependencies.Input('fill-timeframe-dropdown', 'value'),
    dash.dependencies.Input('fill-tracking-interval', 'n_intervals')]
)
def update_fill_graph(asset, quote, timeframe, n_intervals):

    # get the fill tracking data for the selected timeframe
    global fill_tracking_data

    # see which callback was triggered
    ctx = dash.callback_context

    if ctx.triggered:
        trigger = ctx.triggered[0]['prop_id']
        if trigger == 'fill-tracking-interval.n_intervals':
            print('routine fill update')
            fill_tracking_data = fill_tracking(aid = aid_op, asset = asset, quote = quote)
        elif trigger == 'asset-dropdown.value':
            print('asset change')
            fill_tracking_data = fill_tracking(aid = aid_op, asset = asset, quote = quote)
        elif trigger == 'quote-dropdown.value':
            print('quote change')
            fill_tracking_data = fill_tracking(aid = aid_op, asset = asset, quote = quote)
        
    df = fill_tracking_data[timeframe]

    # add a stacked bar chart that shows the fill tracking data and the asset price as a line chart on the secondary y axis
    return {
        'data' : [        
            {'x': df['time_bin'], 'y': df['buy_amount'], 'type': 'bar', 'name': 'Buy Amount', 'base': 0},
            {'x': df['time_bin'], 'y': df['bought_amount'], 'type': 'bar', 'name': 'Bought Amount', 'base': 0},    
            {'x': df['time_bin'], 'y': df['sell_amount'], 'type': 'bar', 'name': 'Sell Amount', 'base': df['sell_amount'].max()},
            {'x': df['time_bin'], 'y': df['sold_amount'], 'type': 'bar', 'name': 'Sold Amount', 'base': df['sold_amount'].max()},
            {'x': df['time_bin'], 'y': df['price'], 'type': 'line', 'name': 'Asset Price', 'yaxis': 'y2'}
        ],
        'layout' : {
            'title' : 'Fill Tracking over ' + timeframe,
            'barmode': 'stack',
            'xaxis' : {'title' : 'Time Bin'},
            'yaxis' : {'title' : 'Amounts'},
            'yaxis2' : {'title' : asset + ' Price', 'overlaying': 'y', 'side': 'right'}
        }
    }

if __name__ == "__main__":
    app.run_server(debug=True)

# TODO: 
# 1. figure out how this will be run within a node environment
    # a. specifically, how we will pass in relevant data to the dashboard such as a node enpoint or a market aid address