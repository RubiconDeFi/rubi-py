from typing import Optional, Tuple, List

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams

from rubi.contracts.base_contract import BaseContract


class RubiconRouter(BaseContract):
    """This class represents the RubiconRouter.sol contract.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
    ) -> None:
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
        )

    ######################################################################
    # read calls
    ######################################################################

    # getMakerBalance(baseToken (address), tokens (List[address]), maker (address))
    # -> (uint256 balanceInBook, uint256 balance)
    def get_maker_balance(
        self,
        base_token: ChecksumAddress,
        tokens: List[ChecksumAddress],
        maker: ChecksumAddress,
    ) -> Tuple[int, int]:
        """Iterates through all the base_token/tokens[i] offers of the maker and returns the balance of the base_token
        in the book and the balance of the base token.

        :param base_token: The address of the base token.
        :type base_token: ChecksumAddress
        :param tokens: A list of all the tokens to calculate the balance of
        :type tokens: List[ChecksumAddress]
        :param maker: The address of the maker to fet the balance for
        :type maker: ChecksumAddress
        :return: balance in book, total token balance
        :rtype: Tuple[int, int]
        """

        return self.contract.functions.getMakerBalance(base_token, tokens, maker).call()

    # getMakerBalanceInPair(asset (address), quote (address), maker (address)) -> (uint256 balance)
    def get_maker_balance_in_pair(
        self,
        asset: ChecksumAddress,
        quote: ChecksumAddress,
        maker: ChecksumAddress,
    ) -> int:
        """Retrieves the balance of a specific maker for a given asset/quote pair.

        :param asset: The address of the asset token.
        :type asset: ChecksumAddress
        :param quote: The address of the quote token.
        :type quote: ChecksumAddress
        :param maker: The address of the maker.
        :type maker: ChecksumAddress
        :return: The balance of the maker in the specified asset/quote pair.
        :rtype: int
        """

        return self.contract.functions.getMakerBalanceInPair(asset, quote, maker).call()

    # getBookFromPair(asset (address), quote (address)) -> (uint256[3][] asks, uint256[3][] bids)
    def get_book_from_pair(
        self,
        asset: ChecksumAddress,
        quote: ChecksumAddress,
    ) -> Tuple[List[List[int]], List[List[int]]]:
        """Retrieves the order book for a specific asset/quote pair.

        :param asset: The address of the asset token.
        :type asset: ChecksumAddress
        :param quote: The address of the quote token.
        :type quote: ChecksumAddress
        :return: A tuple containing two lists: asks and bids. Each list contains a sublist of length 3, representing
            the order book entries in the following format (pay_amt, buy_amt, id). The asks list represents the orders
            selling the asset, while the bids list represents the orders buying the asset.
        :rtype: Tuple[List[List[int]], List[List[int]]]
        """

        return self.contract.functions.getBookFromPair(asset, quote).call()

    # getBookDepth(tokenIn (address), tokenOut (address)) -> (uint256 depth, uint256 bestOfferID)
    def get_book_depth(
        self, token_in: ChecksumAddress, token_out: ChecksumAddress
    ) -> Tuple[int, int]:
        """Retrieves the depth of one side of the order book for a specific token pair along with the id of the best
        offer.

        :param token_in: The address of the quote.
        :type token_in: ChecksumAddress
        :param token_out: The address of the asset.
        :type token_out: ChecksumAddress
        :return: A tuple containing the depth of the order book and the ID of the best offer for token_out/token_in.
        :rtype: Tuple[int, int]
        """

        return self.contract.functions.getBookDepth(token_in, token_out).call()

    # getBestOfferAndInfo(asset (address), quote (address)) -> (uint256 id, uint256, address, uint256, address)
    def get_best_offer_and_info(
        self, asset: ChecksumAddress, quote: ChecksumAddress
    ) -> Tuple[int, int, ChecksumAddress, int, ChecksumAddress]:
        """Retrieves the information and id of the best offer for a specific asset/quote pair.

        :param asset: The address of the asset token.
        :type asset: ChecksumAddress
        :param quote: The address of the quote token.
        :type quote: ChecksumAddress
        :return: A tuple containing the ID of the best offer, the pay_amt, the address of the pay_gem,
            the buy_amt, and the address of the buy_gem.
        :rtype: Tuple[int, int, ChecksumAddress, int, ChecksumAddress]
        """

        return self.contract.functions.getBestOfferAndInfo(asset, quote).call()

    # getExpectedSwapFill(pay_amt (uint256), buy_amt_min (uint256), route (address[])) -> (uint256 amount)
    def get_expected_swap_fill(
        self, pay_amt: int, buy_amt_min: int, route: List[ChecksumAddress]
    ) -> int:
        """Estimates the expected amount including fees when swapping the specified payment amount using the specified
        route. reverts with an exception if the swap cannot achieve the buy_amt_min

        :param pay_amt: The payment amount.
        :type pay_amt: int
        :param buy_amt_min: The minimum buy amount.
        :type buy_amt_min: int
        :param route: The route of addresses representing the swap path.
        :type route: List[ChecksumAddress]
        :return: The estimated swap amount including fees.
        :rtype: int
        """

        return self.contract.functions.getExpectedSwapFill(
            pay_amt, buy_amt_min, route
        ).call()

    # getExpectedMultiswapFill(pay_amts (uint256[]), buy_amt_mins (uint256[]), routes (address[][]))
    # -> (uint256 amount)
    def get_expected_multiswap_fill(
        self,
        pay_amts: List[int],
        buy_amt_mins: List[int],
        routes: List[List[ChecksumAddress]],
    ) -> int:
        """Estimates the expected amount including fees when swapping multiple specified payment amount using multiple
        specified routes. reverts with an exception if the multiswap cannot achieve the buy_amt_mins along each route

        :param pay_amts: The list of payment amounts for each swap.
        :type pay_amts: List[int]
        :param buy_amt_mins: The list of minimum buy amounts for each swap.
        :type buy_amt_mins: List[int]
        :param routes: The list of routes, where each route is a list of addresses representing the swap path.
        :type routes: List[List[ChecksumAddress]]
        :return: The estimated multi-swap amount.
        :rtype: int
        """

        return self.contract.functions.getExpectedMultiswapFill(
            pay_amts, buy_amt_mins, routes
        ).call()

    # checkClaimAllUserBonusTokens(address user, address[] targetBathTokens, address token)
    # -> (uint256 earnedAcrossPools)
    def check_claim_all_user_bonus_tokens(
        self,
        user: ChecksumAddress,
        target_bath_tokens: List[ChecksumAddress],
        token: ChecksumAddress,
    ) -> int:
        """Checks the all bonus tokens that can be claimed by a user earned across all specified rubicon pools.

        :param user: The address of the user.
        :type user: ChecksumAddress
        :param target_bath_tokens: The list of target bath tokens to claim bonus from.
        :type target_bath_tokens: List[ChecksumAddress]
        :param token: The address of the token for which the bonus is claimed.
        :type token: ChecksumAddress
        :return: The total amount earned across all pools.
        :rtype: int
        """

        return self.contract.functions.checkClaimAllUserBonusTokens(
            user, target_bath_tokens, token
        ).call()

    ######################################################################
    # write calls
    ######################################################################

    # multiswap(address[][] routes, uint256[] pay_amts, uint256[] buy_amts_min, address to) -> bool
    def multiswap(
        self,
        routes: List[List[ChecksumAddress]],
        pay_amts: List[int],
        buy_amts_min: List[int],
        to: ChecksumAddress,
        wallet: ChecksumAddress,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> Optional[TxParams]:
        """Construct a transaction to  a multiple swaps for the specified payment amounts using the specified routes.
        Reverts with an exception if any of the swaps cannot achieve the buy_amt_min along the specified route.

        :param routes: The list of routes, where each route is a list of addresses representing the swap path.
        :type routes: List[List[ChecksumAddress]]
        :param pay_amts: The list of payment amounts for each swap.
        :type pay_amts: List[int]
        :param buy_amts_min: The list of minimum buy amounts for each swap.
        :type buy_amts_min: List[int]
        :param to: The address of the recipient.
        :type to: ChecksumAddress
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
        :param nonce: Nonce of the transaction. Defaults to calling the chain state to get the nonce.
            (optional, default is None).
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: Max fee that can be paid for gas. Defaults to max_priority_fee (from chain)
            + (2 * base fee per gas of latest block) (optional, default is None).
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: Max priority fee that can be paid for gas. Defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None).
        :type max_priority_fee_per_gas: Optional[int]
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """

        multiswap = self.contract.functions.multiswap(
            routes, pay_amts, buy_amts_min, to
        )

        return self._construct_transaction(
            instantiated_contract_function=multiswap,
            wallet=wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # swap(uint256 pay_amt, uint256 buy_amt_min, address[] memory route, address to) -> uint256
    def swap(
        self,
        pay_amt: int,
        buy_amt_min: int,
        route: List[ChecksumAddress],
        to: ChecksumAddress,
        wallet: ChecksumAddress,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> Optional[TxParams]:
        """Construct a transaction to perform a swap operation with the specified payment amount using the specified
        route paying out to the recipient. Reverts if the swap does not result in the buy_min_amount.

        :param pay_amt: The payment amount.
        :type pay_amt: int
        :param buy_amt_min: The minimum buy amount.
        :type buy_amt_min: int
        :param route: The route, represented as a list of addresses representing the swap path.
        :type route: List[ChecksumAddress]
        :param to: The address of the recipient.
        :type to: ChecksumAddress
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
        :param nonce: Nonce of the transaction. Defaults to calling the chain state to get the nonce.
            (optional, default is None).
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: Max fee that can be paid for gas. Defaults to max_priority_fee (from chain)
            + (2 * base fee per gas of latest block) (optional, default is None).
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: Max priority fee that can be paid for gas. Defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None).
        :type max_priority_fee_per_gas: Optional[int]
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """

        swap = self.contract.functions.swap(pay_amt, buy_amt_min, route, to)

        return self._construct_transaction(
            instantiated_contract_function=swap,
            wallet=wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # TODO
    #  sellAllAmountForETH
    #  sellAllAmountWithETH
    #  buyAllAmountWithETH
    #  buyAllAmountForETH
    #  swapWithETH
    #  swapForETH
    #  offerWithETH
    #  offerForETH
    #  cancelForETH
    #  depositWithETH
    #  withdrawForETH
