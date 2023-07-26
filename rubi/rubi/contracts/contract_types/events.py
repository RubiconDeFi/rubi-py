import logging as log
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar, Union

from eth_typing import ChecksumAddress, HexStr
from eth_utils import add_0x_prefix
from web3._utils.filters import LogFilter  # noqa
from web3.contract import Contract
from web3.types import EventData

# To solve for circular dependencies
_RubiconMarket = TypeVar("_RubiconMarket")
_RubiconRouter = TypeVar("_RubiconRouter")


class BaseEvent(ABC):
    """Base class for events to define the structure of an Event from a Rubicon contract."""

    def __init__(self, block_number: int, **args):
        """Initialize a BaseEvent instance.

        :param block_number: The block number of the event.
        :type block_number: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        self.block_number = block_number

    @staticmethod
    def builder(
        name: str, **kwargs
    ) -> Union["EmitOfferEvent", "EmitTakeEvent", "EmitCancelEvent", "EmitSwap"]:
        match name:
            case "emitOffer":
                return EmitOfferEvent(**kwargs)
            case "emitTake":
                return EmitTakeEvent(**kwargs)
            case "emitCancel":
                return EmitCancelEvent(**kwargs)
            case "emitSwap":
                return EmitSwap(**kwargs)

    @staticmethod
    @abstractmethod
    def get_event_contract(
        market: _RubiconMarket, router: _RubiconRouter
    ) -> Union[_RubiconMarket, _RubiconRouter]:
        """Abstract method to determine the contract an event corresponds to. Must be overridden in subclasses.

        :param market: The RubiconMarket instance.
        :type market: _RubiconMarket
        :param router: The RubiconRouter instance.
        :type router: _RubiconRouter
        :return: The contract corresponding to the event.
        :rtype: Union[_RubiconMarket, _RubiconRouter]
        """
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """Abstract method to create an event filter for the given contract with optional argument filters. Must be
        overridden in each event subclass.

        :param contract: The contract instance.
        :type contract: Contract
        :param argument_filters: Optional filters. Only events that match these filters will be returned when the filter
            is queried.
        :type argument_filters: Optional[Dict[str, Any]]
        :return: The created event filter.
        :rtype: LogFilter
        """
        raise NotImplementedError()

    @classmethod
    def default_handler(
        cls, pair_name: str, event_type: Type["BaseEvent"], event_data: EventData
    ) -> None:
        """A default event handler. If no handler is provided then this one is used.

        :param pair_name: The name of the pair.
        :type pair_name: str
        :param event_type: The type of the event.
        :type event_type: Type["BaseEvent"]
        :param event_data: The data of the event.
        :type event_data: EventData
        """
        log.info(event_data)

    @staticmethod
    @abstractmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """Get the default filters for an event. These are used if no argument filters are provided. By default, these
        filters make sure we only receive events that relate to us. E.g on markets we care about.

        :param bid_identifier: The identifier for bid events.
        :type bid_identifier: str
        :param ask_identifier: The identifier for ask events.
        :type ask_identifier: str
        :return: The default filters.
        :rtype: dict
        """
        raise NotImplementedError()

    # noinspection PyMethodMayBeStatic
    def client_filter(self, wallet: ChecksumAddress) -> bool:
        """Filter function for client-side filtering. By default, no filtering is done but this can optionally be
        overwritten by each subclass.

        :param wallet: The wallet address.
        :type wallet: ChecksumAddress
        :return: True if the event passes the filter, False otherwise.
        :rtype: bool
        """
        return True

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


######################################################################
# market events
######################################################################


class BaseMarketEvent(BaseEvent, ABC):
    """This class is a base class for all MarketEvents"""

    def __init__(self, id: bytes, pair: bytes, **args):
        """Initialize a BaseMarketEvent instance.

        :param id: The event ID.
        :type id: bytes
        :param pair: The event bid or ask pair identifier.
        :type pair: bytes
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)
        self.id = int(id.hex(), 16)
        self.pair = add_0x_prefix(HexStr(pair.hex()))

    @staticmethod
    def get_event_contract(
        market: _RubiconMarket, router: _RubiconRouter
    ) -> Union[_RubiconMarket, _RubiconRouter]:
        """implementation of BaseEvent get_event_contract"""
        return market


class EmitOfferEvent(BaseMarketEvent):
    """Event emitted whenever a new offer is made on the RubiconMarket"""

    def __init__(
        self,
        maker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        pay_amt: int,
        buy_amt: int,
        **args,
    ):
        """Initialize an EmitOfferEvent instance.

        :param maker: The maker address.
        :type maker: ChecksumAddress
        :param pay_gem: The address of the token to be paid.
        :type pay_gem: ChecksumAddress
        :param buy_gem: The address of the token to be bought.
        :type buy_gem: ChecksumAddress
        :param pay_amt: The amount to be paid.
        :type pay_amt: int
        :param buy_amt: The amount to be bought.
        :type buy_amt: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)
        self.maker = maker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.pay_amt = pay_amt
        self.buy_amt = buy_amt

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitOffer.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {"pair": [bid_identifier, ask_identifier]}

        return {key: value for key, value in filters.items() if value is not None}


class EmitTakeEvent(BaseMarketEvent):
    """Event emitted whenever an offer is taken by a market order on the RubiconMarket"""

    def __init__(
        self,
        maker: ChecksumAddress,
        taker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        take_amt: int,
        give_amt: int,
        **args,
    ):
        """Initialize an EmitTakeEvent instance.

        :param maker: The maker address.
        :type maker: ChecksumAddress
        :param taker: The taker address.
        :type taker: ChecksumAddress
        :param pay_gem: The address of the token that was paid.
        :type pay_gem: ChecksumAddress
        :param buy_gem: The address of the token that was bought.
        :type buy_gem: ChecksumAddress
        :param take_amt: The amount that was taken.
        :type take_amt: int
        :param give_amt: The amount that was given.
        :type give_amt: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)

        self.maker = maker
        self.taker = taker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.take_amt = take_amt
        self.give_amt = give_amt

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitTake.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: HexStr, ask_identifier: HexStr) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {"pair": [bid_identifier, ask_identifier]}

        return {key: value for key, value in filters.items() if value is not None}

    def client_filter(self, wallet: ChecksumAddress) -> bool:
        """overwriting of BaseEvent client_filter to only filter when our wallet is either the maker or taker"""
        return wallet is None or (self.maker == wallet or self.taker == wallet)


class EmitCancelEvent(BaseMarketEvent):
    """Event emitted whenever an offer is cancelled on the RubiconMarket"""

    def __init__(
        self,
        maker: ChecksumAddress,
        pay_gem: ChecksumAddress,
        buy_gem: ChecksumAddress,
        pay_amt: int,
        buy_amt: int,
        **args,
    ):
        """Initialize an EmitCancelEvent instance.

        :param maker: The maker address.
        :type maker: ChecksumAddress
        :param pay_gem: The address of the token to be paid of the cancelled offer.
        :type pay_gem: ChecksumAddress
        :param buy_gem: The address of the token to be bought of the cancelled offer.
        :type buy_gem: ChecksumAddress
        :param pay_amt: The amount to be paid of the cancelled offer.
        :type pay_amt: int
        :param buy_amt: The amount to be bought of the cancelled offer.
        :type buy_amt: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)

        self.maker = maker
        self.pay_gem = pay_gem
        self.buy_gem = buy_gem
        self.pay_amt = pay_amt
        self.buy_amt = buy_amt

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitCancel.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {"pair": [bid_identifier, ask_identifier]}

        return {key: value for key, value in filters.items() if value is not None}


class EmitFeeEvent(BaseMarketEvent):
    """Event emitted whenever an offer is taken on the RubiconMarket that results in a fee being paid to the maker."""

    def __init__(
        self,
        taker: ChecksumAddress,
        feeTo: ChecksumAddress,
        asset: ChecksumAddress,
        feeAmt: int,
        **args,
    ):
        """Initialize an EmitFeeEvent instance.

        :param taker: The taker address.
        :type taker: ChecksumAddress
        :param feeTo: The address to receive the fee.
        :type feeTo: ChecksumAddress
        :param asset: The address of the asset for the fee.
        :type asset: ChecksumAddress
        :param feeAmt: The amount of the fee.
        :type feeAmt: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)

        self.taker = taker
        self.fee_to = feeTo
        self.asset = asset
        self.fee_amt = feeAmt

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitFee.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {}

        return {key: value for key, value in filters.items() if value is not None}


class EmitDeleteEvent(BaseMarketEvent):
    """Event emitted whenever an offer is fully taken by a market order on the RubiconMarket resulting in the offer
    being closed
    """

    def __init__(self, maker: ChecksumAddress, **args):
        """Initialize an EmitDeleteEvent instance.

        :param maker: The maker address.
        :type maker: ChecksumAddress
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)

        self.maker = maker

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitDelete.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {"pair": [bid_identifier, ask_identifier]}

        return {key: value for key, value in filters.items() if value is not None}


######################################################################
# router events
######################################################################


class EmitSwap(BaseEvent):
    """Event emitted whenever swap is executed on the RubiconRouter"""

    def __init__(
        self,
        recipient: ChecksumAddress,
        inputERC20: ChecksumAddress,
        targetERC20: ChecksumAddress,
        pair: bytes,
        inputAmount: int,
        realizedFill: int,
        hurdleBuyAmtMin: int,
        **args,
    ):
        """Initialize an EmitSwap instance.

        :param recipient: The address of the recipient of the swap.
        :type recipient: ChecksumAddress
        :param inputERC20: The address of the input ERC20 token.
        :type inputERC20: ChecksumAddress
        :param targetERC20: The address of the target ERC20 token.
        :type targetERC20: ChecksumAddress
        :param pair: The bid/offer identifier of the pair of tokens being swapped (first_token/last_token).
        :type pair: bytes
        :param inputAmount: The amount of input tokens being swapped.
        :type inputAmount: int
        :param realizedFill: The realized fill amount.
        :type realizedFill: int
        :param hurdleBuyAmtMin: The minimum hurdle buy amount.
        :type hurdleBuyAmtMin: int
        :param args: Additional arguments for the event.
        :type args: dict
        """
        super().__init__(**args)

        self.recipient = recipient
        self.inputERC20 = inputERC20
        self.targetERC20 = targetERC20
        self.pair = pair
        self.inputAmount = inputAmount
        self.realizedFill = realizedFill
        self.hurdleBuyAmtMin = hurdleBuyAmtMin

    @staticmethod
    def get_event_contract(
        market: _RubiconMarket, router: _RubiconRouter
    ) -> Union[_RubiconMarket, _RubiconRouter]:
        """implementation of BaseEvent get_event_contract"""
        return router

    @staticmethod
    def create_event_filter(
        contract: Contract, argument_filters: Optional[Dict[str, Any]] = None
    ) -> LogFilter:
        """implementation of BaseEvent create_event_filter"""
        return contract.events.emitSwap.create_filter(
            argument_filters=argument_filters, fromBlock="latest"
        )

    @staticmethod
    def default_filters(bid_identifier: str, ask_identifier: str) -> dict:
        """implementation of BaseEvent default_filters"""
        filters = {}

        return {key: value for key, value in filters.items() if value is not None}
