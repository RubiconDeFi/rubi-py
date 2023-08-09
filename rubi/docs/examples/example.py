import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import Client, OrderEvent, RubiconMarketApproval
from rubi import EmitOfferEvent, NewLimitOrder, OrderSide

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
    http_node_url=http_node_url,
    custom_token_addresses_file="custom_token_addresses.yaml",
    wallet=wallet,
    key=key,
    message_queue=queue,
)

# approve WETH and USDC to trade them on Rubicon
client.approve(approval=RubiconMarketApproval(amount=Decimal("1"), token="WETH"))
client.approve(approval=RubiconMarketApproval(amount=Decimal("2000"), token="USDC"))

# Construct a new limit order
limit_order = NewLimitOrder(
    pair_name="WETH/USDC",
    order_side=OrderSide.BUY,
    size=Decimal("1"),
    price=Decimal("1914.13"),
)

transaction = client.limit_order(order=limit_order)

log.info(transaction)

# Place the limit order by executing the transaction
result = client.execute_transaction(transaction=transaction)

# Get the offer id from the transaction result
offer = None

for event in result.events:
    if isinstance(event, OrderEvent):
        offer = event
        break

log.info(offer)
