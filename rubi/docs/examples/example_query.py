import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue
import pickle

from dotenv import load_dotenv

from rubi import Client
from rubi import (
    EmitOfferEvent,
    Transaction,
    NewLimitOrder,
    OrderSide,
    DetailedOrderBook
)

# load from env file
load_dotenv("../../local.env")

# you local.env should look like this:
# HTTP_NODE_URL={ the url of the node you are using to connect to the network }
# DEV_WALLET={ your wallet address 0x... }
# DEV_KEY={ your private key }

# set logging config
log.basicConfig(level=log.INFO)

# set the env variables
http_node_url = os.getenv("HTTP_NODE_URL")
wallet = os.getenv("DEV_WALLET")
key = os.getenv("DEV_KEY")

# create a queue to receive messages
queue = Queue()

# create client
client = Client.from_http_node_url(http_node_url=http_node_url, message_queue=queue)
'''
# open_offers = client.market_data.get_limit_orders(
open_offers = client.get_offers(    
    pair_name="WETH/USDC",
    book_side=OrderSide.NEUTRAL,
    open=False,
    maker=client.wallet,
    first=100,
    formatted=False,
)
print(open_offers)

# pickle the dataframe
with open('open_offers.pickle', 'wb') as handle:
    pickle.dump(open_offers, handle, protocol=pickle.HIGHEST_PROTOCOL)
'''
# load the dataframe
with open('open_offers.pickle', 'rb') as handle:
    open_offers = pickle.load(handle)

print(open_offers.shape)
print(open_offers.columns)
print(open_offers.head(1))

offers = client.market_data.offer_query.dataframe_to_limit_orders(
    df=open_offers,
    pair_name="WETH/USDC",)
print(offers)

'''
# query the open WETH/USDC offers for your wallet
open_offers = client.market_data.get_limit_orders(
    pair_name="WETH/USDC",
    book_side=OrderSide.NEUTRAL,
    open=False,
    maker=client.wallet,
    first=100,
)
# print(open_offers)

data = (open_offers[0], open_offers[1])

# create a detailed order book for WETH/USDC
book = DetailedOrderBook.from_rubicon_offer_book(data)
print(book.best_bid_offer())
'''