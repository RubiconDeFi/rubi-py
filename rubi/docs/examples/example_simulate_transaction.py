import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import Client, NewMarketOrder
from rubi import EmitOfferEvent, Transaction, NewLimitOrder, OrderSide

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

# create client
client = Client.from_http_node_url(
    http_node_url=http_node_url,
    wallet=wallet,
    key=key,
)

# add the WETH/USDC pair to the client
client.add_pair(pair_name="WETH/USDC")

# Place a new limit order
limit_order = NewLimitOrder(
    pair_name="WETH/USDC",
    order_side=OrderSide.BUY,
    size=Decimal("1"),
    price=Decimal("10"),
)

transaction = Transaction(orders=[limit_order], simulate=True)

transaction_simulation_result = client.place_limit_order(transaction=transaction)

log.info(transaction_simulation_result)
