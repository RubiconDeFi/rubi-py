# pytest fixtures for the rubi-py client test

# imports
import os
import json
import pytest
import logging as log
from _decimal import Decimal
from multiprocessing import Queue
from threading import Thread
from time import sleep
from typing import Union, List, Optional, Dict, Type, Any, Callable

from eth_typing import ChecksumAddress
from web3.types import EventData

from eth_utils import to_wei
from eth_tester import PyEVMBackend
from web3 import EthereumTesterProvider, Web3

from rubi.contracts import (
    RubiconMarket,
    RubiconRouter,
    ERC20,
)
from rubi.network import (
    Network,
)
from rubi.types import (
    OrderSide,
    NewMarketOrder,
    NewLimitOrder,
    Pair,
    OrderBook,
    PairDoesNotExistException,
    BaseEvent,
    OrderEvent,
    Transaction,
    BaseNewOrder,
    NewCancelOrder,
    UpdateLimitOrder
)

from rubi import Client

from dotenv import load_dotenv

################################################################
#    Fixtures from old test - might be useful still
################################################################

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

################################################################
#    New fixtures based on v2
################################################################

@pytest.fixture
def loadenv():
    load_dotenv(".env")
    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("DEV_WALLET")
    key = os.getenv("DEV_KEY")

    return {"http_node_url": http_node_url, "wallet": wallet, "key": key}

@pytest.fixture
def createQueue():
    queue = Queue()
    return queue

class TestClient:
    
    def test_init(self, loadenv, createQueue):
        # this test requires me to set up the Network
        client = Client()
        # Test if the wallet attribute is set correctly when a valid wallet address is provided.
        # Test if the key attribute is set correctly when a key is provided.
        # Test if the market attribute is initialized with the correct values.
        # Test if the router attribute is initialized with the correct values.
        # Test if the _pairs attribute is initialized as an empty dictionary.
        # Test if the message_queue attribute is set to None when no queue is provided.
    
    def test_from_http_node_url(self, loadenv, createQueue):
        queue = createQueue()
        
        client = Client.from_http_node_url(
            http_node_url=loadenv["http_node_url"],
            custom_token_addresses_file="rubi/tests/custom_token_addresses.yaml",
            wallet=loadenv["wallet"],
            key=loadenv["key"],
            message_queue= queue
        )
        # Test if a Client instance is created successfully.
        # Test if the network attribute of the created instance is set correctly.
        # Test if the message_queue attribute of the created instance is set to None when no queue is provided.
        # Test if the wallet attribute of the created instance is set correctly when a valid wallet address is provided.
        # Test if the wallet attribute of the created instance is set to None when no wallet address is provided.
        # Test if the key attribute of the created instance is set correctly when a key is provided.


