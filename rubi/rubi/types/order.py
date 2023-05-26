from _decimal import Decimal
from enum import Enum
from typing import Optional


class Side(Enum):
    BID = "BID"
    ASK = "ASK"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

    # this is only used for reading
    CANCEL = "CANCEL"


class Transaction:
    def __init__(
        self,
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        self.nonce = nonce
        self.gas = gas
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee_per_gas = max_priority_fee_per_gas


# TODO: edit this to deal with cancels
class BaseOrderTransaction(Transaction):
    def __init__(
        self,
        pair_name: str,
        order_type: OrderType,
        order_side: Side,
        size: Decimal,
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        super().__init__(
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

        self.pair = pair_name
        self.order_side = order_side
        self.order_type = order_type
        self.size = size


class MarketOrderTransaction(BaseOrderTransaction):
    def __init__(
        self,
        pair_name: str,
        order_side: Side,
        size: Decimal,
        allowable_slippage: Optional[Decimal] = Decimal("0.005"),
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.MARKET,
            order_side=order_side,
            size=size,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

        self.allowable_slippage = allowable_slippage


class LimitOrderTransaction(BaseOrderTransaction):
    def __init__(
        self,
        pair_name: str,
        order_side: Side,
        size: Decimal,
        price: Decimal,
        nonce: Optional[int] = None,
        gas: int = 350000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ):
        super().__init__(
            pair_name=pair_name,
            order_type=OrderType.LIMIT,
            order_side=order_side,
            size=size,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

        self.price = price
