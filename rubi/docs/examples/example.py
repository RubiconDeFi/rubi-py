import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import EmitOfferEvent, Transaction, NewLimitOrder, OrderSide
from rubi import Client, NetworkName

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
client = Client.from_network_name(
    network_name=NetworkName.OPTIMISM_GOERLI,
    http_node_url=http_node_url,
    wallet=wallet,
    key=key,
    message_queue=queue
)

# add the WETH/USDC pair to the client
client.add_pair(pair_name="WETH/USDC", base_asset_allowance=Decimal("0.2"), quote_asset_allowance=Decimal("1000"))

# start listening to offer events created by your wallet on the WETH/USDC market and the WETH/USDC orderbook
client.start_event_poller("WETH/USDC", event_type=EmitOfferEvent)
client.start_orderbook_poller("WETH/USDC")

# Place a new limit order
limit_order = NewLimitOrder(
    pair_name="WETH/USDC",
    order_side=OrderSide.BUY,
    size=Decimal("1"),
    price=Decimal("1914.13")
)

client.place_limit_order(
    transaction=Transaction(
        orders=[limit_order]
    )
)

# Print events and order books
while True:
    message = queue.get()

    log.info(message)
