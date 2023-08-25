import logging

from abc import ABC, abstractmethod
from collections import deque
from threading import Semaphore, Lock, Thread
from typing import Any, Callable

logger = logging.getLogger(__name__)


class BaseEventQueue(ABC):
    """Base class for event queues.

    This class provides a basic structure for event queues used in event-driven trading frameworks. Subclasses should
    inherit from this class and implement the necessary methods to handle adding messages and handling messages.

    :param message_queue: The underlying message queue for storing incoming messages.
    :type message_queue: Any
    :param message_handler: The callable object that handles the messages from the queue.
    :type message_handler: Callable
    """

    def __init__(
        self,
        message_queue: Any,
        message_handler: Callable,
    ):
        self.message_queue = message_queue
        self.message_handler = message_handler
        self.message_notifier = Semaphore(value=0)
        self.queue_lock = Lock()

        self.running = False

    def start(self):
        """Start the event queue.

        This method starts the event queue by setting the running flag to True and spawning a thread to handle the
        messages in the queue.
        """
        self.running = True

        thread = Thread(target=self._handle_messages, daemon=True)
        thread.start()

    def stop(self):
        """Stop the event queue."""
        self.running = False

    @abstractmethod
    def add_message(self, message: Any):
        """This method should be implemented by subclasses to add a new message to the event queue.

        :param message: The message to be added to the event queue.
        :type message: Any
        """
        raise NotImplementedError()

    @abstractmethod
    def _handle_messages(self):
        """This method should be implemented by subclasses to handle messages in the event queue."""
        raise NotImplementedError()


class FreshEventQueue(BaseEventQueue):
    """Event queue that handles the latest message.

    This event queue implementation handles only the latest message added to the queue and drops any older messages.

    :param message_handler: The callable object that handles the messages from the queue.
    :type message_handler: Callable
    """

    def __init__(self, message_handler: Callable):
        message_queue = deque(maxlen=1)
        super().__init__(message_queue=message_queue, message_handler=message_handler)

    def add_message(self, message: Any):
        """This method adds a new message to the fresh event queue. If the queue was empty before adding the message,
        it releases the message notifier semaphore to notify the queue handler that there is a new message to handle.

        :param message: The message to be added to the fresh event queue.
        :type message: Any
        """
        with self.queue_lock:
            notify = len(self.message_queue) == 0

            self.message_queue.append(message)

        if notify:
            self.message_notifier.release()

    def _handle_messages(self):
        """This method handles messages from the fresh event queue. It acquires the message notifier semaphore,
        retrieves the latest message from the queue, and passes it to the message handler.
        """
        logger.info(f"{self.__class__} started")
        while self.running:
            self.message_notifier.acquire()

            with self.queue_lock:
                message = self.message_queue.pop()

            self.message_handler(message)


class FIFOEventQueue(BaseEventQueue):
    """Event queue that handles messages in a first-in-first-out (FIFO) order.

    This event queue implementation handles messages in the order they were added to the queue.

    :param message_handler: The callable object that handles the messages from the queue.
    :type message_handler: Callable
    """

    def __init__(self, message_handler: Callable):
        message_queue = deque()
        super().__init__(message_queue=message_queue, message_handler=message_handler)

    def add_message(self, message: Any):
        """This method adds a new message to the FIFO event queue and releases the message notifier semaphore
        to notify the queue handler that new messages have been added to the queue and can be processed.

        :param message: The message to be added to the FIFO event queue.
        :type message: Any
        """
        with self.queue_lock:
            self.message_queue.append(message)

        self.message_notifier.release()

    def _handle_messages(self):
        """This method handles messages from the FIFO event queue. It acquires the message notifier semaphore,
        retrieves the first message from the queue, and passes it to the message handler.

        """
        logger.info(f"{self.__class__} started")
        while self.running:
            self.message_notifier.acquire()

            with self.queue_lock:
                message = self.message_queue.popleft()

            self.message_handler(message)
