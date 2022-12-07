import os
import rubi as Rubi
from web3 import Web3
# from rubi import Rubicon
from dotenv import load_dotenv

load_dotenv()

# set the env variables
OP_MAINNET_NODE = os.getenv("OP_MAINNET_NODE")
OP_GOERLI_NODE = os.getenv("OP_GOERLI_NODE")
DEV_EOA = os.getenv("DEV_EOA")
DEV_KEYS = os.getenv("DEV_KEYS")

# ensure the env variables are set
if None in [OP_MAINNET_NODE, OP_GOERLI_NODE, DEV_EOA, DEV_KEYS]:
    raise ValueError("Please set the environment variables, either update or create a .env file")

# create a web3 instance
w3 = Web3(Web3.HTTPProvider(OP_MAINNET_NODE))

# create a rubicon instance
rubi = Rubi.Rubicon(w3, wallet=DEV_EOA, key=DEV_KEYS)

# check that the factory is pointed at the market contract
assert rubi.factory.rubicon_market() == rubi.market.address

# check that the user does not currently have any market aid contracts deployed 
aids = rubi.factory.get_user_market_aids(rubi.wallet)

if aids:
    print("You already have a market aid contract deployed, lets connect to it!")
    aid_address = aids[0]
    aid = rubi.aid(aid_address)
else:
    print("You do not have a market aid contract deployed, lets deploy one!")
    rubi.factory.create_market_aid_instance()

    aids = rubi.factory.get_user_market_aids(rubi.wallet)
    aid_address = aids[0]
    aid = rubi.aid(aid_address)

    # check that the aid was deployed and connect to it 
    if aid.address:
        print("Market aid deployed!")
        aid = rubi.aid(aid.address)

# check that the aid is connected to the correct market and print out the aid address
assert aid.rubicon_market_address() == rubi.market.address
print("Market aid address: ", aid.address)

# access the rolodex of helpful addresses based upon the chain id of the node that is being used
chain = rubi.chain
rolodex = Rubi.contracts.helper.networks[chain]()

# get the weth and usdc addresses
weth = rolodex.weth
usdc = rolodex.usdc

# connect to the weth and usdc contracts
weth = rubi.token(weth)
usdc = rubi.token(usdc)

# check that the contracts connected match the rolodex addresses
assert weth.address == rolodex.weth
assert usdc.address == rolodex.usdc