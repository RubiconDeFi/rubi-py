import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import NewLimitOrder, OrderSide
from rubi import (
    OrderTrackingClient,
)

# load from env file
load_dotenv("local.env")

# you local.env should look like this:
# HTTP_NODE_URL={ the url of the node you are using to connect to the network }
# DEV_WALLET={ your wallet address 0x... }
# DEV_KEY={ your private key }

# set logging config
log.basicConfig(level=log.INFO)

# set the env variables
http_node_url = os.getenv("HTTP_NODE_URL")
wallet = os.getenv("PROD_WALLET")
key = os.getenv("PROD_KEY")

# create a queue to receive messages
queue = Queue()

# create client
client = OrderTrackingClient.from_http_node_url(
    http_node_url=http_node_url,
    pair_names=["WETH/USDC", "WBTC/USDC"],
    wallet=wallet,
    key=key,
    message_queue=queue,
)

# Log our open limit orders
log.info(f"Open limit orders: {client.open_limit_orders}")

# place a new limit order

transaction = client.limit_order(
    NewLimitOrder(
        pair_name="WETH/USDC",
        order_side=OrderSide.BUY,
        size=Decimal("0.01"),
        price=Decimal("1000"),
    )
)

# place the transaction
result = client.execute_transaction(transaction=transaction)

log.info(result.transaction_status)

# Log our open limit orders and we should see our new order
log.info(f"Open limit orders: {client.open_limit_orders}")
