import logging as log
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum
from threading import Lock, Semaphore, Thread
from typing import Callable, Optional

from rubi import Transaction, TransactionReceipt, Client
from web3.types import Nonce


class TransactionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class PendingTransaction:
    def __init__(
        self,
        transaction: Transaction,
        transaction_receipt_future: Future[TransactionReceipt]
    ):
        self.transaction = transaction
        self.transaction_receipt_future = transaction_receipt_future

    @property
    def nonce(self) -> int:
        return self.transaction.nonce


class TransactionResult:
    def __init__(
        self,
        status: TransactionStatus,
        transaction: Transaction,
        transaction_receipt: Optional[TransactionReceipt]
    ):
        self.status = status
        self.transaction = transaction
        self.transaction_receipt = transaction_receipt

    @property
    def nonce(self) -> int:
        return self.transaction.nonce


class ThreadedTransactionManager:
    def __init__(self, client: Client):
        self.running = False

        self.client = client
        self.transaction_result_queue = client.message_queue

        self.nonce = client.get_nonce()
        self.nonce_lock = Lock()

        self.transaction_notifier = Semaphore(value=0)
        self.pending_transactions: deque[PendingTransaction] = deque()

        self.executor = ThreadPoolExecutor()

    def start(self):
        self.running = True

        thread = Thread(target=self._handle_transaction_receipts, daemon=True)
        thread.start()

    def stop(self):
        self.running = False

        self.executor.shutdown()

    def place_transaction(
        self,
        transaction_executor: Callable[[Transaction], TransactionReceipt],
        transaction: Transaction
    ) -> Nonce:
        with self.nonce_lock:
            transaction.nonce = self.nonce

            transaction_receipt_future: Future[TransactionReceipt] = self.executor.submit(
                transaction_executor,
                transaction
            )

            self.pending_transactions.append(
                PendingTransaction(
                    transaction=transaction,
                    transaction_receipt_future=transaction_receipt_future
                )
            )
            self.transaction_notifier.release()

            self.nonce += 1

            return transaction.nonce

    def _handle_transaction_receipts(self):
        while self.running:
            self.transaction_notifier.acquire()

            first_pending_transaction: PendingTransaction = self.pending_transactions.popleft()
            try:
                transaction_receipt: TransactionReceipt = first_pending_transaction.transaction_receipt_future.result()

                self.transaction_result_queue.put(TransactionResult(
                    status=TransactionStatus.FAILURE if transaction_receipt.status == 0 else TransactionStatus.SUCCESS,
                    transaction=first_pending_transaction.transaction,
                    transaction_receipt=transaction_receipt
                ))

            except Exception as e:
                with self.nonce_lock:
                    log.error(e)

                    # Due to transaction nonces this means that this transaction and all pending transactions after this
                    # will have failed, so we may as well stop caring about them.
                    self.nonce = first_pending_transaction.nonce

                    # if the error has the message nonce too low then we have messed up significantly somehow, and we
                    # should just reset.
                    if hasattr(e, 'message'):
                        if e.message == "nonce too low":
                            self.nonce = self.client.get_nonce()

                    self.transaction_result_queue.put(TransactionResult(
                        status=TransactionStatus.FAILURE,
                        transaction=first_pending_transaction.transaction,
                        transaction_receipt=None
                    ))

                    for pending_transaction in self.pending_transactions:
                        self.transaction_result_queue.put(TransactionResult(
                            status=TransactionStatus.FAILURE,
                            transaction=pending_transaction.transaction,
                            transaction_receipt=None
                        ))
                    self.pending_transactions.clear()
