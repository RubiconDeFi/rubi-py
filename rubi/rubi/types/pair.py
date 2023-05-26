from _decimal import Decimal

from rubi import ERC20


class Pair:
    def __init__(
        self,
        name: str,
        base_asset: ERC20,
        quote_asset: ERC20,
        current_base_asset_allowance: Decimal,
        current_quote_asset_allowance: Decimal
    ):
        self.name = name

        self.base_asset: ERC20 = base_asset
        self.quote_asset: ERC20 = quote_asset

        self.bid_identifier: bytes = base_asset.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[self.quote_asset.address, self.base_asset.address]
        ).hex()
        self.ask_identifier: bytes = base_asset.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[self.base_asset.address, self.quote_asset.address]
        ).hex()

        self.current_base_asset_allowance = current_base_asset_allowance
        self.current_quote_asset_allowance = current_quote_asset_allowance

    def update_base_asset_allowance(self, new_base_asset_allowance: Decimal) -> None:
        self.current_base_asset_allowance = new_base_asset_allowance

    def update_quote_asset_allowance(self, new_quote_asset_allowance: Decimal) -> None:
        self.current_quote_asset_allowance = new_quote_asset_allowance


class PairDoesNotExistException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
