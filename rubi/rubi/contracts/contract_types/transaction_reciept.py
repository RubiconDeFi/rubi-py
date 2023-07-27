from _decimal import Decimal
from enum import Enum
from typing import Optional, List, Any

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
        self.block_number = block_number
        self.contract_address = contract_address
        self.effective_gas_price = effective_gas_price
        self.gas_used = gas_used
        self.from_address = from_address
        self.to_address = to_address
        self.status = status
        # Do this so that introducing TransactionStatus is not a breaking change
        self.transaction_status = TransactionStatus.from_int(status=status)
        self.transaction_hash = transaction_hash
        self.transaction_index = transaction_index
        self.l1_fee = l1_fee
        self.l1_gas_price = l1_gas_price
        self.l1_gas_used = l1_gas_used
        self.l1_fee_scalar = l1_fee_scalar
        self.raw_events = raw_events
        self.events = None

    @classmethod
    def from_tx_receipt(
        cls, tx_receipt: TxReceipt, raw_events: List[BaseEvent | EventData]
    ) -> "TransactionReceipt":
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

    # TODO: Any is used to avoid circular dependencies, look at a restructure. These are OrderEvents.
    def set_events(self, events: List[Any]):
        self.events = events

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
