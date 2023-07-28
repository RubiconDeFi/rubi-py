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
    first=10,
    formatted=False,
)
print(open_offers)

# pickle the dataframe
with open('open_offers.pickle', 'wb') as handle:
    pickle.dump(open_offers, handle, protocol=pickle.HIGHEST_PROTOCOL)

'''
'''
# load the dataframe
with open('open_offers.pickle', 'rb') as handle:
    open_offers = pickle.load(handle)

offers = client.market_data.offer_query.dataframe_to_limit_orders(
    df=open_offers,
    pair_name="WETH/USDC",)

# iterate through list and make bids/asks
bids = []
asks = []
for offer in offers:
    if offer.order_side == OrderSide.BUY:
        bids.append(offer)
    else:
        asks.append(offer)

'''

# query the open WETH/USDC offers for your wallet
open_offers = client.market_data.get_limit_orders(
    pair_name="WETH/USDC",
    book_side=OrderSide.NEUTRAL,
    open=False,
    #maker=client.wallet,
    first=100,
    removed_block_start=10000000,
)
# print(open_offers)


data = (open_offers[0], open_offers[1])
#data = (bids, asks)

# create a detailed order book for WETH/USDC
book = DetailedOrderBook.from_rubicon_offer_book(data)

# go through and remove all the bids
test = book.best_bid_offer()
test.price = Decimal("4200.69")
book.add_order(test)
print(book.best_bid_offer())
'''
while best_bid != None:
    print(best_bid)
    print('-------------------------')
    print('the current best bid is: ', best_bid.id)
    print('the current best price is: ', best_bid.price)
    print('-------------------------')
    book.remove_order(best_bid.id)
    best_bid = book.best_bid_offer()

print('this should be the first bid: ', first_bid.id)
book.add_order(first_bid)

print(book.best_bid_offer())

print(best_bid)
print(best_bid.id)
'''
#book.remove_order(best_bid.id)

#print(book.best_bid_offer())
#print(book.best_bid_offer().id)
