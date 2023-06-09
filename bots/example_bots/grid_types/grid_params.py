from _decimal import Decimal
from typing import Optional

from rubi import OrderSide


class GridParams:

    def __init__(
        self,
        starting_base_asset_amount: Decimal,
        starting_quote_asset_amount: Decimal,
        starting_mid_price: Decimal,
        grid_spread_in_quote: Decimal,
        level_spread_multiplier: Decimal,
        number_levels: int,
        base_level_size: Decimal,
        # order related
        min_order_size_in_quote: Decimal,
        allowed_order_drift: Optional[Decimal] = None
    ):
        self.base_asset_amount = starting_base_asset_amount
        self.quote_asset_amount = starting_quote_asset_amount
        self.mid_price = starting_mid_price
        self.grid_spread_in_quote = grid_spread_in_quote
        self.level_spread_multiplier = level_spread_multiplier
        self.number_levels = number_levels
        self.base_level_size = base_level_size

        self.scale_factor = self._calculate_scale_factor()

        # transaction related
        self.min_order_size_in_quote = min_order_size_in_quote
        self.allowed_order_drift = allowed_order_drift

    def get_level_size(self, level: int) -> Decimal:
        return self.base_level_size + level * self.base_level_size * (1 + self.scale_factor)

    def _calculate_scale_factor(self):
        total_grid_size = self.base_asset_amount + self.quote_asset_amount / self.mid_price

        scale_factor = ((((total_grid_size / 2) / self.base_level_size) - self.number_levels) / (
            Decimal((self.number_levels / 2) * (self.number_levels - 1)))) - 1

        return scale_factor

    def get_level_price(self, side: OrderSide, level: int) -> Decimal:
        return self.mid_price - side.sign() * (self.grid_spread_in_quote / 2) * (level + 1) * (
            1 + self.level_spread_multiplier) ** level

    def update_mid_price(self, mid_price: Decimal):
        self.mid_price = mid_price
