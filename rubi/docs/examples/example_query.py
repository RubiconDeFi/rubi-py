import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import Client
from rubi import (
    EmitOfferEvent,
    Transaction,
    NewLimitOrder,
    OrderSide,
    DetailedOrderBook,
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
client = Client.from_http_node_url(
    http_node_url=http_node_url, wallet=wallet, key=key, message_queue=queue
)

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
