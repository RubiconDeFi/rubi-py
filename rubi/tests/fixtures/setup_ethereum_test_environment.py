import logging as log
import os
from typing import Dict

from eth_tester import PyEVMBackend
from eth_utils import to_wei
from pytest import fixture
from web3 import EthereumTesterProvider, Web3
from web3.contract import Contract

from rubi import Network, Client, ERC20, RubiconMarket
from tests.fixtures.helper.deploy_contract import deploy_contract
from tests.fixtures.helper.deploy_contract import deploy_erc20


######################################################################
# setup EthereumTesterProvider, Web3 instance
######################################################################

@fixture
def ethereum_tester_provider() -> EthereumTesterProvider:
    test_provider = EthereumTesterProvider()
    test_provider.ethereum_tester.backend = PyEVMBackend.from_mnemonic(
        "test test test test test test test test test test test junk",
        genesis_state_overrides={"balance": to_wei(1000000, "ether")}
    )

    return test_provider


@fixture
def web3(ethereum_tester_provider: EthereumTesterProvider) -> Web3:
    return Web3(ethereum_tester_provider)


######################################################################
# setup EthereumTesterProvider with accounts, coins and contracts
######################################################################

@fixture
def account_1(ethereum_tester_provider: EthereumTesterProvider, web3: Web3) -> Dict:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    account_1 = ethereum_tester_provider.ethereum_tester.add_account(
        "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d"
    )

    # fund account
    web3.eth.send_transaction({'from': deploy_address, 'to': account_1, 'value': 100 * 10 ** 18})

    return {"address": account_1, "key": "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d"}


@fixture
def account_2(ethereum_tester_provider: EthereumTesterProvider, web3: Web3) -> Dict:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    account_2 = ethereum_tester_provider.ethereum_tester.add_account(
        "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420"
    )

    # fund account
    web3.eth.send_transaction({'from': deploy_address, 'to': account_2, 'value': 100 * 10 ** 18})

    return {"address": account_2, "key": "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420"}


@fixture
def rubicon_market(ethereum_tester_provider: EthereumTesterProvider, web3: Web3) -> Contract:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    fee_address = ethereum_tester_provider.ethereum_tester.get_accounts()[1]

    # deploy rubicon market
    path = f"{os.path.dirname(os.path.abspath(__file__))}/../test_network_config/contract_interfaces/RubiconMarket.json"
    market_contract_address, abi = deploy_contract(
        path=path,
        web3=web3,
        deploy_address=deploy_address
    )

    # initialize rubicon market
    rubicon_market = web3.eth.contract(address=market_contract_address, abi=abi)
    initialization_transaction = rubicon_market.functions.initialize(fee_address).transact()

    try:
        web3.eth.wait_for_transaction_receipt(initialization_transaction, 180)
    except Exception as e:
        log.warning('market contract failed to initialize: ', e)

    return rubicon_market


@fixture
def cow(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    account_1: Dict,
    account_2: Dict
) -> Contract:
    supply = 420 * 10 ** 18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market,
        account_1,
        account_2,
        # constructor arguments
        "defi cowboy", "COW", supply, 18
    )


@fixture
def eth(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    account_1: Dict,
    account_2: Dict
) -> Contract:
    supply = 420 * 10 ** 18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market,
        account_1,
        account_2,
        # constructor arguments
        "ether", "ETH", supply, 18
    )


@fixture
def blz(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    account_1: Dict,
    account_2: Dict
) -> Contract:
    supply = 420 * 10 ** 18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market,
        account_1,
        account_2,
        # constructor arguments
        "blaze it", "BLZ", supply, 18
    )


@fixture
def rubicon_router(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    cow: Contract
) -> Contract:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    fee_address = ethereum_tester_provider.ethereum_tester.get_accounts()[1]

    # deploy rubicon router
    path = f"{os.path.dirname(os.path.abspath(__file__))}/../test_network_config/contract_interfaces/RubiconRouter.json"
    router_contract_address, abi = deploy_contract(
        path=path,
        web3=web3,
        deploy_address=deploy_address
    )

    # initialize rubicon router
    rubicon_router = web3.eth.contract(address=router_contract_address, abi=abi)
    initialization_transaction = rubicon_router.functions.startErUp(rubicon_market.address, cow.address).transact()

    try:
        web3.eth.wait_for_transaction_receipt(initialization_transaction, 180)
    except Exception as e:
        log.warning('market contract failed to initialize: ', e)

    return rubicon_router


######################################################################
# setup Network with the deployed coins
######################################################################

@fixture
def test_network(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    rubicon_router: Contract,
    cow: Contract,
    eth: Contract,
    blz: Contract
) -> Network:
    base_path = f"{os.path.dirname(os.path.abspath(__file__))}/../test_network_config"

    rubicon = {
        "market": {
            "address": rubicon_market.address
        },
        "router": {
            "address": rubicon_router.address
        }

    }

    token_addresses = {
        "COW": cow.address,
        "ETH": eth.address,
        "BLZ": blz.address
    }

    return Network(
        path=base_path,
        w3=web3,
        name='IshanChain',
        chain_id=69420,
        currency='ISH',
        rpc_url='https://ishan.io/rpc',
        explorer_url='https://ishanexplorer.io',
        rubicon=rubicon,
        token_addresses=token_addresses
    )


######################################################################
# setup rubi contracts for account 2
######################################################################

@fixture
def rubicon_market_for_account_2(web3: Web3, rubicon_market: Contract, account_2: Dict) -> RubiconMarket:
    return RubiconMarket(
        w3=web3,
        contract=rubicon_market,
        wallet=account_2["address"],
        key=account_2["key"]
    )


@fixture
def add_account_2_offers_to_cow_eth_market(rubicon_market_for_account_2: RubiconMarket, cow: Contract, eth: Contract):
    # COW/ETH bid
    rubicon_market_for_account_2.offer(
        pay_amt=1 * 10 ** 18,
        pay_gem=eth.address,
        buy_amt=1 * 10 ** 18,
        buy_gem=cow.address
    )

    # COW/ETH ask
    rubicon_market_for_account_2.offer(
        pay_amt=1 * 10 ** 18,
        pay_gem=cow.address,
        buy_amt=2 * 10 ** 18,
        buy_gem=eth.address
    )


######################################################################
# setup Client and rubi erc20 contracts
######################################################################

@fixture
def test_client(test_network: Network) -> Client:
    return Client(
        network=test_network
    )


@fixture
def test_client_for_account_1(test_network: Network, account_1: Dict) -> Client:
    client = Client(
        network=test_network,
        wallet=account_1["address"],
        key=account_1["key"]
    )

    pair_name = "COW/ETH"

    client.add_pair(pair_name=pair_name)

    return client


@fixture
def cow_erc20_for_account_1(test_network: Network, account_1: Dict) -> ERC20:
    return ERC20.from_network(
        name="COW",
        network=test_network,
        wallet=account_1["address"],
        key=account_1["key"]
    )


@fixture
def eth_erc20_for_account_1(test_network: Network, account_1: Dict) -> ERC20:
    return ERC20.from_network(
        name="ETH",
        network=test_network,
        wallet=account_1["address"],
        key=account_1["key"]
    )