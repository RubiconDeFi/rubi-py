from _decimal import Decimal
from typing import Optional

from rubi import ERC20


class Pair:
    """Class representing a trading asset pair, e.g. WETH/USDC would have WETH as the base asset and USDC as the quote
    asset.

    :param name: The name of the pair, e.g. WETH/USDC.
    :type name: str
    :param base_asset: Base asset of the pair.
    :type base_asset: ERC20
    :param quote_asset: Quote asset of the pair.
    :type quote_asset: ERC20
    :param current_base_asset_allowance: The base asset spending allowance of the RubiconMarket contract, Optional.
    :type current_base_asset_allowance: Decimal
    :param current_quote_asset_allowance: The quote asset spending allowance of the RubiconMarket contract, Optional.
    :type current_quote_asset_allowance: Decimal
    """

    def __init__(
        self,
        name: str,
        base_asset: ERC20,
        quote_asset: ERC20,
        current_base_asset_allowance: Optional[Decimal],
        current_quote_asset_allowance: Optional[Decimal],
    ):
        self.name = name

        self.base_asset: ERC20 = base_asset
        self.quote_asset: ERC20 = quote_asset

        self.bid_identifier: str = base_asset.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[self.quote_asset.address, self.base_asset.address],
        ).hex()
        self.ask_identifier: str = base_asset.w3.solidity_keccak(
            abi_types=["address", "address"],
            values=[self.base_asset.address, self.quote_asset.address],
        ).hex()

        # TODO: think about structure of allowances on this class. Currently, this only caters for the RubiconMarket
        #  contract.
        self.current_base_asset_allowance = current_base_asset_allowance
        self.current_quote_asset_allowance = current_quote_asset_allowance

    def update_base_asset_allowance(self, new_base_asset_allowance: Decimal) -> None:
        """Update the current base asset allowance.

        :param new_base_asset_allowance: New base asset allowance.
        :type new_base_asset_allowance: Decimal
        :return: None
        """
        self.current_base_asset_allowance = new_base_asset_allowance

    def update_quote_asset_allowance(self, new_quote_asset_allowance: Decimal) -> None:
        """Update the current quote asset allowance.

        :param new_quote_asset_allowance: New quote asset allowance.
        :type new_quote_asset_allowance: Decimal
        :return: None
        """
        self.current_quote_asset_allowance = new_quote_asset_allowance


class PairDoesNotExistException(Exception):
    """Exception raised when an asset pair does not exist.

    :param msg: Error message.
    :type msg: str
    """

    def __init__(self, msg: str):
        super().__init__(msg)
