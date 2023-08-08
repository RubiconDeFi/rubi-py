import logging as log
import os
from multiprocessing import Queue
from typing import Dict

from eth_tester import PyEVMBackend
from eth_utils import to_wei
from pytest import fixture
from web3 import EthereumTesterProvider, Web3
from web3.contract import Contract

from fixtures.helper import execute_transaction
from rubi import Network, Client, RubiconMarket
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
        genesis_state_overrides={"balance": to_wei(1000000, "ether")},
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
    web3.eth.send_transaction(
        {"from": deploy_address, "to": account_1, "value": 100 * 10**18}
    )

    return {
        "wallet": account_1,
        "key": "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d241d",
    }


@fixture
def account_2(ethereum_tester_provider: EthereumTesterProvider, web3: Web3) -> Dict:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    account_2 = ethereum_tester_provider.ethereum_tester.add_account(
        "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420"
    )

    # fund account
    web3.eth.send_transaction(
        {"from": deploy_address, "to": account_2, "value": 100 * 10**18}
    )

    return {
        "wallet": account_2,
        "key": "0x58d23b55bc9cdce1f18c2500f40ff4ab7245df9a89505e9b1fa4851f623d2420",
    }


@fixture
def rubicon_market_contract(
    ethereum_tester_provider: EthereumTesterProvider, web3: Web3
) -> Contract:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    fee_address = ethereum_tester_provider.ethereum_tester.get_accounts()[1]

    # deploy rubicon market
    path = f"{os.path.dirname(os.path.abspath(__file__))}/../test_network_config/contract_interfaces/RubiconMarket.json"
    market_contract_address, abi = deploy_contract(
        path=path, web3=web3, deploy_address=deploy_address
    )

    # initialize rubicon market
    rubicon_market = web3.eth.contract(address=market_contract_address, abi=abi)
    initialization_transaction = rubicon_market.functions.initialize(
        fee_address
    ).transact()

    try:
        web3.eth.wait_for_transaction_receipt(initialization_transaction, 180)
    except Exception as e:
        log.warning("market contract failed to initialize: ", e)

    # set maker fee to 1 bip
    add_maker_fee_transaction = rubicon_market.functions.setMakerFee(10).transact()

    try:
        web3.eth.wait_for_transaction_receipt(add_maker_fee_transaction, 180)
    except Exception as e:
        log.warning("market contract failed to set maker fee: ", e)

    return rubicon_market


@fixture
def cow(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market_contract,
    account_1: Dict,
    account_2: Dict,
) -> Contract:
    supply = 420 * 10**18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market_contract,
        account_1,
        account_2,
        # constructor arguments
        "defi cowboy",
        "COW",
        supply,
        18,
    )


@fixture
def eth(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market_contract,
    account_1: Dict,
    account_2: Dict,
) -> Contract:
    supply = 420 * 10**18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market_contract,
        account_1,
        account_2,
        # constructor arguments
        "ether",
        "ETH",
        supply,
        18,
    )


@fixture
def blz(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market_contract,
    account_1: Dict,
    account_2: Dict,
) -> Contract:
    supply = 420 * 10**18

    return deploy_erc20(
        ethereum_tester_provider,
        web3,
        rubicon_market_contract,
        account_1,
        account_2,
        # constructor arguments
        "blaze it",
        "BLZ",
        supply,
        18,
    )


@fixture
def rubicon_router(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market_contract,
    cow: Contract,
) -> Contract:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]

    # deploy rubicon router
    path = f"{os.path.dirname(os.path.abspath(__file__))}/../test_network_config/contract_interfaces/RubiconRouter.json"
    router_contract_address, abi = deploy_contract(
        path=path, web3=web3, deploy_address=deploy_address
    )

    # initialize rubicon router
    rubicon_router = web3.eth.contract(address=router_contract_address, abi=abi)
    initialization_transaction = rubicon_router.functions.startErUp(
        rubicon_market_contract.address, cow.address
    ).transact()

    try:
        web3.eth.wait_for_transaction_receipt(initialization_transaction, 180)
    except Exception as e:
        log.warning("market contract failed to initialize: ", e)

    return rubicon_router


######################################################################
# setup Network with the deployed coins
######################################################################


@fixture
def test_network(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market_contract,
    rubicon_router: Contract,
    cow: Contract,
    eth: Contract,
    blz: Contract,
) -> Network:
    rubicon = {
        "market": rubicon_market_contract.address,
        "router": rubicon_router.address,
    }

    token_addresses = {"COW": cow.address, "ETH": eth.address, "BLZ": blz.address}

    return Network(
        w3=web3,
        name="IshanChain",
        chain_id=69420,
        currency="ISH",
        rpc_url="https://ishan.io/rpc",
        explorer_url="https://ishanexplorer.io",
        # TODO: update once prod has been synced
        market_data_url="https://api.rubicon.finance/subgraphs/name/RubiconV2_Optimism_Mainnet_Dev",
        market_data_fallback_url="https://api.rubicon.finance/subgraphs/name/RubiconV2_Optimism_Mainnet_Dev",
        rubicon=rubicon,
        token_addresses=token_addresses,
    )


######################################################################
# setup rubi contracts for account 2
######################################################################


@fixture
def rubicon_market(web3: Web3, rubicon_market_contract) -> RubiconMarket:
    return RubiconMarket(
        w3=web3,
        contract=rubicon_market_contract,
    )


@fixture
def add_account_2_offers_to_cow_eth_market(
    test_network: Network,
    rubicon_market: RubiconMarket,
    cow: Contract,
    eth: Contract,
    account_2: Dict,
):
    # COW/ETH bids
    offer_1 = rubicon_market.offer(
        pay_amt=1 * 10**18,
        pay_gem=eth.address,
        buy_amt=1 * 10**18,
        buy_gem=cow.address,
        wallet=account_2["wallet"],
    )

    execute_transaction(network=test_network, transaction=offer_1, key=account_2["key"])

    # COW/ETH asks
    offer_2 = rubicon_market.offer(
        pay_amt=1 * 10**18,
        pay_gem=cow.address,
        buy_amt=2 * 10**18,
        buy_gem=eth.address,
        wallet=account_2["wallet"],
    )

    execute_transaction(network=test_network, transaction=offer_2, key=account_2["key"])

    offer_3 = rubicon_market.offer(
        pay_amt=1 * 10**18,
        pay_gem=cow.address,
        buy_amt=3 * 10**18,
        buy_gem=eth.address,
        wallet=account_2["wallet"],
    )

    execute_transaction(network=test_network, transaction=offer_3, key=account_2["key"])


######################################################################
# setup Client and rubi erc20 contracts
######################################################################


@fixture
def test_client(test_network: Network) -> Client:
    return Client(network=test_network)


@fixture
def test_client_for_account_1(test_network: Network, account_1: Dict) -> Client:
    message_queue = Queue()

    client = Client(
        network=test_network,
        message_queue=message_queue,
        wallet=account_1["wallet"],
        key=account_1["key"],
    )

    return client


@fixture
def test_client_for_account_2(test_network: Network, account_2: Dict) -> Client:
    message_queue = Queue()

    client = Client(
        network=test_network,
        message_queue=message_queue,
        wallet=account_2["wallet"],
        key=account_2["key"],
    )

    return client
