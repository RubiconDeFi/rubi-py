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

# get the aid history
op_aid_history = rubi_op.data.market_aid_optimism_processing.build_aid_history(aid = aid_op, bin_size = bin_size)
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

print(op_aid_history['data'].head())

# dash app 
app = dash.Dash(__name__)

# dash layout
app.layout = html.Div(
    children = [
        html.H1(children = "Market Aid Dashboard",
                style={"fontSize": "48px", "color": "red"},
        ),
        html.P(
            children = "This dashboard is designed to monitor the status of a market aid instance"
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": op_aid_history['data']['timestamp'],
                        "y": op_aid_history['data']['total_balance_usd'], 
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid USD Balance History"},
            },           
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": op_aid_history['data']['timestamp'],
                        "y": op_aid_history['data']['WETH_price'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid WETH Price History"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": full_history_performance['timestamp'],
                        "y": full_history_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_two_week_performance['timestamp'],
                        "y": trailing_two_week_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (2 Week Trailing)"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_week_performance['timestamp'],
                        "y": trailing_week_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (1 Week Trailing)"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_three_day_performance['timestamp'],
                        "y": trailing_three_day_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (3 Day Trailing)"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_day_performance['timestamp'],
                        "y": trailing_day_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (1 Day Trailing)"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_twelve_hour_performance['timestamp'],
                        "y": trailing_twelve_hour_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (12 Hour Trailing)"},
            },
        ),
        dcc.Graph(
            figure={
                'data': [
                    {
                        "x": trailing_six_hour_performance['timestamp'],
                        "y": trailing_six_hour_performance['hodl_strat_performance_delta'],
                        "type": "lines",
                    },
                ],
                'layout': {"title": "Market Aid Trading Delta vs HODL Strategy (6 Hour Trailing)"},
            },
        )
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)

# TODO: 
# 1. figure out how this will be run within a node environment
    # a. specifically, how we will pass in relevant data to the dashboard such as a node enpoint or a market aid address