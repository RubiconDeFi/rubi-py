from _decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import TxParams

from rubi.contracts.base_contract import BaseContract


class ERC20(BaseContract):
    """this class represents a contract that implements the ERC20 standard.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
    ):
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
        )

        with ThreadPoolExecutor() as executor:
            name_future = executor.submit(self.name)
            symbol_future = executor.submit(self.symbol)
            decimals_future = executor.submit(self.decimals)

        self.name = name_future.result()
        self.symbol = symbol_future.result()
        self.decimals = decimals_future.result()
        self.address = self.contract.address

    ######################################################################
    # read calls
    ######################################################################

    # allowance(owner (address), spender (address)) -> uint256
    def allowance(self, owner: ChecksumAddress, spender: ChecksumAddress) -> int:
        """Reads the allowance of the spender from the owner for the erc20 contract

        :param owner: address that owns the erc20 tokens
        :type owner: ChecksumAddress
        :param spender: address that is allowed to spend the erc20 tokens
        :type spender: ChecksumAddress
        :return: the allowance of the spender from the owner for the contract, in the integer representation of the
            token
        :rtype: int
        """

        return self.contract.functions.allowance(owner, spender).call()

    # balanceOf(account (address)) -> uint256
    def balance_of(self, account: ChecksumAddress) -> int:
        """Reads the erc20 balance of the account

        :param account: the address of the account to read the balance of
        :type account: str
        :return: the balance of the account, in the integer representation of the token
        :rtype: int
        """

        return self.contract.functions.balanceOf(account).call()

    # totalSupply() -> uint256
    def total_supply(self) -> int:
        """Reads the total supply of the erc20 token

        :return: the total supply of the erc20 token, in the integer representation of the token
        :rtype: int
        """

        return self.contract.functions.totalSupply().call()

    # decimals() -> uint256
    def decimals(self) -> int:
        """Reads the number of decimals of the erc20 token - warning this is not a constant function, so it may result
        in an error in its current implementation

        :return: the number of decimals of the erc20 token
        :rtype: int
        """

        return self.contract.functions.decimals().call()

    # name() -> string
    def name(self) -> str:
        """Reads the name of the erc20 token

        :return: the name of the erc20 token
        :rtype: str
        """

        return self.contract.functions.name().call()

    # symbol() -> string
    def symbol(self) -> str:
        """Reads the symbol of the erc20 token

        :return: the symbol of the erc20 token
        :rtype: str
        """

        return self.contract.functions.symbol().call()

    ######################################################################
    # write calls
    ######################################################################

    # approve(spender (address), amount (uint256)) -> bool
    def approve(
        self,
        spender: ChecksumAddress,
        amount: int,
        wallet: ChecksumAddress,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> Optional[TxParams]:
        """Construct an approval transaction which approved the spender to spend the amount of the erc20 token.

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param amount: amount of the erc20 token to approve the spender to spend
        :type amount: int
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
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
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """
        approve = self.contract.functions.approve(spender, amount)

        return self._construct_transaction(
            instantiated_contract_function=approve,
            wallet=wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # transfer(recipient (address), amount (uint256)) -> bool
    def transfer(
        self,
        recipient: ChecksumAddress,
        amount: int,
        wallet: ChecksumAddress,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> Optional[TxParams]:
        """Construct a transfer transaction to the recipient for the amount.

        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit for the transaction. If None is passed then w3.eth.estimate_gas is used.
        :type gas: Optional[int]
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
            max_priority_fee (from chain) + (2 * base fee per gas of latest block) (optional, default is None)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
            estimate the max_priority_fee_per_gas (optional, default is None)
        :type max_priority_fee_per_gas: Optional[int]
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """
        transfer = self.contract.functions.transfer(recipient, amount)

        return self._construct_transaction(
            instantiated_contract_function=transfer,
            wallet=wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # transferFrom(sender (address), recipient (address), amount (uint256)) -> bool
    def transfer_from(
        self,
        sender: ChecksumAddress,
        recipient: ChecksumAddress,
        amount: int,
        wallet: ChecksumAddress,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> Optional[TxParams]:
        """Construct a transfer from transaction from the sender to the recipient for the amount.

        :param sender: address of the sender
        :type sender: ChecksumAddress
        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param wallet: The wallet address to use for interacting with the contract.
        :type wallet: ChecksumAddress
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
        :return: The built transaction. The result is None if the transaction fails to build
        :rtype: Optional[TxParams]
        """

        transfer_from = self.contract.functions.transferFrom(sender, recipient, amount)

        return self._construct_transaction(
            instantiated_contract_function=transfer_from,
            wallet=wallet,
            nonce=nonce,
            gas=gas,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    ######################################################################
    # helper methods
    ######################################################################

    def to_decimal(self, number: int) -> Decimal:
        """Converts an integer representation of the token to a Decimal representation of the token by dividing the
        integer by 10 to the power of the number of decimals of the token

        :param number: the integer representation of the token
        :type number: int
        :return: the Decimal representation of the token
        :rtype: Decimal
        """

        if number == 0:
            return Decimal("0")
        else:
            return Decimal(number) / Decimal(10**self.decimals)

    def to_integer(self, number: Decimal) -> int:
        """Converts a Decimal representation of the token to an integer representation of the token by multiplying the
        float by 10 to the power of the number of decimals of the token

        :param number: the Decimal representation of the token
        :type number: Decimal
        :return: the integer representation of the token
        :rtype: int
        """

        if number == Decimal("0"):
            return 0
        else:
            return int(number * (10**self.decimals))

    def max_approval_amount(self) -> Decimal:
        """return the max uint256 token approval amount. Note: this is not very secure and if you give this approval you
        should revoke it when you are done!

        :return: the max approval amount of a uint256 token in Decimal representation
        :rtype: Decimal
        """
        max_uint256 = (
            "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        )

        return self.to_decimal(number=int(max_uint256, base=16))
