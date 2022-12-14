import os
import time
import json
import pytest
import logging as log
from eth_utils import to_wei
from eth_tester import PyEVMBackend
from web3 import EthereumTesterProvider, Web3

from rubi import Rubicon

# the main structural choice here is the utilization of rubi's ability to pass in a contract object to initiliaze the class when the network (in this case EthereumTesterProvider) does not have data in the rolodex
# so, we are going to deploy and initialize the contracts in a fixture that will pass back the Rubicon object along with the contract objects in a dictionary

# set a fixture to return a tester provider intance 
@pytest.fixture
def tester_provider():
    eth_tester_provider = EthereumTesterProvider()
    eth_tester_provider.ethereum_tester.backend = PyEVMBackend.from_mnemonic(
        'test test test test test test test test test test test junk',
        genesis_state_overrides={'balance': to_wei(1000000, 'ether')}
    )
    # return EthereumTesterProvider()
    return eth_tester_provider

# set a fixture to return the eth_tester object from the tester provider instance
@pytest.fixture
def eth_tester(tester_provider):
    return tester_provider.ethereum_tester

# set a fixture to return a web3 instance instantiated from the tester provider
@pytest.fixture
def w3(tester_provider):
    return Web3(tester_provider)

# a function to add an account to the eth_tester object given the private key
@pytest.fixture
def add_account(eth_tester):

    new = eth_tester.add_account('0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d')
    return {'address' : new, 'key': '0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d'}

# a function to add another account to the eth_tester object given the private key
@pytest.fixture
def add_account_buyer(eth_tester):

    new = eth_tester.add_account('0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420')
    return {'address' : new, 'key': '0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420'}

# set a fixture to initialize a dictionary of erc20 contracts
@pytest.fixture
def erc20s(market_contract, add_account, add_account_buyer, eth_tester, w3):

    # set the test addresses
    deploy_address = eth_tester.get_accounts()[0]
    user_one = eth_tester.get_accounts()[1]
    user_two = eth_tester.get_accounts()[2]
    user_new = add_account['address']
    user_buyer = add_account_buyer['address']

    # load the contract abi and bytecode
    path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/ERC20MockDecimals.json"
    with open(path, 'r') as f:
        contract_interface = json.load(f)
    f.close()
    abi = contract_interface["abi"]
    bytecode = contract_interface["bytecode"]

    # set up the contract instance 
    erc20_deployement = w3.eth.contract(abi=abi, bytecode=bytecode)

    # set the constructor arguments -> cow_setup = name, symbol, supply, decimals
    supply = 420 * 10**18

    # deploy the contract
    cow_deploy = erc20_deployement.constructor("defi cowboy", "COW", supply, 18).transact({'from': deploy_address})
    eth_deploy = erc20_deployement.constructor("ether", "ETH", supply, 18).transact({'from': deploy_address})
    blz_deploy = erc20_deployement.constructor("blaze it", "BLZ", supply, 18).transact({'from': deploy_address})

    # get the contract address
    cow_receipt = w3.eth.wait_for_transaction_receipt(cow_deploy, 180)
    eth_receipt = w3.eth.wait_for_transaction_receipt(eth_deploy, 180)
    blz_receipt = w3.eth.wait_for_transaction_receipt(blz_deploy, 180)

    # connect to the contract
    try:
        cow = w3.eth.contract(address=cow_receipt.contractAddress, abi=abi)
        eth = w3.eth.contract(address=eth_receipt.contractAddress, abi=abi)
        blz = w3.eth.contract(address=blz_receipt.contractAddress, abi=abi)
    except Exception as e:
        log.warning('there was an error connecting to the erc20 contracts: ', e)

    # send 100 tokens & 100 eth from the deployer to user_new and user_buyer
    w3.eth.send_transaction({'from': deploy_address, 'to': user_new, 'value': 100 * 10**18})
    w3.eth.send_transaction({'from': deploy_address, 'to': user_buyer, 'value': 100 * 10**18})
    cow.functions.transfer(user_new, 100 * 10**18).transact({'from': deploy_address})
    eth.functions.transfer(user_new, 100 * 10**18).transact({'from': deploy_address})
    blz.functions.transfer(user_new, 100 * 10**18).transact({'from': deploy_address})
    cow.functions.transfer(user_buyer, 100 * 10**18).transact({'from': deploy_address})
    eth.functions.transfer(user_buyer, 100 * 10**18).transact({'from': deploy_address})
    blz.functions.transfer(user_buyer, 100 * 10**18).transact({'from': deploy_address})

    # set the max approval for the erc20s
    max_approval = 2**256 - 1

    # approve the market contract to spend the strategist's tokens
    cow.functions.approve(market_contract.address, max_approval).transact({'from': deploy_address})
    cow.functions.approve(market_contract.address, max_approval).transact({'from': user_one})
    cow.functions.approve(market_contract.address, max_approval).transact({'from': user_two})
    cow.functions.approve(market_contract.address, max_approval).transact({'from': user_new})
    cow.functions.approve(market_contract.address, max_approval).transact({'from': user_buyer})
    eth.functions.approve(market_contract.address, max_approval).transact({'from': deploy_address})
    eth.functions.approve(market_contract.address, max_approval).transact({'from': user_one})
    eth.functions.approve(market_contract.address, max_approval).transact({'from': user_two})
    eth.functions.approve(market_contract.address, max_approval).transact({'from': user_new})
    eth.functions.approve(market_contract.address, max_approval).transact({'from': user_buyer})
    blz.functions.approve(market_contract.address, max_approval).transact({'from': deploy_address})
    blz.functions.approve(market_contract.address, max_approval).transact({'from': user_one})
    blz.functions.approve(market_contract.address, max_approval).transact({'from': user_two})
    blz.functions.approve(market_contract.address, max_approval).transact({'from': user_new})
    blz.functions.approve(market_contract.address, max_approval).transact({'from': user_buyer})

    erc20 = {'cow': cow, 'eth': eth, 'blz': blz}

    return erc20

# set a fixture to return a RubiconMarket.sol instance
@pytest.fixture
def market_contract(eth_tester, w3):

    # set the test addresses
    deploy_address = eth_tester.get_accounts()[0]
    fee_address = eth_tester.get_accounts()[1]

    # load the contract abi and bytecode
    path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/RubiconMarket.json"
    with open(path, 'r') as f:
        contract_interface = json.load(f)
    f.close()
    abi = contract_interface["abi"]
    bytecode = contract_interface["bytecode"]

    # set up the contract instance 
    market_deployement = w3.eth.contract(abi=abi, bytecode=bytecode)

    # create a transaction to deploy the contract
    txn = market_deployement.constructor().transact({'from': deploy_address})

    # wait for the transaction to be mined and return an instance of the contract
    receipt = w3.eth.wait_for_transaction_receipt(txn, 180)

    # now initialize the contract with the test data
    market = w3.eth.contract(address=receipt.contractAddress, abi=abi)
    init_txn = market.functions.initialize(True, fee_address).transact()

    try:
        w3.eth.wait_for_transaction_receipt(init_txn, 180)
    except Exception as e:
        log.warning('market contract failed to initialize: ', e)

    return market

# set a fixture to return a RubiconRouter.sol instance
@pytest.fixture
def router_contract(market_contract, erc20s, eth_tester, w3):

    # set the test addresses
    deploy_address = eth_tester.get_accounts()[0]

    # load the contract abi and bytecode
    path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/RubiconRouter.json"
    with open(path, 'r') as f:
        contract_interface = json.load(f)
    f.close()
    abi = contract_interface["abi"]
    bytecode = contract_interface["bytecode"]

    # set up the contract instance 
    router_deployement = w3.eth.contract(abi=abi, bytecode=bytecode)

    # create a transaction to deploy the contract
    txn = router_deployement.constructor().transact({'from': deploy_address})

    # wait for the transaction to be mined and return an instance of the contract
    receipt = w3.eth.wait_for_transaction_receipt(txn, 180)

    # now initialie the contract with the test data
    router = w3.eth.contract(address=receipt.contractAddress, abi=abi)
    init_txn = router.functions.startErUp(market_contract.address, erc20s['cow'].address).transact()

    try:
        w3.eth.wait_for_transaction_receipt(init_txn, 180)
    except Exception as e:
        log.warning('router contract failed to initialize:', e)

    # return {'router' : router, 'market' : market_contract}
    return router

# set a fixture to return a MarketAidFactory.sol instance
@pytest.fixture
def factory_contract(market_contract, eth_tester, w3):

    # set the test addresses
    deploy_address = eth_tester.get_accounts()[0]
    
    # load the contract abi and bytecode
    path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/MarketAidFactory.json"
    with open(path, 'r') as f:
        contract_interface = json.load(f)
    f.close()
    abi = contract_interface["abi"]
    bytecode = contract_interface["bytecode"]

    # set up the contract instance
    factory_deployement = w3.eth.contract(abi=abi, bytecode=bytecode)

    # create a transaction to deploy the contract
    txn = factory_deployement.constructor().transact({'from': deploy_address})

    # wait for the transaction to be mined and return an instance of the contract
    receipt = w3.eth.wait_for_transaction_receipt(txn, 180)

    # now initialize the contract with the test data
    factory = w3.eth.contract(address=receipt.contractAddress, abi=abi)
    init_txn = factory.functions.initialize(market_contract.address).transact()

    try:
        w3.eth.wait_for_transaction_receipt(init_txn, 180)
    except Exception as e:
        log.warning('factory contract failed to initialize: ', e)
    
    return factory

# set a fixture to return a MarketAide.sol instance
@pytest.fixture
def aid_contract(factory_contract, eth_tester, w3):

    # set the test addresses
    strategist_address = eth_tester.get_accounts()[2]

    # load the contract abi and bytecode
    path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/MarketAid.json"
    with open(path, 'r') as f:
        contract_interface = json.load(f)
    f.close()
    abi = contract_interface["abi"]

    # create a marketaid instance from the factory contract
    create_txn = factory_contract.functions.createMarketAidInstance().transact({'from': strategist_address})

    # wait for the transaction to be mined 
    try: 
        w3.eth.wait_for_transaction_receipt(create_txn, 180)
    except Exception as e:
        print('failed to create a market aid instance: ', e)

    # get the address of the new market aid instance
    first_aid = factory_contract.functions.getUserMarketAids(strategist_address).call()[0]

    # TODO: see if you simply can return the receipt and then use the receipt to get the contract address
    # wait for the transaction to be mined and return an instance of the contract
    # receipt = w3.eth.wait_for_transaction_receipt(create_txn, 180)

    # now initialie the contract with the test data
    aide = w3.eth.contract(address=first_aid, abi=abi)
    
    return aide

# set a fixture that will initialize a Rubicon instance given the contracts above
@pytest.fixture 
def rubicon(market_contract, router_contract, factory_contract, add_account, w3):

    rubicon = Rubicon(w3, add_account['address'], add_account['key'], market_contract, router_contract, factory_contract)
    return rubicon

# set a fixture that will initailize a Rubicon instance given the contracts above, for the buyer account
@pytest.fixture
def rubicon_buyer(market_contract, router_contract, factory_contract, add_account_buyer, w3):

    rubicon = Rubicon(w3, add_account_buyer['address'], add_account_buyer['key'], market_contract, router_contract, factory_contract)
    return rubicon

# set a fixture that will populate a RubiconMarket.sol contract with orders
# TODO: for any future tests we should utilize this populated market instance 
# def offer(self, pay_amt, pay_gem, buy_amt, buy_gem, pos=0, nonce=None, gas=3000000, gas_price=None):
@pytest.fixture
def populated_market(market_contract, rubicon, erc20s):

    # populate the market contract 
    rubicon.market.offer(100000, erc20s['cow'].address, 100000, erc20s['eth'].address) # offer id 1
    rubicon.market.offer(200000, erc20s['cow'].address, 100000, erc20s['eth'].address) # offer id 2
    rubicon.market.offer(100000, erc20s['eth'].address, 600000, erc20s['cow'].address) # offer id 3
    rubicon.market.offer(100000, erc20s['eth'].address, 1000000, erc20s['cow'].address) # offer id 4
    rubicon.market.offer(100000, erc20s['eth'].address, 1100000, erc20s['cow'].address) # offer id 5
    
    rubicon.market.offer(100000, erc20s['blz'].address, 100000, erc20s['eth'].address) # offer id 6
    rubicon.market.offer(200000, erc20s['blz'].address, 100000, erc20s['eth'].address) # offer id 7

    return market_contract

class TestUser:

    def test_user(self, market_contract, erc20s, eth_tester, w3):

        # check the user balance of the erc20 tokens
        user_0 = eth_tester.get_accounts()[0]
        user_1 = eth_tester.get_accounts()[1]
        user_2 = eth_tester.get_accounts()[2]

        # check the user balance of the erc20 tokens
        assert erc20s['cow'].functions.balanceOf(user_0).call() == 220000000000000000000
        assert erc20s['cow'].functions.balanceOf(user_1).call() == 0
        assert erc20s['cow'].functions.balanceOf(user_2).call() == 0

        # check that all erc20 tokens have been deployed
        assert erc20s['cow'].address != None
        assert erc20s['eth'].address != None
        assert erc20s['blz'].address != None

        # TODO: there are some issues right now with how we are loading in the erc20 contracts
        assert erc20s['cow'].functions.decimals().call() == 18

        # check that the erc20 tokens have the correct properties
        assert erc20s['cow'].functions.symbol().call() == 'COW'
        assert erc20s['eth'].functions.symbol().call() == 'ETH'
        assert erc20s['blz'].functions.symbol().call() == 'BLZ'

        # check the allowance of the erc20 tokens
        max_approval = 2**256 - 1
        assert erc20s['cow'].functions.allowance(user_0, market_contract.address).call() == max_approval
        assert erc20s['cow'].functions.allowance(user_1, market_contract.address).call() == max_approval
        assert erc20s['cow'].functions.allowance(user_2, market_contract.address).call() == max_approval
        assert erc20s['eth'].functions.allowance(user_0, market_contract.address).call() == max_approval
        assert erc20s['eth'].functions.allowance(user_1, market_contract.address).call() == max_approval
        assert erc20s['eth'].functions.allowance(user_2, market_contract.address).call() == max_approval
        assert erc20s['blz'].functions.allowance(user_0, market_contract.address).call() == max_approval
        assert erc20s['blz'].functions.allowance(user_1, market_contract.address).call() == max_approval
        assert erc20s['blz'].functions.allowance(user_2, market_contract.address).call() == max_approval

class TestMarket(): 

    def test_market(self, rubicon, rubicon_buyer, erc20s, eth_tester, add_account, add_account_buyer):

        # test the market contract to see if it is initialized
        assert rubicon.market.contract.functions.initialized().call() == True

        # check that the fee is set to 20bps
        assert rubicon.market.get_fee_bps() == 20

        # check that the fee address is set to account index 1
        assert rubicon.market.contract.functions.getFeeTo().call() == eth_tester.get_accounts()[1]

        # check that the contract owner is the deployer
        assert rubicon.market.contract.functions.owner().call() == eth_tester.get_accounts()[0]

        # check that buy is enabled 
        assert rubicon.market.contract.functions.buyEnabled().call() == True

        # populate the market contract with some liquidity
        rubicon.market.offer(100000, erc20s['cow'].address, 100000, erc20s['eth'].address) # offer id 1
        rubicon.market.offer(200000, erc20s['cow'].address, 100000, erc20s['eth'].address) # offer id 2
        rubicon.market.offer(100000, erc20s['blz'].address, 100000, erc20s['eth'].address) # offer id 3
        rubicon.market.offer(200000, erc20s['blz'].address, 100000, erc20s['eth'].address) # offer id 4

        # check if the offers we inserted are sorted 
        assert rubicon.market.contract.functions.isOfferSorted(1).call() == True
        assert rubicon.market.contract.functions.isOfferSorted(2).call() == True
        assert rubicon.market.contract.functions.isOfferSorted(3).call() == True
        assert rubicon.market.contract.functions.isOfferSorted(4).call() == True

        # check that the offer count is correct
        assert rubicon.market.get_offer_count(erc20s['cow'].address, erc20s['eth'].address) == 2
        assert rubicon.market.get_offer_count(erc20s['blz'].address, erc20s['eth'].address) == 2 

        # check that the offers are in the market
        assert rubicon.market.get_offer(1) == [100000, erc20s['cow'].address, 100000, erc20s['eth'].address]
        assert rubicon.market.get_offer(2) == [200000, erc20s['cow'].address, 100000, erc20s['eth'].address]
        assert rubicon.market.get_offer(3) == [100000, erc20s['blz'].address, 100000, erc20s['eth'].address]
        assert rubicon.market.get_offer(4) == [200000, erc20s['blz'].address, 100000, erc20s['eth'].address]

        # check the best offer for each token pair
        assert rubicon.market.get_best_offer(erc20s['cow'].address, erc20s['eth'].address) == 2
        assert rubicon.market.get_best_offer(erc20s['blz'].address, erc20s['eth'].address) == 4

        # check the function get_better_offer 
        assert rubicon.market.get_better_offer(1) == 2
        assert rubicon.market.get_better_offer(3) == 4

        # check the function get_buy_amount(buy_gem, pay_gem, pay_amt)
        assert rubicon.market.get_buy_amount(erc20s['cow'].address, erc20s['eth'].address, 100000) == 200000
        assert rubicon.market.get_buy_amount(erc20s['blz'].address, erc20s['eth'].address, 100000) == 200000

        # check the function get_owner(id)
        assert rubicon.market.get_owner(1) == add_account['address']
        assert rubicon.market.get_owner(2) == add_account['address']
        assert rubicon.market.get_owner(3) == add_account['address']
        assert rubicon.market.get_owner(4) == add_account['address']

        # check the function get_pay_amount(pay_gem, buy_gem, buy_amt)
        assert rubicon.market.get_pay_amount(erc20s['eth'].address, erc20s['cow'].address, 100000) == 50000
        assert rubicon.market.get_pay_amount(erc20s['eth'].address, erc20s['blz'].address, 100000) == 50000

        # check the function get_worse_offer(id)
        assert rubicon.market.get_worse_offer(2) == 1
        assert rubicon.market.get_worse_offer(4) == 3

        # check function matching_enabled()
        assert rubicon.market.matching_enabled() == True

        # check the function buy(id, amount, nonce=None, gas=300000, gas_price=None) -> check the user's balance before and after the buy
        assert erc20s['cow'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) - 300000
        assert erc20s['blz'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) - 300000
        assert erc20s['eth'].functions.balanceOf(add_account['address']).call() == (100 * 10**18)
        assert erc20s['cow'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18)
        assert erc20s['blz'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18)
        assert erc20s['eth'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18)

        rubicon_buyer.market.buy(1, 100000)
        rubicon_buyer.market.buy(3, 100000)
        fee_one = int((100000 * .002) * 2)

        assert erc20s['cow'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) - 300000
        assert erc20s['blz'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) - 300000 
        assert erc20s['eth'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) + 200000
        assert erc20s['cow'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000
        assert erc20s['blz'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000
        assert erc20s['eth'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) - 200000 - fee_one

        # check the function buy_all_amount(buy_gem, buy_amt, pay_gem, max_fill_amount, nonce=None, gas=300000, gas_price=None) -> check the user's balance after the buy
        rubicon_buyer.market.buy_all_amount(erc20s['cow'].address, 100, erc20s['eth'].address, 100)
        rubicon_buyer.market.buy_all_amount(erc20s['blz'].address, 100, erc20s['eth'].address, 100)
        fee_two = int((100 * .002) * 2)

        assert erc20s['eth'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) + 200000 + 100
        assert erc20s['cow'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000 + 100
        assert erc20s['blz'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000 + 100
        assert erc20s['eth'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) - 200000 - 100 - fee_one - fee_two

        # check the function cancel(id, nonce=None, gas=300000, gas_price=None)
        rubicon.market.cancel(1)
        zero_address = "0x0000000000000000000000000000000000000000"
        rubicon.market.get_offer(1) == [0, zero_address, 0, zero_address]

        # check the function sell_all_amount(pay_gem, pay_amt, buy_gem, min_fill_amount, nonce=None, gas=300000, gas_price=None)
        rubicon_buyer.market.sell_all_amount(erc20s['eth'].address, 100, erc20s['cow'].address, 100)
        rubicon_buyer.market.sell_all_amount(erc20s['eth'].address, 100, erc20s['blz'].address, 100)
        fee_three = int((100 * .002) * 2)

        assert erc20s['eth'].functions.balanceOf(add_account['address']).call() == (100 * 10**18) + 200000 + 100 + 200
        assert erc20s['cow'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000 + 100 + 200
        assert erc20s['blz'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) + 100000 + 100 + 200
        assert erc20s['eth'].functions.balanceOf(add_account_buyer['address']).call() == (100 * 10**18) - 200000 - 100 - fee_one - fee_two - 200 - fee_three

        # see if there are unsorted offers 
        assert rubicon.market.contract.functions.getFirstUnsortedOffer().call() == 0

class TestRouter:
        
    # test that the contract was deployed
    def test_router_deployed(self, rubicon, router_contract, populated_market, erc20s, rubicon_buyer):

        # TODO: restructure this to be handled by the erc20 fixture and avoid recursive dependencies in the fixture
        # set the max approval for the erc20s
        max_approval = 2**256 - 1

        # approve the router contract to spend the user's tokens
        #cow.functions.approve(market_contract.address, max_approval).transact({'from': deploy_address})
        erc20s['cow'].functions.approve(router_contract.address, max_approval).transact({'from': rubicon_buyer.wallet})
        erc20s['blz'].functions.approve(router_contract.address, max_approval).transact({'from': rubicon_buyer.wallet})
        erc20s['eth'].functions.approve(router_contract.address, max_approval).transact({'from': rubicon_buyer.wallet})

        # check that the approval was set correctly
        assert erc20s['cow'].functions.allowance(rubicon_buyer.wallet, router_contract.address).call() == max_approval
        assert erc20s['blz'].functions.allowance(rubicon_buyer.wallet, router_contract.address).call() == max_approval
        assert erc20s['eth'].functions.allowance(rubicon_buyer.wallet, router_contract.address).call() == max_approval

        # check the contract address
        assert router_contract.address != None

        # check that the market address is set
        assert router_contract.functions.RubiconMarketAddress().call() == populated_market.address

        # check that the weth address is the same ass the erc20s['COW'] address
        assert router_contract.functions.wethAddress().call() == erc20s['cow'].address

        # check the function get_best_offer(asset, quote)
        assert rubicon.router.get_best_offer(erc20s['cow'].address, erc20s['eth'].address) == [2, 200000, erc20s['cow'].address, 100000, erc20s['eth'].address]
        assert rubicon.router.get_best_offer(erc20s['blz'].address, erc20s['eth'].address) == [7, 200000, erc20s['blz'].address, 100000, erc20s['eth'].address]

        # check the function get_book_from_pair(asset, quote, topNOrders)
        assert rubicon.router.get_book_from_pair(erc20s['cow'].address, erc20s['eth'].address, 2) == [[[200000, 100000, 2], [100000, 100000, 1]], [[100000, 600000, 3], [100000, 1000000, 4]], 2]
        assert rubicon.router.get_book_from_pair(erc20s['blz'].address, erc20s['eth'].address, 2) == [[[200000, 100000, 7], [100000, 100000, 6]], [[0, 0, 0], [0, 0, 0]], 2]
        assert rubicon_buyer.router.get_book_from_pair(erc20s['cow'].address, erc20s['eth'].address, 2) == [[[200000, 100000, 2], [100000, 100000, 1]], [[100000, 600000, 3], [100000, 1000000, 4]], 2]
        assert rubicon_buyer.router.get_book_from_pair(erc20s['blz'].address, erc20s['eth'].address, 2) == [[[200000, 100000, 7], [100000, 100000, 6]], [[0, 0, 0], [0, 0, 0]], 2]

        # check the function swap(pay_amt, buy_amt_min, route, expected_market_fee_bps=1, nonce=None, gas=300000, gas_price=None) -> check the user's balance before and after the swap
        assert erc20s['cow'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18) 
        assert erc20s['blz'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18)
        assert erc20s['eth'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18) 

        rubicon_buyer.router.swap(100, 100, [erc20s['eth'].address, erc20s['cow'].address], 20)
        rubicon_buyer.router.swap(100, 100, [erc20s['eth'].address, erc20s['blz'].address], 20)
        
        assert rubicon.router.get_book_from_pair(erc20s['cow'].address, erc20s['eth'].address, 2) == [[[199800, 99900, 2], [100000, 100000, 1]], [[100000, 600000, 3], [100000, 1000000, 4]], 2]
        assert rubicon.router.get_book_from_pair(erc20s['blz'].address, erc20s['eth'].address, 2) == [[[199800, 99900, 7], [100000, 100000, 6]], [[0, 0, 0], [0, 0, 0]], 2]
        assert erc20s['cow'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18) + 200
        assert erc20s['blz'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18) + 200
        assert erc20s['eth'].functions.balanceOf(rubicon_buyer.wallet).call() == (100 * 10**18) - 200
    

class TestFactory:

    # test that the contract was deployed
    def test_factory_deployed(self, rubicon, factory_contract, aid_contract, eth_tester):

        # check that the contract address is set 
        assert factory_contract.address != None

        # check that the admin is the deployer
        assert factory_contract.functions.admin().call() == eth_tester.get_accounts()[0]

        # check the function admin()
        assert rubicon.factory.admin() == eth_tester.get_accounts()[0]

        # check the function get_user_market_aids(user)
        assert rubicon.factory.get_user_market_aids(eth_tester.get_accounts()[2])[0] == aid_contract.address

        # check the function rubicon_market()
        assert rubicon.factory.rubicon_market() == rubicon.market.address

        # check the function create_market_aid_instance(nonce=None, gas=300000, gas_price=None)
        # TODO: it would be nice if we could get the address returned back from the function call to create the aid contract
        rubicon.factory.create_market_aid_instance()
        assert rubicon.factory.get_user_market_aids(rubicon.wallet) != []
  

class TestAide:

    # test that the contract was deployed
    def test_aide_deployed(self, rubicon, erc20s, eth_tester):    

        # create the market aid contract from the factory
        rubicon.factory.create_market_aid_instance()

        # check the wallet address has a market aid contract associated with it
        aid_address = rubicon.factory.get_user_market_aids(rubicon.wallet)[0]
        assert aid_address != []

        # connect to the market aid contract
        aid = rubicon.aid(aid_address)

        # check that the contract address is set
        assert aid.address == aid_address

        # check the function admin()
        assert aid.admin() == rubicon.wallet

        # check the function approved_strategists()
        assert aid.approved_strategists(rubicon.wallet) == True

        # check the function is_approved_strategist(strategist)
        assert aid.is_approved_strategist(rubicon.wallet) == True

        # check the function rubicon_market_address()
        assert aid.rubicon_market_address() == rubicon.market.address

        ### Populate the market aid contract with some data ###

        # send some tokens to the market aid contract
        amount = 10 * 10**18
        erc20s['cow'].functions.transfer(aid.address, amount).transact({'from': rubicon.wallet})
        erc20s['blz'].functions.transfer(aid.address, amount).transact({'from': rubicon.wallet})

        # check the function get_strategist_total_liquidity(asset, quote, strategist) -> there should be no outstanding liquidity at this point
        assert aid.get_strategist_total_liquidity(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [amount, amount, False]     

        # check the function admin_pull_all_funds(erc20s, nonce=None, gas=300000, gas_price=None) -> pull all the funds from the market aid contract
        aid.admin_pull_all_funds([erc20s['cow'].address, erc20s['blz'].address])
        assert aid.get_strategist_total_liquidity(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [0, 0, False]     

        erc20s['cow'].functions.transfer(aid.address, amount).transact({'from': rubicon.wallet})
        erc20s['blz'].functions.transfer(aid.address, amount).transact({'from': rubicon.wallet})
        assert aid.get_strategist_total_liquidity(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [amount, amount, False]   

        # check the function batch_market_making_trades(token_pairs, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=300000, gas_price=None)
        # aid.batch_market_making_trades([weth.address, usdc.address], [the amount of the asset you will sell], [the amount of the quote you will receive], [the amount of quote you will pay], [the amount of asset you would receive])
        aid.batch_market_making_trades([erc20s['cow'].address, erc20s['blz'].address], [100], [10000], [100], [100])

        # check the function get_outstanding_strategist_trades(asset, quote, strategist)
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [1]

        # check the function get_strategist_trade(trade_id)
        # TODO: improve this test to check the timestamp value returned by the function
        assert aid.get_strategist_trade(1)[:-1] == [1, 100, erc20s['cow'].address, 2, 100, erc20s['blz'].address, rubicon.wallet]

        # check the function admin_max_approve_target(target, token, nonce=None, gas=300000, gas_price=None)
        target = eth_tester.get_accounts()[1]
        aid.admin_max_approve_target(target, erc20s['cow'].address)
        assert erc20s['cow'].functions.allowance(aid.address, target).call() == 2**256 - 1

        # check the function approve_strategist(strategist, nonce=None, gas=300000, gas_price=None)
        aid.approve_strategist(eth_tester.get_accounts()[1])
        assert aid.approved_strategists(eth_tester.get_accounts()[1]) == True

        # check the function batch_requote_all_offers(token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=300000, gas_price=None)
        aid.batch_requote_all_offers([erc20s['cow'].address, erc20s['blz'].address], [100], [10000], [100], [100])
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [2]

        # check the function batch_requote_offers(ids, token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=300000, gas_price=None)
        aid.batch_requote_offers([2], [erc20s['cow'].address, erc20s['blz'].address], [100], [10000], [100], [100])
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [3]

        # check the function place_market_making_trades(token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator, nonce=None, gas=300000, gas_price=None)
        aid.place_market_making_trades([erc20s['cow'].address, erc20s['blz'].address], 100, 10000, 100, 100)
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [3, 4]

        # check the function remove_strategist(strategist, nonce=None, gas=300000, gas_price=None)
        aid.remove_strategist(eth_tester.get_accounts()[1])
        assert aid.approved_strategists(eth_tester.get_accounts()[1]) == False

        # check the function requote(id, token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator, nonce=None, gas=300000, gas_price=None)
        aid.requote(4, [erc20s['cow'].address, erc20s['blz'].address], 101, 10000, 100, 100)
        assert rubicon.market.get_offer(9) == [101, erc20s['cow'].address, 10000, erc20s['blz'].address]
        assert rubicon.market.get_offer(10) == [100, erc20s['blz'].address, 100, erc20s['cow'].address]

        # check the function scrub_strategist_trade(id, nonce=None, gas=300000, gas_price=None)
        aid.scrub_strategist_trade(5)
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == [3]

        # check the function scrub_strategist_trades(ids, nonce=None, gas=300000, gas_price=None)
        aid.scrub_strategist_trades([3])
        assert aid.get_outstanding_strategist_trades(erc20s['cow'].address, erc20s['blz'].address, rubicon.wallet) == []

        aid.place_market_making_trades([erc20s['cow'].address, erc20s['blz'].address], 100, 10000, 100, 100)
        # check the function admin_rebalance_funds(asset_to_sell, amount_to_sell, asset_to_target, nonce=None, gas=300000, gas_price=None)
        assert rubicon.market.get_offer(12) == [100, erc20s['blz'].address, 100, erc20s['cow'].address]
        aid.admin_rebalance_funds(erc20s['cow'].address, 100, erc20s['blz'].address)
        assert rubicon.market.get_offer(12) == [0, '0x0000000000000000000000000000000000000000', 0, '0x0000000000000000000000000000000000000000']

class TestRubi: 

    def test_rubi_functionality(self, rubicon, erc20s, populated_market): 

        # get the number of orders in the book for the given token pair and return the book at that depth
        offer_count = rubicon.market.get_offer_count(erc20s['cow'].address, erc20s['eth'].address)
        book = rubicon.router.get_book_from_pair(erc20s['cow'].address, erc20s['eth'].address, offer_count)
        assert book == [[[200000, 100000, 2], [100000, 100000, 1]], [[100000, 600000, 3], [100000, 1000000, 4]], 2]
        assert book[0] == [[200000, 100000, 2], [100000, 100000, 1]]

        # now check the other side 
        offer_count = rubicon.market.get_offer_count(erc20s['eth'].address, erc20s['cow'].address)
        book = rubicon.router.get_book_from_pair(erc20s['eth'].address, erc20s['cow'].address, offer_count)
        assert book == [[[100000, 600000, 3], [100000, 1000000, 4], [100000, 1100000, 5]], [[200000, 100000, 2], [100000, 100000, 1], [0, 0, 0]], 3]
        assert book[0] == [[100000, 600000, 3], [100000, 1000000, 4], [100000, 1100000, 5]]

        # check the book functionality of the class
        assert rubicon.get_offers(erc20s['cow'].address, erc20s['eth'].address) == [[[200000, 100000, 2], [100000, 100000, 1]], [[100000, 600000, 3], [100000, 1000000, 4]], 2]
        assert rubicon.get_offers(erc20s['eth'].address, erc20s['cow'].address) == [[[100000, 600000, 3], [100000, 1000000, 4], [100000, 1100000, 5]], [[200000, 100000, 2], [100000, 100000, 1], [0, 0, 0]], 3]

        book_one = rubicon.get_book(erc20s['cow'].address, erc20s['eth'].address)
        assert book_one.token0 == erc20s['cow'].address
        assert book_one.token1 == erc20s['eth'].address
        assert book_one.orders == [2, 1]
        assert book_one.details == {2 : [200000, 100000], 1 : [100000, 100000]}

        book_two = rubicon.get_book(erc20s['eth'].address, erc20s['cow'].address)
        assert book_two.token0 == erc20s['eth'].address
        assert book_two.token1 == erc20s['cow'].address
        assert book_two.orders == [3, 4, 5]
        assert book_two.details == {3 : [100000, 600000], 4 : [100000, 1000000], 5 : [100000, 1100000]}
