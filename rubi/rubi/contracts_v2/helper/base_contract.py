import logging as log
from time import sleep
from typing import Optional, Any, Callable, TypeVar

from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from web3 import Web3
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.types import ABI, Nonce

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
            log.info(f"instantiated with signing rights")

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
    def _start_default_listener(event_filter: LogFilter, event_handler: Callable, poll_time: int = 10) -> None:
        while True:
            for event in event_filter.get_new_entries():
                event_handler(event)
            sleep(poll_time)
