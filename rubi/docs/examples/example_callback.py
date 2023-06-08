import logging as log
import os
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv

from rubi import Client, ERC20
from rubi import EmitOfferEvent, Transaction, NewLimitOrder, OrderSide, BaseEvent

from typing import Union, List, Optional, Dict, Type, Any, Callable
from web3.types import EventData

import requests
import json
from functools import partial

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

####################################
# Callbacks
####################################

def event_handler(pair_name: str, event_type: Type[BaseEvent], event_data: EventData) -> None:
    """A basic callback function that demonstrates the pattern for handling events.

    :param pair_name: Name of the pair associated with the event.
    :type pair_name: str
    :param event_type: Type of the event.
    :type event_type: Type[BaseEvent]
    :param event_data: Data of the retrieved event.
    :type event_data: EventData
    """
    raw_event = event_type(block_number=event_data["blockNumber"], **event_data["args"])
    print('testing callback:')
    print(raw_event)

def compare_eth_offer(pair_name: str, event_type: Type[BaseEvent], event_data: EventData, base_asset: ERC20, quote_asset: ERC20) -> None:
    """This is a simple callback function that checks if the offer is an ETH offer, and if so get the current ETH price from Coinbase."""

    # handle the raw event
    raw_event = event_type(block_number=event_data["blockNumber"], **event_data["args"])

    # we know this type is an EmitOfferEvent, so we can cast it
    if raw_event.buy_gem == base_asset.address:
        print('this is a buy offer (buying WETH with USDC)')
        weth_amt = raw_event.buy_amt
        usdc_amt = raw_event.pay_amt
        weth_amt_formatted = base_asset.to_decimal(weth_amt)
        usdc_amt_formatted = quote_asset.to_decimal(usdc_amt)
        print(f'an offer to buy {weth_amt_formatted} WETH with {usdc_amt_formatted} USDC at a price of {Decimal(usdc_amt_formatted/weth_amt_formatted)} USDC/WETH')

    elif raw_event.pay_gem == base_asset.address:
        print('this is a sell offer (selling WETH for USDC)')
        weth_amt = raw_event.pay_amt
        usdc_amt = raw_event.buy_amt
        weth_amt_formatted = base_asset.to_decimal(weth_amt)
        usdc_amt_formatted = quote_asset.to_decimal(usdc_amt)
        print(f'an offer to sell {weth_amt_formatted} WETH for {usdc_amt_formatted} USDC at a price of {Decimal(usdc_amt_formatted/weth_amt_formatted)} USDC/WETH')
    
    # check if the base asset is ETH
    if base_asset.symbol == "WETH":

        # get the current ETH price 
        response = requests.get('https://api.coinbase.com/v2/prices/ETH-USD/spot')
        data = response.json()

        if response.status_code == 200:
            price = data['data']['amount']
            print(f'the current ETH price on coinbase is: {price}')
        else:
            return "Error: Unable to retrieve price"

# create a queue to receive messages
queue = Queue()

# create client
client = Client.from_http_node_url(
    http_node_url=http_node_url,
    custom_token_addresses_file="custom_token_addresses.yaml",
    wallet=wallet,
    key=key,
    message_queue=queue
)

# initialize ERC20 clients for the base and quote assets
base_asset = ERC20.from_network(name='WETH', network=client.network)
quote_asset = ERC20.from_network(name='USDC', network=client.network)

# add the WETH/USDC pair to the client - optional allowances can be set here
client.add_pair(pair_name="WETH/USDC") # , base_asset_allowance=Decimal("1"), quote_asset_allowance=Decimal("2000")

# start listening to offer events created by your wallet on the WETH/USDC market and the WETH/USDC orderbook
client.start_event_poller("WETH/USDC", event_type=EmitOfferEvent, event_handler=partial(compare_eth_offer, base_asset=base_asset, quote_asset=quote_asset))

# now we can create an offer and see the callback in action
limit_order = NewLimitOrder(
    pair_name="WETH/USDC",
    order_side=OrderSide.BUY,
    size=Decimal("0.001"),
    price=Decimal("1914.13")
)

transaction_result = client.place_limit_order(
    transaction=Transaction(
        orders=[limit_order]
    )
)

log.info(transaction_result)

# Print events and order books
while True:
    message = queue.get()

    log.info(message)

# Key Considerations

# the callback function is utilimately passed to the event poller on the base contract, you can find the function here: https://github.com/RubiconDeFi/rubi-py/blob/13b746067d2dd4208cb2004b824370794b63efd5/rubi/rubi/contracts/base_contract.py#L155
# the pattern for the callback function is as follows: event_handler(pair_name, event_type, event_data) where: 
# :param pair_name: The name of the event pair.
# :type pair_name: str
# :param event_type: The type of the event.
# :type event_type: Type[BaseEvent]
# :param event_data: The filtered event data of the log from the transaction. 
# :type event_data: LogFilter (you can read more here: https://web3py.readthedocs.io/en/stable/filters.html#web3.utils.filters.LogFilter.set_data_filters)

# event types can be found here in the documentation: https://rubi.readthedocs.io/en/latest/rubi.contracts.types.html#rubi-contracts-types-package