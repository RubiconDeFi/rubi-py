import logging as log

from abc import ABC, abstractmethod
from collections import deque
from threading import Semaphore, Lock, Thread
from typing import Any, Callable


class BaseEventQueue(ABC):

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
        self.running = True

        thread = Thread(target=self._handle_messages, daemon=True)
        thread.start()

    def stop(self):
        self.running = False

    @abstractmethod
    def add_message(self, message: Any):
        raise NotImplementedError()

    @abstractmethod
    def _handle_messages(self):
        raise NotImplementedError()


class FreshEventQueue(BaseEventQueue):
    def __init__(self, message_handler: Callable):
        message_queue = deque(maxlen=1)
        super().__init__(message_queue=message_queue, message_handler=message_handler)

    def add_message(self, message: Any):
        with self.queue_lock:
            notify = len(self.message_queue) == 0

            self.message_queue.append(message)

        if notify:
            self.message_notifier.release()

    def _handle_messages(self):
        log.info(f"{self.__class__} started")
        while self.running:
            self.message_notifier.acquire()

            with self.queue_lock:
                message = self.message_queue.pop()

            self.message_handler(message)


class FIFOEventQueue(BaseEventQueue):
    def __init__(self, message_handler: Callable):
        message_queue = deque()
        super().__init__(message_queue=message_queue, message_handler=message_handler)

    def add_message(self, message: Any):
        with self.queue_lock:
            self.message_queue.append(message)

        self.message_notifier.release()

    def _handle_messages(self):
        log.info(f"{self.__class__} started")
        while self.running:
            self.message_notifier.acquire()

            with self.queue_lock:
                message = self.message_queue.popleft()

            self.message_handler(message)
