import os
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
def rubicon(market_contract, router_contract, aid_contract, add_account, w3):

    rubicon = Rubicon(w3, add_account['address'], add_account['key'], market_contract, router_contract, aid_contract)
    return rubicon

# set a fixture that will initailize a Rubicon instance given the contracts above, for the buyer account
@pytest.fixture
def rubicon_buyer(market_contract, router_contract, aid_contract, add_account_buyer, w3):

    rubicon = Rubicon(w3, add_account_buyer['address'], add_account_buyer['key'], market_contract, router_contract, aid_contract)
    return rubicon

# set a fixture that will populate a RubiconMarket.sol contract with orders
#@pytest.fixture
#def populated_market(market_contract, rubicon, erc20s, eth_tester, w3):

    # populate the market contract 
    #rubicon.market.make(erc20s['cow'].address, erc20s['eth'].address, 1000, 1000)
    #rubicon.market.make(erc20s['cow'].address, erc20s['eth'].address, 2000, 1000)
    #rubicon.market.make(erc20s['blz'].address, erc20s['eth'].address, 1000, 1000)
    #rubicon.market.make(erc20s['blz'].address, erc20s['eth'].address, 2000, 1000)

    #return market_contract

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
    def test_router_deployed(self, router_contract, market_contract, erc20s):

        # check the contract address
        assert router_contract.address != None

        # check that the market address is set
        assert router_contract.functions.RubiconMarketAddress().call() == market_contract.address

        # check that the weth address is the same ass the erc20s['COW'] address
        assert router_contract.functions.wethAddress().call() == erc20s['cow'].address

    # test the contract read functions
    # def test_router_reads(self, router_contract):

    # test the contract write functions
    # def test_router_writes(self, router_contract):

    # test the contract events
    # def test_router_events(self, router_contract):

class TestFactory:

    # test that the contract was deployed
    def test_factory_deployed(self, factory_contract, eth_tester):

        # check that the contract address is set 
        assert factory_contract.address != None

        # check that the admin is the deployer
        assert factory_contract.functions.admin().call() == eth_tester.get_accounts()[0]

class TestAide:

    # test that the contract was deployed
    def test_aide_deployed(self, aid_contract, eth_tester):    

        # check that the contract address is set
        assert aid_contract.address != None

        # check to see that the correct admin was set
        assert aid_contract.functions.admin().call() == eth_tester.get_accounts()[2]

    # test the contract read functions in the rubicon package
    #def test_aid_reads(self, aid_contract, eth_tester):
        
        # check that the admin is properly set


    # test the contract write functions
    # def test_aide_writes(self, aid_contract):

    # test the contract events
    # def test_aide_events(self, aid_contract):