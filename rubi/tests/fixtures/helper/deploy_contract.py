import json
import logging as log
import os
from typing import Tuple, Any, Dict

from eth_typing import ChecksumAddress
from web3 import Web3, EthereumTesterProvider
from web3.contract import Contract
from web3.types import TxReceipt


def deploy_contract(
    path: str,
    web3: Web3,
    deploy_address: ChecksumAddress,
    # These args are passed directly to the contract constructor
    *args,
) -> Tuple[ChecksumAddress, Any]:
    with open(path, "r") as f:
        contract_interface = json.load(f)

    abi = contract_interface["abi"]
    bytecode = contract_interface["bytecode"]

    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    deployment_transaction = contract.constructor(*args).transact(
        {"from": deploy_address}
    )

    transaction_receipt: TxReceipt = web3.eth.wait_for_transaction_receipt(
        deployment_transaction, 180
    )

    return transaction_receipt["contractAddress"], abi


def deploy_erc20(
    ethereum_tester_provider: EthereumTesterProvider,
    web3: Web3,
    rubicon_market: Contract,
    account_1: Dict,
    account_2: Dict,
    # constructor arguments
    *args,
) -> Contract:
    deploy_address = ethereum_tester_provider.ethereum_tester.get_accounts()[0]
    account_1_address = account_1["address"]
    account_2_address = account_2["address"]

    path = (
        f"{os.path.dirname(os.path.realpath(__file__))}/../../"
        + f"test_network_config/contract_interfaces/ERC20MockDecimals.json"
    )
    contract_address, abi = deploy_contract(
        path,
        web3,
        deploy_address,
        # constructor arguments
        *args,
    )

    # instantiate contracts
    try:
        contract = web3.eth.contract(address=contract_address, abi=abi)

        contract.functions.transfer(account_1_address, 100 * 10**18).transact(
            {"from": deploy_address}
        )
        contract.functions.transfer(account_2_address, 100 * 10**18).transact(
            {"from": deploy_address}
        )

        # set the max approval for the erc20s
        max_approval = 2**256 - 1

        # approve the rubicon market contract to spend tokens
        contract.functions.approve(rubicon_market.address, max_approval).transact(
            {"from": account_1_address}
        )
        contract.functions.approve(rubicon_market.address, max_approval).transact(
            {"from": account_2_address}
        )

        return contract
    except Exception as e:
        log.warning("error instantiating erc20 contract: ", e)
