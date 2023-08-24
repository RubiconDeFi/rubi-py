import json
import logging
import os
from threading import Thread
from time import sleep
from typing import Optional, Callable, Type, Dict, Any, Union

from eth_typing import ChecksumAddress
from eth_utils import encode_hex, function_abi_to_4byte_selector
from web3 import Web3
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.contract.contract import (
    ContractFunction,
)  # TODO: figure out why jupyter notebook is complaining about this
from web3.exceptions import ContractCustomError
from web3.types import ABI, Nonce, TxParams

from rubi.contracts.contract_types import BaseEvent

logger = logging.getLogger(__name__)


class BaseContract:
    """Base class representation of a contract which defines the structure of a contract and provides several helpful
    methods that can be used by subclass contracts that extend this contract.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
    ):
        """constructor method"""
        self.contract = contract
        self.address = contract.address
        self.w3 = w3
        self.chain_id = self.w3.eth.chain_id

        self.error_decoder: Dict[str, str] = {}
        for item in self.contract.abi:
            if item["type"] == "error":
                error_hex_code = str(encode_hex(function_abi_to_4byte_selector(item)))

                self.error_decoder[error_hex_code] = item["name"]

    @classmethod
    def from_address_and_abi(
        cls,
        w3: Web3,
        address: ChecksumAddress,
        contract_abi: ABI,
    ) -> "BaseContract":
        """Create a BaseContract instance from the contract address and ABI.

        :param w3: The Web3 instance.
        :type w3: Web3
        :param address: The address of the contract.
        :type address: ChecksumAddress
        :param contract_abi: The ABI of the contract.
        :type contract_abi: ABI
        :return: An instance of BaseContract.
        :rtype: BaseContract
        """

        contract = w3.eth.contract(
            address=w3.to_checksum_address(address), abi=contract_abi
        )

        return cls(
            w3=w3,
            contract=contract,
        )

    @classmethod
    def from_address(
        cls,
        w3: Web3,
        address: Union[ChecksumAddress, str],
    ) -> "BaseContract":
        """Create a BaseContract instance from an address.

        :param w3: Web3 instance.
        :type w3: Web3
        :param address: The address of the contract.
        :type address: Union[ChecksumAddress, str]
        :return: A BaseContract instance based on the address.
        :rtype: BaseContract
        """

        match str(cls.__name__):
            case "RubiconMarket":
                name = "market"
            case "RubiconRouter":
                name = "router"
            case "ERC20":
                name = "ERC20"
            case _:
                raise Exception("from_address called on unexpected class")

        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/abis/{name}.json"

            with open(path) as f:
                abi = json.load(f)

        except FileNotFoundError:
            raise Exception(
                f"{name}.json abi not found. This file should be in the network_config/abis/ folder"
            )

        return cls.from_address_and_abi(
            w3=w3,
            address=address,
            contract_abi=abi,
        )

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
                logger.error(e)

                # The filter has been deleted by the node and needs to be recreated
                if "filter not found" in str(e):
                    event_filter = event_type.create_event_filter(
                        contract=contract, argument_filters=argument_filters
                    )
                    logger.info(f"event filter for: {event_type} has been recreated")

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

    def _construct_transaction(
        self,
        instantiated_contract_function: ContractFunction,
        wallet: ChecksumAddress,
        nonce: Optional[int],
        gas: Optional[int],
        max_fee_per_gas: Optional[int],
        max_priority_fee_per_gas: Optional[int],
    ) -> Optional[TxParams]:
        """Default transaction constructor for building transactions for this contract. This function will build
         a transaction with reasonable defaults (mostly from the web3py library).

        Note: if a nonce is not passed then this function will query to the wallet to get the nonce.

        :param instantiated_contract_function: The instantiated contract function to call.
        :type instantiated_contract_function: ContractFunction
        :param nonce: Optional nonce value for the transaction (optional, default is None).
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: Optional maximum fee per gas for the transaction (optional, default is None).
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: Optional maximum priority fee per gas for the transaction.
            (optional, default is None).
        :type max_priority_fee_per_gas: Optional[int]
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """
        base_transaction = self._transaction_params(
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            wallet=wallet,
        )

        try:
            built_transaction = instantiated_contract_function.build_transaction(
                transaction=base_transaction
            )
        except ContractCustomError as e:
            decoded_message = self.error_decoder[e.message]

            logger.error(f"Error constructing arbitrage transaction: {decoded_message}")
            return None
        except Exception as e:
            logger.error(f"Error constructing arbitrage transaction: {e}")
            return None

        return built_transaction

    def _transaction_params(
        self,
        wallet: ChecksumAddress,
        nonce: Optional[Nonce],
        gas: Optional[int],
        max_fee_per_gas: Optional[int],
        max_priority_fee_per_gas: Optional[int],
    ) -> Dict:
        """Build transaction parameters Dict for a transaction. If a key is associated with a None value after building
        the Dict then this key will be removed before returning the dict.

        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
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
            nonce = self.w3.eth.get_transaction_count(wallet)

        transaction = {
            "chainId": self.chain_id,
            "gas": gas,
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "nonce": nonce,
            "from": wallet,
        }

        return {key: value for key, value in transaction.items() if value is not None}
