import logging as log
from threading import Thread
from time import sleep
from typing import Optional, Callable, TypeVar, Type, Dict, Any

from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from web3 import Web3
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.types import ABI, Nonce

from rubi.contracts_v2.helper.event_types import BaseEvent

T = TypeVar("T")


class BaseContract:
    """this class is the base representation of a contract

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    :param wallet: a wallet address of the signer (optional)
    :type wallet: Optional[ChecksumAddress]
    :param key: the private key of the signer (optional)
    :type key: Optional[str]
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ):
        """constructor method"""
        if (wallet is None) != (key is None):
            raise Exception("both a wallet and a key are required to sign transactions. provide both or omit both")

        self.contract = contract
        self.address = contract.address
        self.w3 = w3
        self.chain_id = self.w3.eth.chain_id

        # Signing permissions
        self.signing_permissions = (wallet is not None and key is not None)

        if self.signing_permissions:
            log.info(f"instantiated {self.__class__} with signing rights")

            # Force typing as my editors inspection is throwing a tantrum
            self.wallet = wallet  # type: ChecksumAddress
            self.key = key  # type: str

    @classmethod
    def from_address_and_abi(
        cls,
        w3: Web3,
        address: ChecksumAddress,
        contract_abi: ABI,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ) -> "BaseContract":
        contract = w3.eth.contract(address=address, abi=contract_abi)

        return cls(w3=w3, contract=contract, wallet=wallet, key=key)

    ######################################################################
    # event listeners
    ######################################################################

    # TODO: revisit poll time. Right now it is set to block production time of optimism according to:
    # https://community.optimism.io/docs/protocol/2-rollup-protocol/#block-storage
    # however arbitrum produces blocks faster (every 0.25 secs) according to:
    # https://arbiscan.io/chart/blocktime so we may be prudent to account for different chains
    # however the better way to do this is probably a websocket connection to the node
    def start_event_poller(
        self,
        pair_name: str,
        event_type: Type[BaseEvent],
        argument_filters: Optional[Dict[str, Any]] = None,
        event_handler: Optional[Callable] = None,
        poll_time: int = 2
    ) -> None:
        # TODO: investigate using a block filter so that you don't need to poll for each event
        # however parsing the event also needs to be updated then
        # filter_params: dict = {"fromBlock": "latest", "address": self.contract.address}
        # block_filter = self.w3.eth.filter(filter_params)

        event_filter = event_type.create_event_filter(contract=self.contract, argument_filters=argument_filters)
        handler = event_handler if event_handler is not None else event_type.default_handler

        thread = Thread(
            target=self._start_default_event_poller,
            args=(pair_name, event_type, event_filter, handler, poll_time),
            daemon=True
        )
        thread.start()

    ######################################################################
    # helper methods
    ######################################################################

    def _default_transaction_handler(
        self,
        instantiated_contract_function: ContractFunction,
        gas: int,
        nonce: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> str:
        if not self.signing_permissions:
            raise Exception(f"cannot write transaction without signing rights. "
                            f"re-instantiate {self.__class__} with a wallet and private key")

        base_txn = self._transaction_params(
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

        txn = instantiated_contract_function.build_transaction(
            transaction=base_txn
        )

        signed_txn = self.w3.eth.account.sign_transaction(
            transaction_dict=txn,
            private_key=self.key
        )
        result = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before
        # continuing
        if nonce is None:
            self._wait_for_transaction_receipt(transaction=signed_txn)

        return result.hex()

    def _transaction_params(
        self,
        nonce: Optional[Nonce],
        gas: int,
        max_fee_per_gas: Optional[int],
        max_priority_fee_per_gas: Optional[int]
    ) -> dict:
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        transaction = {
            'chainId': self.chain_id,
            'gas': gas,
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'nonce': nonce,
        }

        return {key: value for key, value in transaction.items() if value is not None}

    def _wait_for_transaction_receipt(self, transaction: SignedTransaction) -> None:
        if self.w3.eth.wait_for_transaction_receipt(transaction.hash)['status'] == 0:
            raise Exception(f"transaction {transaction.hash.hex()} failed")

    @staticmethod
    def _start_default_event_poller(
        pair_name: str,
        event_type: Type[BaseEvent],
        event_filter: LogFilter,
        event_handler: Callable,
        poll_time: int
    ) -> None:
        while True:
            try:
                for event_data in event_filter.get_new_entries():
                    event_handler(pair_name, event_type, event_data)
            except Exception as e:
                log.error(e)
            sleep(poll_time)
