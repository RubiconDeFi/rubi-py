import os
import json
import pytest
import logging as log
from web3 import EthereumTesterProvider, Web3

from rubi import Rubicon

# the main structural choice here is the utilization of rubi's ability to pass in a contract object to initiliaze the class when the network (in this case EthereumTesterProvider) does not have data in the rolodex
# so, we are going to deploy and initialize the contracts in a fixture that will pass back the Rubicon object along with the contract objects in a dictionary

# set a fixture to return a tester provider intance 
@pytest.fixture
def tester_provider():
    return EthereumTesterProvider()

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

    new = eth_tester.add_account('0x42000000000000000000000000000000000000000000000000000defi0c0wb0y')
    return {'address' : new, 'key': '0x42000000000000000000000000000000000000000000000000000defi0c0wb0y'}

# set a fixture to initialize a dictionary of erc20 contracts
@pytest.fixture
def erc20s(eth_tester, w3):

    # set the test addresses
    deploy_address = eth_tester.get_accounts()[0]

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
def rubicon(market_contract, router_contract, aid_contract, add_account, eth_tester, w3):

    rubicon = Rubicon(w3, add_account['address'], add_account['key'], market_contract, router_contract, aid_contract)
    return rubicon

# set a fixture that will populate a RubiconMarket.sol contract with orders
#@pytest.fixture
#def populate_market(market_contract, erc20s, eth_tester, w3):

class TestUser:

    def test_user(self, erc20s, eth_tester, w3):

        # check the user balance of the erc20 tokens
        user_address = eth_tester.get_accounts()[1]

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

class TestMarket:
        
    # test that the contract was deployed
    def test_market_deployed(self, market_contract, eth_tester):
        
        # check the contract address
        assert market_contract.address != None

        # check that the contract is initialized
        assert market_contract.functions.initialized().call() == True

        # check that the fee address is set
        assert market_contract.functions.getFeeTo().call() == eth_tester.get_accounts()[1]

        # check that the contract owner is the deployer
        # assert market_contract.functions.owner().call() == eth_tester.get_accounts()[0]
    
    # test the contract read functions
    # in order to test the read functions, we need to write to the contract first
    # def test_market_reads(self, market_contract):

    # test the contract write functions
    # def test_market_writes(self, market_contract):

    # test the contract events
    # def test_market_events(self, market_contract):

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