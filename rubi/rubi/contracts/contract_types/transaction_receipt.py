from _decimal import Decimal
from enum import Enum
from typing import Optional, List, Any, Union

from eth_typing import BlockNumber, ChecksumAddress
from hexbytes import HexBytes
from web3.types import Wei, TxReceipt, EventData

from rubi.contracts.contract_types import BaseEvent


class TransactionStatus(Enum):
    """Enum representing the status of a transaction."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

    def __eq__(self, other):
        return self.name is other.name and self.value == other.value

    @classmethod
    def from_int(cls, status: int) -> "TransactionStatus":
        """
        Transform the TxReceipt status into an Enum
        """
        if status == 0:
            return cls.FAILURE
        else:
            return cls.SUCCESS


class TransactionReceipt:
    """Transaction receipt object"""

    def __init__(
        self,
        block_number: BlockNumber,
        contract_address: Optional[ChecksumAddress],
        effective_gas_price: Wei,
        gas_used: int,
        from_address: ChecksumAddress,
        to_address: ChecksumAddress,
        status: int,
        transaction_hash: HexBytes,
        transaction_index: int,
        l1_fee: Optional[int] = None,
        l1_gas_price: Optional[int] = None,
        l1_gas_used: Optional[int] = None,
        l1_fee_scalar: Optional[Decimal] = None,
        raw_events: Optional[List[BaseEvent]] = None,
    ):
        # Block number
        self.block_number = block_number

        # Addresses
        self.from_address = from_address
        self.to_address = to_address
        self.created_contract_at_address = contract_address

        # Transaction cost
        self.gas_used = gas_used
        self.transaction_cost_in_eth = self._calc_gas_cost_in_eth(
            effective_gas_price=effective_gas_price,
            gas_used=gas_used,
            l1_gas_price=l1_gas_price,
            l1_gas_used=l1_gas_used,
            l1_fee_scalar=l1_fee_scalar,
        )

        # Transaction details
        self.transaction_status = TransactionStatus.from_int(status=status)
        self.transaction_hash = transaction_hash.hex()
        self.position_in_block = transaction_index

        # Transaction Events
        self.raw_events = raw_events
        self.events = None

    @classmethod
    def from_tx_receipt(
        cls, tx_receipt: TxReceipt, raw_events: List[Union[BaseEvent, EventData]]
    ) -> "TransactionReceipt":
        """Initialize a TransactionReceipt

        :param tx_receipt: The transaction receipt Dict received from the node.
        :type tx_receipt: TxReceipt
        :param raw_events: The raw events decoded from the logs
        :type raw_events: List[Union[BaseEvent, EventData]]
        :return: A TransactionReceipt object
        :rtype: TransactionReceipt
        """
        return cls(
            block_number=tx_receipt["blockNumber"],
            contract_address=tx_receipt["contractAddress"],
            effective_gas_price=tx_receipt["effectiveGasPrice"],
            gas_used=tx_receipt["gasUsed"],
            from_address=tx_receipt["from"],
            to_address=tx_receipt["to"],
            status=tx_receipt["status"],
            transaction_hash=tx_receipt["transactionHash"],
            transaction_index=tx_receipt["transactionIndex"],
            l1_fee=None
            if tx_receipt.get("l1Fee") is None
            else int(tx_receipt.get("l1Fee"), 16),
            l1_gas_price=None
            if tx_receipt.get("l1GasPrice") is None
            else int(tx_receipt.get("l1GasPrice"), 16),
            l1_gas_used=None
            if tx_receipt.get("l1GasUsed") is None
            else int(tx_receipt.get("l1GasUsed"), 16),
            l1_fee_scalar=None
            if tx_receipt.get("l1FeeScalar") is None
            else Decimal(tx_receipt.get("l1FeeScalar")),
            raw_events=raw_events,
        )

    # TODO: Any is used to avoid circular dependencies, look at a restructure. These are OrderEvents | ApprovalEvents |
    #  TransferEvents.
    def set_events(self, events: List[Any]):
        """Set the events on the Transaction Receipt. Used on the client to set human-readable events"""
        self.events = events

    @staticmethod
    def _calc_gas_cost_in_eth(
        gas_used: int,
        effective_gas_price: Wei,
        l1_gas_price: Optional[int] = None,
        l1_gas_used: Optional[int] = None,
        l1_fee_scalar: Optional[Decimal] = None,
    ) -> Optional[Decimal]:
        """Calculate the cost of the transaction in eth.

        :param gas_used: The amount of gas used by the transaction.
        :type gas_used: int
        :param effective_gas_price: The effective L2 gas price of the transaction.
        :type effective_gas_price: Wei
        :param l1_gas_price: The L1 gas price.
        :type l1_gas_price: Optional[int]
        :param l1_gas_used: The L1 gas used.
        :type l1_gas_used: Optional[int]
        :param l1_fee_scalar: The L1 fee scalar.
        :type l1_fee_scalar: Optional[int]
        :return:
        """
        if not (l1_gas_price and l1_gas_used and l1_fee_scalar):
            return None

        return (
            Decimal(effective_gas_price * gas_used)
            + (l1_gas_price * l1_gas_used * l1_fee_scalar)
        ) / Decimal(10**18)

    def __repr__(self):
        items = (
            "{}={!r}".format(k, self.__dict__[k])
            for k in self.__dict__
            if k != "raw_events"
        )
        return "{}({})".format(type(self).__name__, ", ".join(items))
