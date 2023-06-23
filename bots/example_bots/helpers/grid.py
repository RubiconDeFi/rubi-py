import math
from _decimal import Decimal
from typing import List, Optional, Tuple

from rubi import OrderSide


class DesiredOrder:
    def __init__(
        self,
        price: Decimal,
        size: Decimal,
        side: OrderSide
    ):
        self.price = price
        self.size = size
        self.side = side


class GridLevel:
    def __init__(self, bid: DesiredOrder, ask: DesiredOrder):
        self.bid = bid
        self.ask = ask


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
        grid_range: Decimal,
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
        self.price_tick = price_tick
        self.grid_range = grid_range
        self.spread = spread

        self.min_order_size_in_quote = min_order_size_in_quote

        # Grid
        self.desired_grid: List[GridLevel] = self._construct_grid()
        self.current_grid_index: int = self._calculate_grid_index()

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

        self.current_grid_index = self._calculate_grid_index()

    ######################################################################
    # grid functions
    ######################################################################

    def get_desired_orders(self) -> Tuple[List[DesiredOrder], List[DesiredOrder]]:
        desired_bids = list(map(lambda level: level.bid, self.desired_grid[self.current_grid_index:: -1]))
        desired_bids.reverse()
        desired_asks = list(map(lambda level: level.ask, self.desired_grid[self.current_grid_index:]))

        return desired_bids, desired_asks

    def _calculate_grid_index(self) -> int:
        total_size = self.base_asset_amount * self.fair_price + self.quote_asset_amount

        quote_as_percent_of_size = self.quote_asset_amount / total_size

        grid_levels = len(self.desired_grid)

        middle_index = math.ceil(grid_levels / 2)

        index = grid_levels * quote_as_percent_of_size

        if index <= middle_index:
            current_grid_index = math.ceil(index)
        else:
            current_grid_index = math.floor(index)

        return current_grid_index - 1

    def _construct_grid(self) -> List[GridLevel]:
        bid_side = self._construct_grid_side(OrderSide.BUY)
        bid_side.reverse()

        ask_side = self._construct_grid_side(OrderSide.SELL)

        middle_level = GridLevel(
            bid=DesiredOrder(
                price=self._round_to_grid_tick(self.fair_price - self.spread / 2),
                size=bid_side[-1].bid.size,
                side=OrderSide.BUY
            ),
            ask=DesiredOrder(
                price=self._round_to_grid_tick(self.fair_price + self.spread / 2),
                size=ask_side[0].ask.size,
                side=OrderSide.SELL
            )
        )

        desired_grid = bid_side + [middle_level] + ask_side

        return desired_grid

    def _construct_grid_side(self, side: OrderSide) -> List[GridLevel]:
        half_size = (self.base_asset_amount * self.fair_price + self.quote_asset_amount) / 2

        capital_restricted_number_of_levels = half_size / self.min_order_size_in_quote

        edge = self.fair_price - side.sign() * self.grid_range / 2

        price = self._round_to_grid_tick(
            self.fair_price - (side.sign() * self.spread) / 2
        ) - side.sign() * self.price_tick

        max_number_levels = (price * side.sign() - edge * side.sign()) / self.price_tick

        skip_capital = round(max_number_levels / capital_restricted_number_of_levels)

        level_size = half_size / min(max_number_levels / skip_capital, capital_restricted_number_of_levels)

        grid_side_levels = []
        remaining_capital = half_size
        i = 1
        match side:
            case OrderSide.BUY:
                while price >= edge:
                    size = level_size if (
                        i % skip_capital == 0 and remaining_capital > self.min_order_size_in_quote
                    ) else Decimal("0")

                    grid_side_levels.append(
                        GridLevel(
                            bid=DesiredOrder(
                                price=price,
                                size=size / price,
                                side=OrderSide.BUY
                            ),
                            ask=DesiredOrder(
                                price=price + self.spread,
                                size=size / (price + self.spread),
                                side=OrderSide.SELL
                            )
                        )
                    )
                    price = price - self.price_tick
                    i += 1
                    remaining_capital -= size

            case OrderSide.SELL:
                while price <= edge:
                    size = level_size if (
                        i % skip_capital == 0 and remaining_capital > self.min_order_size_in_quote
                    ) else Decimal("0")

                    grid_side_levels.append(
                        GridLevel(
                            bid=DesiredOrder(
                                price=price - self.spread,
                                size=size / (price - self.spread),
                                side=OrderSide.BUY
                            ),
                            ask=DesiredOrder(
                                price=price,
                                size=size / price,
                                side=OrderSide.SELL
                            )
                        )
                    )
                    price = price + self.price_tick
                    i += 1
                    remaining_capital -= size

        return list(
            filter(lambda level: level.bid.size != Decimal("0") or level.ask.size != Decimal("0"), grid_side_levels)
        )

    ######################################################################
    # helper functions
    ######################################################################

    def _round_to_grid_tick(self, number: Decimal) -> Decimal:
        if self.price_tick < Decimal("1"):
            rounded = round(number / self.price_tick) * self.price_tick
        else:
            rounded = round(number * self.price_tick) / self.price_tick

        return rounded
