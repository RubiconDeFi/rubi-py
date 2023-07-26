import logging as log
import time
from enum import Enum
from threading import Thread
from time import sleep
from typing import Optional, Callable, Type, Dict, Any, List

from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.contract.contract import (
    ContractFunction,
)  # TODO: figure out why jupyter notebook is complaining about this
from web3.logs import DISCARD
from web3.types import ABI, Nonce, TxReceipt, EventData

from rubi.contracts.contract_types import BaseEvent, TransactionReceipt


class ContractType(Enum):
    """Enum to distinguish the type of contract instantiated

    Should only be used internally
    """

    RUBICON_MARKET = "RUBICON_MARKET"
    RUBICON_ROUTER = "RUBICON_ROUTER"
    ERC20 = "ERC20"


class BaseContract:
    """Base class representation of a contract which defines the structure of a contract and provides several helpful
    methods that can be used by subclass contracts that extend this contract.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    :param contract_type: the type of contract
    :type contract_type: ContractType
    :param wallet: a wallet address of the signer (optional, default is None)
    :type wallet: Optional[ChecksumAddress]
    :param key: the private key of the signer (optional, default is None)
    :type key: Optional[str]
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
        contract_type: ContractType,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ):
        """constructor method"""
        if (wallet is None) != (key is None):
            raise Exception(
                "both a wallet and a key are required to sign transactions. provide both or omit both"
            )

        self.contract = contract
        self.address = contract.address
        self.contract_type = contract_type
        self.w3 = w3
        self.chain_id = self.w3.eth.chain_id

        # Signing permissions
        self.signing_permissions = wallet is not None and key is not None

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
        contract_type: ContractType,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ) -> "BaseContract":
        """Create a BaseContract instance from the contract address and ABI.

        :param w3: The Web3 instance.
        :type w3: Web3
        :param address: The address of the contract.
        :type address: ChecksumAddress
        :param contract_abi: The ABI of the contract.
        :type contract_abi: ABI
        :param contract_type: The type of contract we are instantiating.
        :type contract_type: ContractType
        :param wallet: The wallet address to use for interacting with the contract (optional, default is None).
        :type wallet: Optional[ChecksumAddress]
        :param key: The private key of the wallet (optional, default is None).
        :type key: Optional[str]
        :return: An instance of BaseContract.
        :rtype: BaseContract
        """

        contract = w3.eth.contract(address=address, abi=contract_abi)

        return cls(
            w3=w3,
            contract=contract,
            contract_type=contract_type,
            wallet=wallet,
            key=key,
        )

    ######################################################################
    # useful methods
    ######################################################################

    def get_transaction_receipt(self, transaction_hash: str) -> TransactionReceipt:
        """Get a transaction receipt for the give transaction_hash.

        :param transaction_hash: The transaction hash.
        :type transaction_hash: str
        :return: A TransactionReceipt for the transaction hash.
        :rtype: TransactionReceipt
        """
        return self._wait_for_transaction_receipt(transaction_hash=transaction_hash)

    ######################################################################
    # event listeners
    ######################################################################

    # TODO: revisit poll time. Right now it is set to block production time of optimism according to:
    #  https://community.optimism.io/docs/protocol/2-rollup-protocol/#block-storage
    #  however arbitrum produces blocks faster (every 0.25 secs) according to:
    #  https://arbiscan.io/chart/blocktime so we may be prudent to account for different chains
    #  however the better way to do this is probably a websocket connection to the node
    # TODO: investigate using a more generic filter so that you don't need to poll for each event as this could
    #  spam the node that is being connected to
    def start_event_poller(
        self,
        pair_name: str,
        event_type: Type[BaseEvent],
        argument_filters: Optional[Dict[str, Any]] = None,
        event_handler: Optional[Callable] = None,
        poll_time: int = 2,
    ) -> None:
        """Start a thread which runs an event poller for a specific event type.

        :param pair_name: The name of the pair we are monitoring events of.
        :type pair_name: str
        :param event_type: The type of event to poll for.
        :type event_type: Type[BaseEvent]
        :param argument_filters: Optional filters that the node will filter events on (optional, default is None).
        :type argument_filters: Optional[Dict[str, Any]]
        :param event_handler: Optional event handler function. Defaults to using the events default handler.
        :type event_handler: Optional[Callable]
        :param poll_time: The time interval between each poll in seconds. Defaults to 2 seconds.
        :type poll_time: int
        """

        event_filter = event_type.create_event_filter(
            contract=self.contract, argument_filters=argument_filters
        )
        handler = (
            event_handler if event_handler is not None else event_type.default_handler
        )

        thread = Thread(
            target=self._start_default_event_poller,
            args=(
                pair_name,
                event_type,
                self.contract,
                argument_filters,
                event_filter,
                handler,
                poll_time,
            ),
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _start_default_event_poller(
        pair_name: str,
        event_type: Type[BaseEvent],
        contract: Contract,
        argument_filters: Optional[Dict[str, Any]],
        event_filter: LogFilter,
        event_handler: Callable,
        poll_time: int,
    ) -> None:
        """Start the default event poller loop. This thread will stop if the pair is removed from the client.

        :param pair_name: The name of the event pair.
        :type pair_name: str
        :param event_type: The type of the event.
        :type event_type: Type[BaseEvent]
        :param event_filter: The event filter to retrieve new entries.
        :type event_filter: LogFilter
        :param event_handler: The event handler function.
        :type event_handler: Callable
        :param poll_time: The time interval between poll iterations in seconds.
        :type poll_time: int
        """
        polling = True

        while polling:
            try:
                for event_data in event_filter.get_new_entries():
                    event_handler(pair_name, event_type, event_data)
            except Exception as e:
                log.error(e)

                # The filter has been deleted by the node and needs to be recreated
                if "filter not found" in str(e):
                    event_filter = event_type.create_event_filter(
                        contract=contract, argument_filters=argument_filters
                    )
                    log.info(f"event filter for: {event_type} has been recreated")

                # TODO: this is a hack to detect if a PairDoesNotExistException is raised and polling should stop.
                #  Currently an additional except PairDoesNotExistException as e: cannot be added as this causes a
                #  circular import. Think about restructuring the directories to avoid this (e.g one root level types
                #  directory).
                if "add pair to the client" in str(e):
                    polling = False

            sleep(poll_time)

    ######################################################################
    # helper methods
    ######################################################################

    def _default_transaction_handler(
        self,
        instantiated_contract_function: ContractFunction,
        gas: Optional[int],
        nonce: Optional[int],
        max_fee_per_gas: Optional[int],
        max_priority_fee_per_gas: Optional[int],
    ) -> TransactionReceipt:
        """Default transaction handler for executing transactions against this contract. This function will build, sign
        and execute a transaction with reasonable defaults (mostly from the web3py library).

        Note: if a nonce is not passed then this function will query to the wallet to get the nonce and also wait for
        the transaction receipt before returning.

        :param instantiated_contract_function: The instantiated contract function to call.
        :type instantiated_contract_function: ContractFunction
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param nonce: Optional nonce value for the transaction (optional, default is None).
        :type nonce: Optional[int]
        :param max_fee_per_gas: Optional maximum fee per gas for the transaction (optional, default is None).
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: Optional maximum priority fee per gas for the transaction.
            (optional, default is None).
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        if not self.signing_permissions:
            raise Exception(
                f"cannot write transaction without signing rights. "
                f"re-instantiate {self.__class__} with a wallet and private key"
            )

        base_txn = self._transaction_params(
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        txn = instantiated_contract_function.build_transaction(transaction=base_txn)

        signed_txn = self.w3.eth.account.sign_transaction(
            transaction_dict=txn, private_key=self.key
        )

        log.debug(f"SENDING TRANSACTION, nonce: {nonce}, timestamp: {time.time_ns()}")
        self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return self._wait_for_transaction_receipt(transaction=signed_txn)

    def _transaction_params(
        self,
        nonce: Optional[Nonce],
        gas: Optional[int],
        max_fee_per_gas: Optional[int],
        max_priority_fee_per_gas: Optional[int],
    ) -> Dict:
        """Build transaction parameters Dict for a transaction. If a key is associated with a None value after building
        the Dict then this key will be removed before returning the dict.

        :param nonce: Optional nonce value for the transaction (optional, default is None).
        :type nonce: Optional[Nonce]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: Optional maximum fee per gas for the transaction (optional, default is None).
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: Optional maximum priority fee per gas for the transaction.
            (optional, default is None).
        :type max_priority_fee_per_gas: Optional[int]
        :return: The transaction parameters dictionary.
        :rtype: Dict
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        transaction = {
            "chainId": self.chain_id,
            "gas": gas,
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "nonce": nonce,
            "from": self.wallet,
        }

        return {key: value for key, value in transaction.items() if value is not None}

    def _wait_for_transaction_receipt(
        self,
        transaction: Optional[SignedTransaction] = None,
        transaction_hash: Optional[str] = None,
    ) -> TransactionReceipt:
        """Wait for the transaction receipt and check if the transaction was successful.

        :param transaction: The signed transaction object.
        :type transaction: SignedTransaction
        """

        if transaction:
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(transaction.hash)
        elif transaction_hash:
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(
                HexBytes(transaction_hash)
            )
        else:
            raise Exception("Provide either a transaction or a transaction_hash")

        raw_events = self._process_receipt_logs_into_raw_events(receipt=tx_receipt)

        result = TransactionReceipt.from_tx_receipt(
            tx_receipt=tx_receipt, raw_events=raw_events
        )

        log.debug(f"RECEIVED RESULT, timestamp: {time.time_ns()}")

        return result

    def _process_receipt_logs_into_raw_events(
        self, receipt: TxReceipt
    ) -> List[BaseEvent | EventData]:
        """
        Processes the logs of a given transaction receipt and returns a list of events associated with the transaction.

        :param receipt:
        :type receipt: TxReceipt
        :return: The list of events associated with the given transaction receipt
        :rtype: List[BaseEvent]
        """
        match self.contract_type:
            case ContractType.RUBICON_MARKET:
                event_names = ["emitTake", "emitOffer", "emitCancel"]
            case ContractType.RUBICON_ROUTER:
                event_names = ["emitSwap"]
            case ContractType.ERC20:
                event_names = ["Approval", "Transfer"]
            case _:
                raise Exception("Unexpected ContractType")

        raw_events = []
        for event_name in event_names:
            transaction_events_data = self.contract.events[
                event_name
            ]().process_receipt(receipt, DISCARD)

            for event_data in transaction_events_data:
                if self.contract_type == ContractType.ERC20:
                    raw_events.append(event_data)

                raw_events.append(
                    BaseEvent.builder(
                        name=event_name,
                        block_number=event_data["blockNumber"],
                        **event_data["args"],
                    )
                )

        return raw_events
