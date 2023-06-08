from _decimal import Decimal

from rubi import Pair, OrderSide


class Inventory:
    def __init__(self, pair: Pair, quote_asset_amount: Decimal):
        self.pair = pair

        self.quote_asset_amount = quote_asset_amount
        self.available_quote_asset_amount = quote_asset_amount

        self.base_asset_amount = Decimal("0")
        self.available_base_asset_amount = Decimal("0")
        self.base_asset_average_price = Decimal("0")

    def add_trade(self, order_side: OrderSide, price: Decimal, size: Decimal) -> None:
        if order_side == OrderSide.SELL:
            self.base_asset_amount -= size

            self.quote_asset_amount += size * price
        else:
            self.base_asset_average_price = (
                                                price * size + (
                                                    self.base_asset_average_price * self.base_asset_amount)
                                            ) / (self.base_asset_amount + size)

            self.base_asset_amount += size

            self.quote_asset_amount -= size * price
