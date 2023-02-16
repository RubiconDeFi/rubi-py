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
    
    # get the aid history
    op_aid_history = rubi_op.data.market_aid_optimism_processing.build_aid_history(aid = aid, bin_size = bin_size)
    full_data = op_aid_history['data']
    tokens = op_aid_history['tokens']

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
        'full_history_performance': full_history_performance
    }

    return performance_data

# get the performance data
performance_data = data_pull(aid = aid_op, bin_size = bin_size)

# get the available columns to use as secondary y axis
secondary_y = list(performance_data['full_history_performance'].columns)
secondary_y.remove('timestamp')
secondary_y.remove('index')

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

    # set the interval to 1 minute
    dcc.Interval(id = 'update-interval', interval = 15 * 60 * 1000, n_intervals = 0)
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

if __name__ == "__main__":
    app.run_server(debug=True)

# TODO: 
# 1. figure out how this will be run within a node environment
    # a. specifically, how we will pass in relevant data to the dashboard such as a node enpoint or a market aid address