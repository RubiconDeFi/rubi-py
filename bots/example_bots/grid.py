from _decimal import Decimal

from rubi import OrderSide


class Grid:

    def __init__(
        self,
        starting_base_asset_amount: Decimal,
        starting_quote_asset_amount: Decimal,
        starting_mid_price: Decimal,
        grid_spread_in_quote: Decimal,
        level_spread_multiplier: Decimal,
        number_levels: int,
        level_allocation_multiplier: Decimal
    ):
        self.base_asset_amount = starting_base_asset_amount
        self.quote_asset_amount = starting_quote_asset_amount
        self.mid_price = starting_mid_price
        self.grid_spread_in_quote = grid_spread_in_quote
        self.level_spread_multiplier = level_spread_multiplier
        self.number_levels = number_levels
        self.level_allocation_multiplier = level_allocation_multiplier

    def base_level_size(self, price: Decimal) -> Decimal:
        total_grid_amount = self.base_asset_amount + self.quote_asset_amount / price

        base_level_multiplier = self.number_levels + (1 * self.level_allocation_multiplier) ** self.number_levels

        return (total_grid_amount / 2) / base_level_multiplier

    def get_level_size(self, level: int, price: Decimal) -> Decimal:
        return self.base_level_size(price=price) * (1 + self.level_allocation_multiplier) ** level

    def get_level_price(self, side: OrderSide, level: int) -> Decimal:
        return self.mid_price - side.sign() * (self.grid_spread_in_quote / 2) * (level + 1) * (
            1 + self.level_spread_multiplier) ** level

    def update_mid_price(self, mid_price: Decimal):
        self.mid_price = mid_price
