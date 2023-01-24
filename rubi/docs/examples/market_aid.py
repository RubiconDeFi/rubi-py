import os
import rubi as Rubi
from web3 import Web3
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

# get the current nonce of the dev account
nonce = rubi.w3.eth.get_transaction_count(rubi.wallet)

# check that the factory is pointed at the market contract
assert rubi.factory.rubicon_market() == rubi.market.address

# check that the user does not currently have any market aid contracts deployed 
aids = rubi.factory.get_user_market_aids(rubi.wallet)

if aids:
    print("\nyou already have a market aid contract deployed, lets connect to it!\n")
    aid_address = aids[0]
    aid = rubi.aid(aid_address)
else:
    print("\nyou do not have a market aid contract deployed, lets deploy one!\n")
    rubi.factory.create_market_aid_instance(nonce = nonce)
    nonce += 1

    aids = rubi.factory.get_user_market_aids(rubi.wallet)
    aid_address = aids[0]
    aid = rubi.aid(aid_address)

    # check that the aid was deployed and connect to it 
    if aid.address:
        print("market aid deployed!")
        aid = rubi.aid(aid.address)

# check that the aid is connected to the correct market and print out the aid address
assert aid.rubicon_market_address() == rubi.market.address
print("market aid address: ", aid.address, "\n")

# access the rolodex of helpful addresses based upon the chain id of the node that is being used
chain = rubi.chain
rolodex = Rubi.contracts.helper.networks[chain]()

# connect to the weth and usdc contracts - rolodex stores the address of some of the most popular tokens
weth = rubi.token(rolodex.weth)
usdc = rubi.token(rolodex.usdc)

# check that the contracts connected match the rolodex addresses
assert weth.address == rolodex.weth
assert usdc.address == rolodex.usdc

# transfer some weth and usdc to the aid contract
weth.transfer(aid.address, 1, nonce=nonce)
nonce += 1
usdc.transfer(aid.address, 1, nonce=nonce)
nonce += 1

# check the current balance of the aid contract
balances = aid.get_strategist_total_liquidity(weth.address, usdc.address, rubi.wallet)

# important to notice that the balances are returned in the order of [weth, usdc, outstanding trades], opposite of the order of the arguments
weth_balance = balances[1]
usdc_balance = balances[0]
oustanding_trades = balances[2]

# print out the current balance of the aid contract
print("current balance of aid contract -> ", weth.symbol(), weth_balance / (10 ** weth.decimal), usdc.symbol(), usdc_balance / (10 ** usdc.decimal), "\n")
print("does the contract have outstanding trades? [T/F] -> ", oustanding_trades, "\n")

if oustanding_trades:

    print("the contract has outstanding trades, lets cancel them!\n")
    
    # get the oustanding trades of the aid contract
    trades = aid.get_outstanding_strategist_trades(weth.address, usdc.address, rubi.wallet)

    # print out the oustanding trades of the aid contract
    print("oustanding trades -> ", trades, "\n")

    # if there are any oustanding trades, lets cancel them
    aid.scrub_strategist_trades(trades, gas=3000000, nonce=nonce)
    nonce += 1

# place a batch market making trade through the aid contract
# this trade will create two new market offers, one selling the asset and one buying the asset 
# this is an offer to sell 0.01 ETH for 1000 USDC or an offer to buy 0.01 ETH for 1 USDC
aid.batch_market_making_trades([weth.address, usdc.address], [10000000000000000], [1000000000], [1000000], [10000000000000000], nonce = nonce)
nonce += 1

# now requote all of the outstanding trades
# this is an offer to sell 0.01 ETH for 10000 USDC or an offer to buy 0.01 ETH for .1 USDC
batch_requote = aid.batch_requote_all_offers([weth.address, usdc.address], [10000000000000000], [10000000000], [100000], [10000000000000000], nonce = nonce)
nonce += 1

# wait for the transaction to be mined
hash = rubi.w3.eth.wait_for_transaction_receipt(batch_requote['hash'])

# now cancel all of the outstanding trades
if hash: 

    # get the oustanding trades of the aid contract
    trades = aid.get_outstanding_strategist_trades(weth.address, usdc.address, rubi.wallet)

    # if there are any oustanding trades, lets cancel them
    scrub = aid.scrub_strategist_trades(trades, gas=3000000, nonce=nonce)
    nonce += 1

    # wait for the transaction and check that the trades were cancelled
    hash = rubi.w3.eth.wait_for_transaction_receipt(scrub['hash'])
    if hash:
        print("all trades for the strategists assset / quote pair were cancelled!")
