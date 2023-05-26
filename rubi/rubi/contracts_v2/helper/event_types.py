import logging as log
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type

from eth_typing import ChecksumAddress, HexStr
from eth_utils import add_0x_prefix
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.types import EventData


# TODO: look into how these events are being constructed because things are not working as intended right now
class BaseEvent(ABC):
    def __init__(self, block_number: int, **args):
        self.block_number = block_number

    @staticmethod
    @abstractmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        raise NotImplementedError()

    @classmethod
    def default_handler(cls, pair_name: str, event_type: Type["BaseEvent"], event_data: EventData) -> None:
        log.info(event_data)


######################################################################
# market events
######################################################################

class BaseMarketEvent(BaseEvent, ABC):
    def __init__(self, id: bytes, pair: bytes, **args):
        super().__init__(**args)
        self.id = int(id.hex(), 16)
        self.pair = add_0x_prefix(HexStr(pair.hex()))


class EmitOfferEvent(BaseMarketEvent):
    def __init__(
        self,
        maker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        pay_amt: int,
        buy_amt: int,
        **args
    ):
        super().__init__(**args)
        self.maker = maker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.pay_amt = pay_amt
        self.buy_amt = buy_amt

    @staticmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitOffer.create_filter(argument_filters=argument_filters, fromBlock="latest")

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class EmitTakeEvent(BaseMarketEvent):
    def __init__(
        self,
        maker: ChecksumAddress,
        taker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        take_amt: int,
        give_amt: int,
        **args
    ):
        super().__init__(**args)

        self.maker = maker
        self.taker = taker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.take_amt = take_amt
        self.give_amt = give_amt

    @staticmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitTake.create_filter(argument_filters=argument_filters, fromBlock="latest")

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class EmitCancelEvent(BaseMarketEvent):
    def __init__(
        self,
        maker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        pay_amt: int,
        buy_amt: int,
        **args
    ):
        super().__init__(**args)

        self.maker = maker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.pay_amt = pay_amt
        self.buy_amt = buy_amt

    @staticmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitCancel.create_filter(argument_filters=argument_filters, fromBlock="latest")


class EmitFeeEvent(BaseMarketEvent):
    def __init__(
        self,
        taker: ChecksumAddress,
        feeTo: ChecksumAddress,
        asset: ChecksumAddress,
        feeAmt: int,
        **args
    ):
        super().__init__(**args)

        self.taker = taker
        self.fee_to = feeTo
        self.asset = asset
        self.fee_amt = feeAmt

    @staticmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitFee.create_filter(argument_filters=argument_filters, fromBlock="latest")


class EmitDeleteEvent(BaseMarketEvent):
    def __init__(self, maker: ChecksumAddress, **args):
        super().__init__(**args)

        self.maker = maker

    @staticmethod
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitDelete.create_filter(argument_filters=argument_filters, fromBlock="latest")


######################################################################
# router events
######################################################################

# TODO: fix, see format above
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
    def create_event_filter(contract: Contract, argument_filters: Optional[Dict[str, Any]] = None) -> LogFilter:
        return contract.events.emitSwap.create_filter(argument_filters=argument_filters, fromBlock="latest")
