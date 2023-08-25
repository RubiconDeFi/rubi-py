from hexbytes import HexBytes
from web3.types import TxParams, TxReceipt

from rubi import Network


def execute_transaction(
    network: Network,
    transaction: TxParams,
    key: str,
) -> TxReceipt:
    signed_transaction = network.w3.eth.account.sign_transaction(
        transaction_dict=transaction, private_key=key
    )

    transaction_hash = network.w3.eth.send_raw_transaction(
        signed_transaction.rawTransaction
    )

    return network.w3.eth.wait_for_transaction_receipt(transaction_hash, timeout=5)
