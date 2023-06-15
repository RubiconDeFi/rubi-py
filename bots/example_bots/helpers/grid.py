import math
from _decimal import Decimal
from typing import List, Optional

from rubi import OrderSide


class GridLevel:
    def __init__(
        self,
        price: Decimal,
        size: Decimal
    ):
        self.price = price
        self.size = size


class Grid:

    def __init__(
        self,
        # Inventory
        starting_base_asset_amount: Decimal,
        starting_quote_asset_amount: Decimal,
        starting_base_asset_average_price: Optional[Decimal],
        # Grid
        fair_price: Decimal,
        price_tick: Decimal,
        top_edge: Decimal,
        bottom_edge: Decimal,
        spread: Decimal,
        # Order
        min_order_size_in_quote: Decimal
    ):
        # Grid Inventory
        self.base_asset_amount = starting_base_asset_amount
        self.quote_asset_amount = starting_quote_asset_amount

        self.base_asset_average_price = (
            starting_base_asset_average_price if starting_base_asset_average_price is not None else Decimal("0")
        )

        # Grid Parameters
        self.fair_price = fair_price
        self.current_mid_price = fair_price
        self.price_tick = price_tick
        self.top_edge = top_edge
        self.bottom_edge = bottom_edge

        self.spread = spread

        # Grid orders
        self.min_order_size_in_quote = min_order_size_in_quote

        self.ideal_bids: List[GridLevel] = self._construct_ideal_side(OrderSide.BUY)
        self.ideal_asks: List[GridLevel] = self._construct_ideal_side(OrderSide.SELL)



    ######################################################################
    # inventory functions
    ######################################################################

    def add_trade(self, order_side: OrderSide, price: Decimal, size: Decimal) -> None:
        if order_side == OrderSide.SELL:
            self.base_asset_amount -= size

            self.quote_asset_amount += size * price
        else:
            self.base_asset_average_price = (
                                                price * size + (self.base_asset_average_price * self.base_asset_amount)
                                            ) / (self.base_asset_amount + size)

            self.base_asset_amount += size

            self.quote_asset_amount -= size * price

    ######################################################################
    # grid functions
    ######################################################################

    def _construct_ideal_side(self, side: OrderSide) -> List[GridLevel]:
        half_grid_size = (self.base_asset_amount * self.fair_price + self.quote_asset_amount) / 2

        if side == OrderSide.BUY:
            number_levels = round((self.fair_price - self.bottom_edge) / self.price_tick)
        else:
            number_levels = round((self.top_edge - self.fair_price) / self.price_tick)

        levels_between_order = math.ceil(number_levels / (half_grid_size / self.min_order_size_in_quote))

        size_in_quote = half_grid_size / (Decimal(number_levels) / levels_between_order)

        side_levels = []
        for i in range(1, number_levels):
            if not i % levels_between_order == 1:
                continue

            price = self.fair_price - side.sign() * self.price_tick * i

            side_levels.append(
                GridLevel(
                    price=price,
                    size=size_in_quote / price
                )
            )

        return side_levels

    ######################################################################
    # helper functions
    ######################################################################

    def _round_to_grid_tick(self, number: Decimal) -> Decimal:
        if self.price_tick < Decimal("1"):
            rounded = round(number / self.price_tick) * self.price_tick
        else:
            rounded = round(number * self.price_tick) / self.price_tick

        return rounded
