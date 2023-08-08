import logging as log
from typing import List

from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.logs import DISCARD
from web3.types import EventData, TxReceipt, TxParams

from rubi.contracts.contract_types import TransactionReceipt, BaseEvent

logger = log.getLogger(__name__)


class TransactionHandler:
    def __init__(self, w3: Web3, contracts: List[Contract]):
        self.w3 = w3
        self.contracts = contracts

    def add_contract(self, contract: Contract):
        self.contracts.append(contract)

    def execute_transaction(
        self,
        transaction: TxParams,
        key: str,
    ) -> TransactionReceipt:
        if "pair_names" in transaction:
            del transaction["pair_names"]

        signed_transaction = self.w3.eth.account.sign_transaction(
            transaction_dict=transaction, private_key=key
        )

        try:
            self.w3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        except Exception as e:
            logger.error(f"Error trying to send transaction: {e}")
            raise e

        return self._wait_for_transaction_receipt(
            transaction_hash=signed_transaction.hash
        )

    def get_transaction_receipt(self, transaction_hash: str) -> TransactionReceipt:
        """Get a transaction receipt for the give transaction_hash.

        :param transaction_hash: The transaction hash.
        :type transaction_hash: str
        :return: A TransactionReceipt for the transaction hash.
        :rtype: TransactionReceipt
        """
        return self._wait_for_transaction_receipt(transaction_hash=transaction_hash)

    ######################################################################
    # helper methods
    ######################################################################

    def _wait_for_transaction_receipt(
        self,
        transaction_hash: str,
    ) -> TransactionReceipt:
        """Get the transaction receipt for the given transaction hash.

        :param transaction_hash: The transaction hash of the transaction.
        :type transaction_hash: str
        :return: The transaction receipt of the given transaction hash
        :rtype: TransactionReceipt
        """

        tx_receipt = self.w3.eth.wait_for_transaction_receipt(
            HexBytes(transaction_hash)
        )

        raw_events = self._process_receipt_logs_into_raw_events(receipt=tx_receipt)

        result = TransactionReceipt.from_tx_receipt(
            tx_receipt=tx_receipt, raw_events=raw_events
        )

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

        raw_events = []
        for contract in self.contracts:
            event_names = list(
                map(lambda event: event.event_name, contract.events)  # noqa
            )

            if len(event_names) == 0:
                continue

            for event_name in event_names:
                # TODO: Figure out why this breaks things for some reason
                if event_name == "LogNote":
                    continue

                transaction_events_data = contract.events[event_name]().process_receipt(
                    receipt, DISCARD
                )

                for event_data in transaction_events_data:
                    event = BaseEvent.from_raw(
                        name=event_name,
                        address=event_data["address"],
                        block_number=event_data["blockNumber"],
                        **event_data["args"],
                    )

                    if event:
                        raw_events.append(event)

        return raw_events
