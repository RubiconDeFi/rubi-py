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

from rq import Queue
from worker import conn
import json

from tools import data_pull, fill_tracking

q = Queue(connection=conn)

print("hello, DeFi Cowboy!")

load_dotenv()

# get the node url
BNF_HTTP = os.getenv('BNF_HTTP')
#GOERLI_HTTP = os.getenv('OP_GOERLI_NODE')

# create a web3 instance
w3_op = Web3(Web3.HTTPProvider(BNF_HTTP))
#w3_goerli = Web3(Web3.HTTPProvider(GOERLI_HTTP))

# create a rubicon instance
#rubi_goerli = Rubi.Rubicon(w3_goerli)
rubi_op = Rubi.Rubicon(w3_op)

#aid_goerli = os.getenv('MARKET_AID_OPTIMISM_GOERLI')
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

# get the performance data
#performance_data = data_pull(aid = aid_op, bin_size = bin_size)
performance_data = q.enqueue(data_pull, rubi_op, aid_op, bin_size, op_asset_mix)

# get the fill tracking data
# TODO: we need some type of error handling here and the ability to load in from the token list
asset = 'WETH'
quote = 'USDC'
#fill_tracking_data = fill_tracking(aid = aid_op, asset = asset, quote = quote)
fill_tracking_data = q.enqueue(fill_tracking, rubi_op, aid_op, asset, quote)

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