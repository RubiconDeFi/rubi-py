from typing import Optional, Tuple, List

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract

from rubi.contracts.base_contract import BaseContract, ContractType
from rubi.contracts.contract_types import TransactionReceipt
from rubi.network import Network


class RubiconMarket(BaseContract):
    """This class represents the RubiconMarket.sol contract and by default has read functionality.
    If a wallet and key are passed in instantiation then this class can also be used to write to the contract instance.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    :param wallet: a wallet address of the signer (optional, default is None)
    :type wallet: Optional[ChecksumAddress]
    :param key: the private key of the signer (optional, default is None)
    :type key: Optional[str]
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
        contract_type: ContractType = ContractType.RUBICON_MARKET,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ) -> None:
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
            contract_type=ContractType.RUBICON_MARKET,
            wallet=wallet,
            key=key,
        )

    @classmethod
    def from_network(
        cls,
        network: Network,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ) -> "RubiconMarket":
        """Create a RubiconMarket instance based on a Network instance.

        :param network: A Network instance.
        :type network: Network
        :param wallet: Optional wallet address to use for interacting with the contract (optional, default is None).
        :type wallet: Optional[ChecksumAddress]
        :param key: Optional private key for the wallet (optional, default is None).
        :type key: Optional[str]
        :return: A RubiconMarket instance based on the Network instance.
        :rtype: RubiconMarket
        """
        return cls.from_address_and_abi(
            w3=network.w3,
            address=network.rubicon.market.address,
            contract_abi=network.rubicon.market.abi,
            contract_type=ContractType.RUBICON_MARKET,
            wallet=wallet,
            key=key,
        )

    ######################################################################
    # read calls
    ######################################################################

    # makerFee() -> (uint265)
    def get_maker_fee(self) -> int:
        """Returns the maker fee on Rubicon

        :return: the maker fee
        :rtype: int
        """

        return self.contract.functions.makerFee().call()

    # getOffer(id (uint256)) -> (uint256, address, uint256, address)
    def get_offer(self, id: int) -> Tuple[int, ChecksumAddress, int, ChecksumAddress]:
        """Returns the offer associated with the provided id

        :param id: the id of the offer being queried
        :type id: int
        :return: a description of the offer as (pay_amt, pay_gem, buy_amt, buy_gem)
        :rtype: Tuple[int, ChecksumAddress, int, ChecksumAddress]
        """
        return self.contract.functions.getOffer(id).call()

    # getMinSell(pay_gem (address)) -> uint256
    def get_min_sell(self, pay_gem: ChecksumAddress) -> int:
        """Returns the minimum sell amount for an offer

        :param pay_gem: the address of the token being sold by the maker
        :type pay_gem: str
        :return: the minimum amount of pay_gem that can be sold in an offer
        :rtype: int
        """

        return self.contract.functions.getMinSell(pay_gem).call()

    # getBestOffer(sell_gem (address), buy_gem (address)) -> uint256
    def get_best_offer(
        self, sell_gem: ChecksumAddress, buy_gem: ChecksumAddress
    ) -> int:
        """Returns the best offer for the given pair of tokens

        :param sell_gem: the address of the token being sold by the maker
        :type sell_gem: str
        :param buy_gem: the address of the token being bought by the maker
        :type buy_gem: str
        :return: the id of the best offer on the book, None if there is no offer on the book
        :rtype: int
        """

        return self.contract.functions.getBestOffer(sell_gem, buy_gem).call()

    # getWorseOffer(id (uint256)) -> uint256
    def get_worse_offer(self, id: int) -> int:
        """Returns the id of the offer that is worse than the given offer

        :param id: the id of the offer
        :type id: int
        :return: the id of the offer that is worse than the given offer, none if there is no worse offer
        :rtype: int
        """

        return self.contract.functions.getWorseOffer(id).call()

    # getBetterOffer(id (uint256)) -> uint256
    def get_better_offer(self, id: int) -> int:
        """Returns the id of the offer that is better than the given offer

        :param id: the id of the offer
        :type id: int
        :return: the id of the offer that is better than the given offer, none if there is no better offer
        :rtype: int
        """

        return self.contract.functions.getBetterOffer(id).call()

    # getOfferCount(sell_gem (address), buy_gem (address)) -> uint256
    def get_offer_count(
        self, sell_gem: ChecksumAddress, buy_gem: ChecksumAddress
    ) -> int:
        """Returns the number of offers for a token pair

        :param sell_gem: the address of the token being sold by the maker
        :type sell_gem: ChecksumAddress
        :param buy_gem: the address of the token being bought by the maker
        :type buy_gem: ChecksumAddress
        :return: the number of offers for a token pair, None if there are no offers for the token pair
        :rtype: int
        """

        return self.contract.functions.getOfferCount(sell_gem, buy_gem).call()

    # calculateFees(amount (uint256), isPay (bool)) -> uint256
    def calculate_fees(self, amount: int) -> int:
        """Calculate fees on an amount

        :param amount: the address of the token being bought
        :type amount: int
        :return: the calculated fees on the amount
        :rtype: int
        """
        return self.contract.functions.calculateFees(amount, True).call()

    # getBuyAmountWithFee(buy_gem (address), pay_gem (address), pay_amt (unit256)) ->
    # (buy_amt (uint256), approvalAmount (uint256))
    def get_buy_amount_with_fee(
        self, buy_gem: ChecksumAddress, pay_gem: ChecksumAddress, pay_amt: int
    ) -> Tuple[int, int]:
        """Returns the amount of the buy_gem you will receive if you send the pay_amt to the contract along with the
        amount to approve for the transaction

        :param buy_gem: the address of the token being bought
        :type buy_gem: ChecksumAddress
        :param pay_gem: the address of the token being sold
        :type pay_gem: ChecksumAddress
        :param pay_amt: the amount of the token being sold to receive the token being bought
        :type pay_amt: int
        :return: (buy_amt, approvalAmount) the amount of tokens that will be received and the amount to approve for the
            transaction
        :rtype: Tuple[int, int]
        """
        return self.contract.functions.getBuyAmountWithFee(
            buy_gem, pay_gem, pay_amt
        ).call()

    # getPayAmountWithFee(pay_gem (address), buy_gem (address), buy_amt (unit256)) ->
    # (buy_amt (uint256), approvalAmount (uint256))
    def get_pay_amount_with_fee(
        self, pay_gem: ChecksumAddress, buy_gem: ChecksumAddress, buy_amt: int
    ) -> Tuple[int, int]:
        """Returns the amount of the pay_gem you will need to pay to the contract to receive the buy_amt along with the
        amount to approve for the transaction

        :param buy_gem: the address of the token being bought
        :type buy_gem: ChecksumAddress
        :param pay_gem: the address of the token being sold
        :type pay_gem: ChecksumAddress
        :param buy_amt: the amount of the token being bought
        :type buy_amt: int
        :return: (pay_amt, approvalAmount) the amount of tokens that will be paid and the amount to approve for the
            transaction
        :rtype: Tuple[int, int]
        """
        return self.contract.functions.getPayAmountWithFee(
            buy_gem, pay_gem, buy_amt
        ).call()

    ######################################################################
    # write calls
    ######################################################################

    # offer offer(pay_amt (uint256), pay_gem (address), buy_amt (uint256), buy_gem (address), pos (uint256),
    # owner (address), recipient (address)) -> uint256
    def offer(
        self,
        pay_amt: int,
        pay_gem: ChecksumAddress,
        buy_amt: int,
        buy_gem: ChecksumAddress,
        pos: int = 0,
        rounding: bool = False,
        owner: Optional[ChecksumAddress] = None,
        recipient: Optional[ChecksumAddress] = None,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Make a new offer to buy the buy_amt of the buy_gem token in exchange for the pay_amt of the pay_gem token

        :param pay_amt: the amount of the token being sold
        :type pay_amt: int
        :param pay_gem: the address of the token being sold
        :type pay_gem: ChecksumAddress
        :param buy_amt: the amount of the token being bought
        :type buy_amt: int
        :param buy_gem: the address of the token being bought
        :type buy_gem: ChecksumAddress
        :param pos: position of the offer in the linked list, default to 0 unless the maker knows the position they want
            to insert the offer at
        :type pos: int
        :param rounding: add rounding to match "close enough" orders, defaults to False
        :type: rounding: bool
        :param owner: the owner of the offer, defaults to the wallet that was provided in instantiating this class.
            (optional, default is None)
        :type owner: Optional[ChecksumAddress]
        :param recipient: the recipient of the offer's fill, defaults to the wallet that was provided in instantiating
            this class (optional, default is None)
        :type recipient: Optional[ChecksumAddress]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """

        if not self.signing_permissions:
            raise Exception(
                f"cannot write transaction without signing rights. "
                f"re-instantiate {self.__class__} with a wallet and private key"
            )

        owner = owner if owner is not None else self.wallet
        recipient = recipient if recipient is not None else self.wallet

        offer = self.contract.functions.offer(
            pay_amt, pay_gem, buy_amt, buy_gem, pos, rounding, owner, recipient
        )

        return self._default_transaction_handler(
            instantiated_contract_function=offer,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # cancel(id (uint256)) -> bool
    def cancel(
        self,
        id: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Cancel an offer by offer id

        :param id: the id of the offer to cancel
        :type id: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """

        cancel = self.contract.functions.cancel(id)

        return self._default_transaction_handler(
            instantiated_contract_function=cancel,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # batchOffer(payAmts (uint[]), payGems (address[]), buyAmts (uint[]), buyGems (address[])) -> uint256[]
    def batch_offer(
        self,
        pay_amts: List[int],
        pay_gems: List[ChecksumAddress],
        buy_amts: List[int],
        buy_gems: List[ChecksumAddress],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Batch the placement of a set of offers in one transaction

        :param pay_amts: the amounts of the token being sold
        :type pay_amts: List[int]
        :param pay_gems: the addresses of the tokens being sold
        :type pay_gems: List[ChecksumAddress]
        :param buy_amts: the amounts of the token being bought
        :type buy_amts: List[int]
        :param buy_gems: the addresses of the tokens being bought
        :type buy_gems: List[ChecksumAddress]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        if not (len(pay_amts) == len(pay_gems) == len(buy_amts) == len(buy_gems)):
            raise Exception(
                "mismatches lengths in pay_amts, pay_gems, buy_amts and buy_gems"
            )

        batch_offer = self.contract.functions.batchOffer(
            pay_amts, pay_gems, buy_amts, buy_gems
        )

        return self._default_transaction_handler(
            instantiated_contract_function=batch_offer,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # batchCancel (ids (uint256[])) -> bool[]
    def batch_cancel(
        self,
        ids: List[int],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Cancel a set offer by offer id in a single transaction

        :param ids: the ids of the offers to cancel
        :type ids: List[int]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        cancels = self.contract.functions.batchCancel(ids)

        return self._default_transaction_handler(
            instantiated_contract_function=cancels,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # batchRequote (ids (uint256[]), payAmts (uint[]), payGems (address[]), buyAmts (uint[]), buyGems (address[]))
    # -> uint256[]
    def batch_requote(
        self,
        ids: List[int],
        pay_amts: List[int],
        pay_gems: List[ChecksumAddress],
        buy_amts: List[int],
        buy_gems: List[ChecksumAddress],
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Batch update a set of offers in a single transaction and return a list of new offer ids

        :param ids: the ids of the offers to cancel
        :type ids: List[int]
        :param pay_amts: the amounts of the token being sold
        :type pay_amts: List[int]
        :param pay_gems: the addresses of the tokens being sold
        :type pay_gems: List[ChecksumAddress]
        :param buy_amts: the amounts of the token being bought
        :type buy_amts: List[int]
        :param buy_gems: the addresses of the tokens being bought
        :type buy_gems: List[ChecksumAddress]
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """

        batch_requote = self.contract.functions.batchRequote(
            ids, pay_amts, pay_gems, buy_amts, buy_gems
        )

        return self._default_transaction_handler(
            instantiated_contract_function=batch_requote,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # sellAllAmount(pay_gem (address), pay_amt (uint256), buy_gem (address), min_fill_amount (uint256)) -> uint256
    def sell_all_amount(
        self,
        pay_gem: ChecksumAddress,
        pay_amt: int,
        buy_gem: ChecksumAddress,
        min_fill_amount: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Sell the pay_amt of the pay_gem token in exchange for buy_gem, on the condition that you receive at least the
        min_fill_amount of the buy_gem token

        :param pay_gem: the address of the tokens being sold
        :type pay_gem: ChecksumAddress
        :param pay_amt: the amount of the token being sold
        :type pay_amt: int
        :param buy_gem: the address of the tokens being bought
        :type buy_gem: ChecksumAddress
        :param min_fill_amount: minimum amount of the buy_gem token you want to receive
        :type min_fill_amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        sell_all_amount = self.contract.functions.sellAllAmount(
            pay_gem, pay_amt, buy_gem, min_fill_amount
        )

        return self._default_transaction_handler(
            instantiated_contract_function=sell_all_amount,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # buyAllAmount(buy_gem (address), buy_amt (uint256), pay_gem (address), max_fill_amount (uint256)) -> uint256
    def buy_all_amount(
        self,
        buy_gem: ChecksumAddress,
        buy_amt: int,
        pay_gem: ChecksumAddress,
        max_fill_amount: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Buy the buy_amt of the buy_gem token in exchange for pay_gem, on the condition that it does not exceed the
        max_fill_amount of the pay_gem token

        :param buy_gem: the address of the tokens being bought
        :type buy_gem: ChecksumAddress
        :param buy_amt: the amount of the token being bought
        :type buy_amt: int
        :param pay_gem: the address of the tokens being sold
        :type pay_gem: ChecksumAddress
        :param max_fill_amount: maximum amount of the pay_gem token you want to pay
        :type max_fill_amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce.
            (optional, default is None)
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        buy_all_amount = self.contract.functions.buyAllAmount(
            buy_gem, buy_amt, pay_gem, max_fill_amount
        )

        return self._default_transaction_handler(
            instantiated_contract_function=buy_all_amount,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
