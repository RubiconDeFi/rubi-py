import os
import pickle

from rubi_network.network import Network
from rubi import Client, OrderSide, DetailedOrderBook

from dotenv import load_dotenv
from multiprocessing import Queue

load_dotenv('.env')

op_node = os.getenv('OP_MAIN_HTTP_NODE_URL')

queue = Queue()

# the timestamp of the first rewards period
start_time = 1688187600
end_time = 1690866000

# the block number of the first rewards period
start_block = 106300428 # TODO: get actual block and not estimate
end_block = 107710993

client = Client.from_http_node_url(
    http_node_url=op_node,
    message_queue=queue,
)
# load the pickled data 
# TODO: there has to be a cleaner way to do this with file strings
with open('weth_usdc_trades.pickle', 'rb') as f:
   weth_usdc_trades = pickle.load(f)
with open('weth_usdc_offers.pickle', 'rb') as f:
   weth_usdc_offers = pickle.load(f)

book = DetailedOrderBook(
   bids=None,
   asks=None,
)

network = Network.from_df(
   client=client,
   pair_names=["WETH/USDC"],
   offers=[weth_usdc_offers],
   trades=[weth_usdc_trades]
)

network.build_graph(
   pair_name="WETH/USDC",
   # graph_type
   # book_history,
   display=True,
)