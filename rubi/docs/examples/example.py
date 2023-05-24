import logging as log
import os

from dotenv import load_dotenv

from rubi.contracts_v2 import RubiconMarket, ERC20
from rubi.network import Network, NetworkName

# load from env file
load_dotenv("../../local.env")

# you local.env should look like this:
# OP_GOERLI_NODE={ the url of the node you are using to connect to the network }
# DEV_WALLET= { your wallet address 0x... }
# DEV_KEY={ your private key }


# set logging config
log.basicConfig(level=log.INFO)

# set the env variables
http_node_url = os.getenv("OP_GOERLI_NODE")
wallet = os.getenv("DEV_WALLET")
key = os.getenv("DEV_KEY")

# create network instance
network = Network.build(name=NetworkName.OPTIMISM_GOERLI, http_node_url=http_node_url)

# create read only rubicon market from the network
read_only_market = RubiconMarket.from_network(network=network)

# create coin instances from the network
weth = ERC20.from_network(name="WETH", network=network, wallet=wallet, key=key)
read_only_usdc = ERC20.from_network(name="USDC", network=network)

# get the id of the best bid on the WETH/USDC market
# bid_id = read_only_market.get_best_offer(sell_gem=read_only_usdc.address, buy_gem=read_only_weth.address)

# log.info(f"bid id: {bid_id}")

# get the information on the bid
# log.info(read_only_market.get_offer(bid_id))

# create a permissioned rubicon market
permissioned_market = RubiconMarket.from_network(network=network, wallet=wallet, key=key)

# place an offer to sell 0.1 WETH for 1980 USDC
log.info(permissioned_market.offer(
    pay_amt=100000000000000000,
    pay_gem=weth.address,
    buy_amt=198000000000000000000,
    buy_gem=read_only_usdc.address,
))

# log.info(weth.transfer(
#     recipient=network.w3.to_checksum_address("0xC30276833798867C1dBC5c468bf51cA900b44E4c"),
#     amount=1
# ))
