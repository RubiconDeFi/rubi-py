from typing import Optional

from eth_typing import BlockNumber, ChecksumAddress
from hexbytes import HexBytes
from web3.types import Wei, TxReceipt


# TODO: a TxReceipt contains logs which can be decoded into events that were emitted by calling the contract function.
#  It may be useful in future to add the logs field to the TransactionReceipt object and decode them into objects.
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
        transaction_index: int
    ):
        self.block_number = block_number
        self.contract_address = contract_address
        self.effective_gas_price = effective_gas_price
        self.gas_used = gas_used
        self.from_address = from_address
        self.to_address = to_address
        self.status = status
        self.transaction_hash = transaction_hash
        self.transaction_index = transaction_index

    @classmethod
    def from_tx_receipt(cls, tx_receipt: TxReceipt) -> "TransactionReceipt":
        return cls(
            block_number=tx_receipt["blockNumber"],
            contract_address=tx_receipt["contractAddress"],
            effective_gas_price=tx_receipt["effectiveGasPrice"],
            gas_used=tx_receipt["gasUsed"],
            from_address=tx_receipt["from"],
            to_address=tx_receipt["to"],
            status=tx_receipt["status"],
            transaction_hash=tx_receipt["transactionHash"],
            transaction_index=tx_receipt["transactionIndex"]
        )

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
