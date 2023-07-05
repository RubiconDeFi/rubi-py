from _decimal import Decimal

from eth_typing import ChecksumAddress
from rubi import OrderType, OrderSide, OrderEvent


class ActiveLimitOrder:
    def __init__(
        self,
        limit_order_id: int,
        limit_order_owner: ChecksumAddress,
        pair_name: str,
        order_side: OrderSide,
        order_type: OrderType,
        price: Decimal,
        size: Decimal,
        filled_size: Decimal = Decimal("0")
    ):
        self.limit_order_id = limit_order_id
        self.limit_order_owner = limit_order_owner
        self.pair_name = pair_name
        self.order_side = order_side
        self.order_type = order_type
        self.price = price
        self.size = size
        self.filled_size = filled_size

    @classmethod
    def from_order_event(cls, order: OrderEvent):
        if order.order_type != OrderType.LIMIT:
            raise Exception("ActiveLimitOrder can only be instantiated from new LimitOrderEvents")

        return cls(
            limit_order_id=order.limit_order_id,
            limit_order_owner=order.limit_order_owner,
            pair_name=order.pair_name,
            order_side=order.order_side,
            order_type=order.order_type,
            price=order.price,
            size=order.size
        )

    def is_full_take(self, take_event: OrderEvent, allowed_size_differential: Decimal) -> bool:
        return self.remaining_size() - take_event.size <= allowed_size_differential

    def update_with_take(self, take_event: OrderEvent) -> None:
        self.filled_size += take_event.size

    def remaining_size(self) -> Decimal:
        return self.size - self.filled_size

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))