import json
from typing import Optional

from eth_account.datastructures import SignedTransaction
from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import ABI

from rubi.contracts_v2.helper.base_contract import BaseContract
from rubi.network import Network


class ERC20(BaseContract):
    """this class represents a contract that implements the ERC20 standard. it is used to read the contract instance.
    if a wallet and key are passed in instantiation then this class can also be used to write to the contract instance.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    :param wallet: a wallet address of the signer (optional)
    :type wallet: Optional[ChecksumAddress]
    :param key: the private key of the signer (optional)
    :type key: Optional[str]
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ):
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
            wallet=wallet,
            key=key
        )

        self.name = self.name()
        self.symbol = self.symbol()
        self.decimal = self.decimals()

    @classmethod
    def from_network(
        cls,
        name: str,
        network: Network,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ) -> "ERC20":
        if network.token_addresses[name] is None:
            raise Exception(f"{name} in not a valid token according to the network config.")

        abi: ABI

        try:
            with open("network_config/ERC20.json") as f:
                abi = json.load(f)

        except FileNotFoundError:
            with open("../../network_config/ERC20.json") as f:
                abi = json.load(f)

        return cls.from_address_and_abi(
            w3=network.w3,
            address=network.token_addresses[name],
            contract_abi=abi,
            wallet=wallet,
            key=key
        )

    ######################################################################
    # read calls
    ######################################################################

    # allowance(owner (address), spender (address)) -> uint256
    def allowance(self, owner: ChecksumAddress, spender: ChecksumAddress) -> int:
        """reads the allowance of the spender from the owner for the erc20 contract

        :param owner: address that owns the erc20 tokens
        :type owner: str
        :param spender: address that is allowed to spend the erc20 tokens
        :type spender: str
        :return: the allowance of the spender from the owner for the contract, in the integer representation of the
        token
        :rtype: int
        """

        return self.contract.functions.allowance(owner, spender).call()

    # balanceOf(account (address)) -> uint256
    def balance_of(self, account: ChecksumAddress) -> int:
        """reads the erc20 balance of the account

        :param account: the address of the account to read the balance of
        :type account: str
        :return: the balance of the account, in the integer representation of the token
        :rtype: int
        """

        return self.contract.functions.balanceOf(account).call()

    # totalSupply() -> uint256
    def total_supply(self) -> int:
        """reads the total supply of the erc20 token

        :return: the total supply of the erc20 token, in the integer representation of the token
        :rtype: int
        """

        return self.contract.functions.totalSupply().call()

    # decimals() -> uint256
    def decimals(self) -> int:
        """reads the number of decimals of the erc20 token - warning this is not a constant function, so it may result
        in an error in its current implementation

        :return: the number of decimals of the erc20 token
        :rtype: int
        """

        return self.contract.functions.decimals().call()

    # name() -> string
    def name(self) -> str:
        """reads the name of the erc20 token

        :return: the name of the erc20 token
        :rtype: str
        """

        return self.contract.functions.name().call()

    # symbol() -> string
    def symbol(self) -> str:
        """reads the symbol of the erc20 token

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
        nonce: Optional[int] = None,
        gas: int = 100000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> bool:
        """approves the spender to spend the amount of the erc20 token from the signer's wallet

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param amount: amount of the erc20 token to approve the spender to spend
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit of the transaction, defaults to a very high estimate made when writing the class
        :type gas: int
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
        max_priority_fee (from chain) + (2 * base fee per gas of latest block)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
        estimate the max_priority_fee_per_gas
        :type max_priority_fee_per_gas: Optional[int]
        :return: the signed transaction
        :rtype: SignedTransaction
        """
        approve = self.contract.functions.approve(spender, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=approve,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    # transfer(recipient (address), amount (uint256)) -> bool
    def transfer(
        self,
        recipient: ChecksumAddress,
        amount: int,
        nonce: Optional[int] = None,
        gas: int = 100000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> bool:
        """transfers the amount of the erc20 token to the recipient

        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit of the transaction, defaults to a very high estimate made when writing the class
        :type gas: int
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
        max_priority_fee (from chain) + (2 * base fee per gas of latest block)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
        estimate the max_priority_fee_per_gas
        :type max_priority_fee_per_gas: Optional[int]
        :return: the signed transaction
        :rtype: SignedTransaction
        """
        transfer = self.contract.functions.transfer(recipient, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=transfer,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    # transferFrom(sender (address), recipient (address), amount (uint256)) -> bool
    def transfer_from(
        self,
        sender: ChecksumAddress,
        recipient: ChecksumAddress,
        amount: int,
        nonce: Optional[int] = None,
        gas: int = 100000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> bool:
        """transfers the amount of the erc20 token from the sender to the recipient

        :param sender: address of the sender
        :type sender: ChecksumAddress
        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit of the transaction, defaults to a very high estimate made when writing the class
        :type gas: int
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
        max_priority_fee (from chain) + (2 * base fee per gas of latest block)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
        estimate the max_priority_fee_per_gas
        :type max_priority_fee_per_gas: Optional[int]
        :return: the signed transaction
        :rtype: SignedTransaction
        """

        transfer_from = self.contract.functions.transferFrom(sender, recipient, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=transfer_from,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    # increaseAllowance(spender (address), addedValue (uint256)) -> bool
    def increase_allowance(
        self,
        spender: ChecksumAddress,
        added_value: int,
        nonce: Optional[int] = None,
        gas: int = 100000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> bool:
        """increases the allowance of the spender by the added_value

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param added_value: amount to increase the allowance by, in the integer representation of the erc20 token
        :type added_value: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit of the transaction, defaults to a very high estimate made when writing the class
        :type gas: int
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
        max_priority_fee (from chain) + (2 * base fee per gas of latest block)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
        estimate the max_priority_fee_per_gas
        :type max_priority_fee_per_gas: Optional[int]
        :return: the signed transaction
        :rtype: SignedTransaction
        """
        increase_allowance = self.contract.functions.increaseAllowance(spender, added_value)

        return self._default_transaction_handler(
            instantiated_contract_function=increase_allowance,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    # decreaseAllowance(spender (address), subtractedValue (uint256)) -> bool
    def decrease_allowance(
        self,
        spender: ChecksumAddress,
        subtracted_value: int,
        nonce: Optional[int] = None,
        gas: int = 100000,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None
    ) -> bool:
        """decreases the allowance of the spender by the subtracted_value

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param subtracted_value: amount to decrease the allowance by, in the integer representation of the erc20 token
        :type subtracted_value: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: Optional[int]
        :param gas: gas limit of the transaction, defaults to a very high estimate made when writing the class
        :type gas: int
        :param max_fee_per_gas: max fee that can be paid for gas, defaults to
        max_priority_fee (from chain) + (2 * base fee per gas of latest block)
        :type max_fee_per_gas: Optional[int]
        :param max_priority_fee_per_gas: max priority fee that can be paid for gas, defaults to calling the chain to
        estimate the max_priority_fee_per_gas
        :type max_priority_fee_per_gas: Optional[int]
        :return: the signed transaction
        :rtype: SignedTransaction
        """
        decrease_allowance = self.contract.functions.decreaseAllowance(spender, subtracted_value)

        return self._default_transaction_handler(
            instantiated_contract_function=decrease_allowance,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

    ######################################################################
    # helper methods
    ######################################################################

    def to_float(self, number: int) -> float:
        """converts an integer representation of the token to a float representation of the token by dividing the
        integer by 10 to the power of the number of decimals of the token

        :param number: the integer representation of the token
        :type number: int
        :return: the float representation of the token
        :rtype: float
        """

        if number == 0:
            return 0
        else:
            return number / (10 ** self.decimal)

    def to_integer(self, number: float) -> int:
        """converts a float representation of the token to an integer representation of the token by multiplying the
        float by 10 to the power of the number of decimals of the token

        :param number: the float representation of the token
        :type number: float
        :return: the integer representation of the token
        :rtype: int
        """

        if number == 0:
            return 0
        else:
            return int(number * (10 ** self.decimal))
