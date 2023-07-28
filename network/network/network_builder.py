import networkx as nx
from rubi import Client, OrderSide, DetailedOrderBook, LimitOrder, Trade # TODO: add the ability to simply initialize an empty book 

from nodes import TraderNode, Edge
from network_analysis import find_pure_pairs
from data import get_book_history, Cancel

import os
import pandas as pd
import logging as log
import numpy as np
from dotenv import load_dotenv
from multiprocessing import Queue

# load from env file
load_dotenv(".env")

g = nx.DiGraph()

# set logging config
log.basicConfig(level=log.INFO)

# set the env variables
http_node_url = os.getenv("HTTP_NODE_URL")
print('the node url is: ', http_node_url)
etherscan_api = os.getenv("ETHERSCAN_API")
mainnet_etherscan_api = os.getenv("MAINNET_ETHERSCAN_API")

# create a queue to receive messages
queue = Queue()

try: 
    book = DetailedOrderBook.from_rubicon_offer_book(([], []))
except:
    print('failed to initialize the book')
    exit()

# create client
client = Client.from_http_node_url(
    http_node_url=http_node_url,
    message_queue=queue
)

start_time = 1688187600
end_time = 1690606800
#erc = client.get_network_tokens()['WETH']
stables = ['USDC', 'USDT', 'DAI']

# Initialize an empty directed graph
order_book_history = get_book_history(client, "DAI/USDC", 107481004)

# get the min block number
min_block = min(order_book_history.keys())
print(order_book_history[min_block])

# get the keys and sort them in ascending order
blocks = list(order_book_history.keys())
blocks.sort()



book = None
bids = []
asks = []

for block in blocks: 

    # get the keys and sort them in ascending order
    block_indexes = list(order_book_history[block].keys())
    block_indexes.sort()

    for block_index in block_indexes:

        log_indexes = list(order_book_history[block][block_index].keys())
        log_indexes.sort()

        for log_index in log_indexes:

            event = order_book_history[block][block_index][log_index]

            if isinstance(event, LimitOrder):
                book.add_order(event)
            elif isinstance(event, Trade):
                # TODO: we need to handle the side here, trade currently does not have a side
                book.update_order(event.order_id, event.take_amt, event.give_amt)
            elif isinstance(event, Cancel):
                book.remove_order(event.id)


            print('this is block: ', block, ' block index: ', block_index, ' log index: ', log_index)
            print(order_book_history[block][block_index][log_index])

print(book)

#block_number=107481004

# load the trades 
'''
trades = client.get_trades(pair_name="DAI/USDC", book_side=OrderSide.NEUTRAL, first=10, start_time=start_time, end_time=end_time)
trade_objects = client.market_data.get_trades_objects(pair_name="DAI/USDC", book_side=OrderSide.NEUTRAL, first=10, start_time=start_time, end_time=end_time)
trades = trades.sort_values(by=['block_number', 'block_index', 'log_index']).reset_index(drop=True)

trades['usd_amt'] = 0
trades['usd_amt'] = np.where(trades['give_gem'].isin(stables), trades['give_amt'], trades['take_amt'])

# pickle the trades
trades.to_pickle('dai_usdc.pkl')

# load the trades
trades = pd.read_pickle('dai_usdc.pkl')

print('dai_usdc: ', trades.columns)

#trade_objects = client.market_data.trade_query.dataframe_to_trades(trades)

print(trade_objects)

# Process trades
for index, trade in trades.iterrows():

    maker = trade['offer_from_address']
    taker = trade['from_address']
    usd_amt = trade['usd_amt']

    # Add/update maker node
    if maker not in g:
        g.add_node(maker, data=TraderNode(maker))
    g.nodes[maker]['data'].make_trade(usd_amt)

    # Add/update taker node
    if taker not in g:
        g.add_node(taker, data=TraderNode(taker))
    g.nodes[taker]['data'].make_trade(usd_amt)

    # Add/update the edge # TODO: we may want to use bidirectional edges
    # for now, the edge is directed from maker to taker
    if not g.has_edge(maker, taker):
        g.add_edge(maker, taker, data=Edge())
    g.edges[maker, taker]['data'].add_trade(usd_amt)

pure_pairs = find_pure_pairs(g)
print(f"Pairs where 100% of their trades are with each other: {pure_pairs}")
'''