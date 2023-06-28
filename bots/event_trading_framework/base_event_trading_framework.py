from abc import ABC, abstractmethod
from multiprocessing import Queue
from typing import Union

from rubi import OrderBook, OrderEvent

from event_trading_framework.helpers import (
    TransactionResult, ThreadedTransactionManager, FreshEventQueue, FIFOEventQueue
)


class BaseEventTradingFramework(ABC):
    """Base class for event-driven trading frameworks.

    This class provides a basic structure for event-driven trading frameworks. Subclasses should inherit from this class
    and implement the necessary methods to handle specific events in order to define a trading strategy.

    :param event_queue: The event queue to be used for receiving events.
    :type event_queue: Queue
    :param transaction_manager: The transaction manager responsible for executing trades.
    :type transaction_manager: ThreadedTransactionManager
    """

    def __init__(self, event_queue: Queue, transaction_manager: ThreadedTransactionManager):
        if event_queue is not transaction_manager.transaction_result_queue:
            raise Exception("The transaction result queue and the event_queue should be the same queue.")

        self.event_queue = event_queue

        self.running = False

        # Initialize transaction manager
        self.transaction_manager = transaction_manager

        # Initialize message queues
        self.orderbook_event_queue = FreshEventQueue(message_handler=self.on_orderbook)
        self.order_event_queue = FIFOEventQueue(message_handler=self.on_order)
        self.transaction_result_queue = FIFOEventQueue(message_handler=self.on_transaction_result)

    @abstractmethod
    def on_startup(self):
        """This method should be implemented by subclasses to perform any necessary operations during the startup phase
        of the trading framework.
        """
        raise NotImplementedError()

    def start(self):
        """This method starts the trading framework by executing the startup operations, starting the transaction
        manager, and starting the message queue handlers. It also listens for events from the event queue and routes
        them to the appropriate message queues.
        """

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

    @abstractmethod
    def on_shutdown(self):
        """This method should be implemented by subclasses to perform any necessary operations during the shutdown phase
        of the trading framework.
        """
        raise NotImplementedError()

    def stop(self, *args, **kwargs):
        """This method stops the trading framework by setting the running flag to False, executing the shutdown
        operations, and stopping the message queue handlers and transaction manager.
        """
        self.running = False

        self.on_shutdown()

        self.orderbook_event_queue.stop()
        self.order_event_queue.stop()
        self.transaction_result_queue.stop()

        self.transaction_manager.stop()

    @abstractmethod
    def on_orderbook(self, orderbook: OrderBook):
        """This method should be implemented by subclasses to handle order book events.

        :param orderbook: The order book event to be handled.
        :type orderbook: OrderBook
        """
        raise NotImplementedError()

    @abstractmethod
    def on_order(self, order: OrderEvent):
        """This method should be implemented by subclasses to handle order events.

        :param order: The order event to be handled.
        :type order: OrderEvent
        """
        raise NotImplementedError()

    @abstractmethod
    def on_transaction_result(self, result: TransactionResult):
        """This method should be implemented by subclasses to handle transaction result events.

        :param result: The transaction result event to be handled.
        :type result: TransactionResult
        """
        raise NotImplementedError()
