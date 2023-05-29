from _decimal import Decimal
from typing import Tuple

from rubi import ERC20


def _price_and_size_from_asset_amounts(
    base_asset: ERC20,
    quote_asset: ERC20,
    base_amount: int,
    quote_amount: int
) -> Tuple[Decimal, Decimal]:
    price = (
                Decimal(quote_amount) / Decimal(10 ** quote_asset.decimal)
            ) / (
                Decimal(base_amount) / Decimal(10 ** base_asset.decimal)
            )
    size = Decimal(base_amount) / Decimal(10 ** base_asset.decimal)

    return price, size
