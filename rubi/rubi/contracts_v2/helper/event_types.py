import logging as log
from abc import ABC, abstractmethod

from eth_typing import ChecksumAddress
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.types import EventData


class BaseEvent(ABC):
    def __init__(self, **args):
        self.id = int(args["id"].hex(), 16)
        self.pair = args["pair"]

    @staticmethod
    @abstractmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        raise NotImplementedError()

    # TODO: this should probably be an abstractmethod that is overwritten per child
    @classmethod
    def handler(cls, event: EventData) -> None:
        log.info(event)
        log.info(cls(**event["args"]))


######################################################################
# market events
######################################################################

class BaseMarketEvent(BaseEvent, ABC):
    id: int
    pair: bytes


class EmitOfferEvent(BaseMarketEvent):
    maker: ChecksumAddress
    pay_gem: ChecksumAddress
    buy_gem: ChecksumAddress
    pay_amt: int
    buy_amt: int

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitOffer.create_filter(fromBlock="latest")


class EmitTakeEvent(BaseMarketEvent):
    maker: ChecksumAddress
    taker: ChecksumAddress
    pay_gem: ChecksumAddress
    buy_gem: ChecksumAddress
    take_amt: int
    give_amt: int

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitTake.create_filter(fromBlock="latest")


class EmitCancelEvent(BaseMarketEvent):
    maker: ChecksumAddress
    pay_gem: ChecksumAddress
    buy_gem: ChecksumAddress
    pay_amt: int
    buy_amt: int

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitCancel.create_filter(fromBlock="latest")


class EmitFeeEvent(BaseMarketEvent):
    taker: ChecksumAddress
    feeTo: ChecksumAddress
    asset: ChecksumAddress
    feeAmt: int

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitFee.create_filter(fromBlock="latest")


class EmitDeleteEvent(BaseMarketEvent):
    maker: ChecksumAddress

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitDelete.create_filter(fromBlock="latest")


######################################################################
# router events
######################################################################

class EmitSwap(BaseEvent):
    recipient: ChecksumAddress
    inputERC20: ChecksumAddress
    targetERC20: ChecksumAddress
    pair: bytes
    inputAmount: int
    realizedFill: int
    hurdleBuyAmtMin: int

    def __init__(self, **args):
        super().__init__(**args)
        self.__dict__.update(args)

    @staticmethod
    def create_event_filter(contract: Contract) -> LogFilter:
        return contract.events.emitSwap.create_filter(fromBlock="latest")
