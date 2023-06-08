from abc import ABC, abstractmethod
from multiprocessing import Queue
from typing import Union, Callable

from rubi import OrderBook, OrderEvent, Transaction, TransactionReceipt
from web3.types import Nonce

from event_trading_framework.transaction_manager import TransactionResult, ThreadedTransactionManager
from event_trading_framework.types.event_queues import FreshEventQueue, FIFOEventQueue


class BaseEventTradingFramework(ABC):
    def __init__(self, event_queue: Queue, nonce: Nonce):
        self.event_queue = event_queue

        self.running = False

        # Initialize transaction manager
        self.transaction_manager = ThreadedTransactionManager(
            queue=event_queue,
            current_nonce=nonce
        )

        # Initialize message queues
        self.orderbook_event_queue = FreshEventQueue(message_handler=self.on_orderbook)
        self.order_event_queue = FIFOEventQueue(message_handler=self.on_order)
        self.transaction_result_queue = FIFOEventQueue(message_handler=self.on_transaction_result)

    @abstractmethod
    def on_startup(self):
        raise NotImplementedError()

    def start(self):
        # run on_startup method for strategy implementation
        self.on_startup()

        # start transaction manager
        self.transaction_manager.start()

        # start message queue handlers
        self.orderbook_event_queue.start()
        self.order_event_queue.start()
        self.transaction_result_queue.start()

        self.running = True
        while self.running:
            message: Union[OrderBook, OrderEvent, TransactionResult] = self.event_queue.get(block=True)

            if isinstance(message, OrderBook):
                self.orderbook_event_queue.add_message(message=message)
            elif isinstance(message, OrderEvent):
                self.order_event_queue.add_message(message=message)
            elif isinstance(message, TransactionResult):
                self.transaction_result_queue.add_message(message=message)
            else:
                raise Exception("Unexpected message fetched from queue")

    def stop(self):
        self.running = False

        self.orderbook_event_queue.stop()
        self.order_event_queue.stop()
        self.transaction_result_queue.stop()

        self.transaction_manager.stop()

    @abstractmethod
    def on_orderbook(self, orderbook: OrderBook):
        raise NotImplementedError()

    @abstractmethod
    def on_order(self, order: OrderEvent):
        raise NotImplementedError()

    @abstractmethod
    def on_transaction_result(self, result: TransactionResult):
        raise NotImplementedError()

    def execute_onchain_transaction(
        self,
        transaction_executor: Callable[[Transaction], TransactionReceipt],
        transaction: Transaction
    ) -> int:
        return self.transaction_manager.place_transaction(transaction_executor, transaction=transaction)
