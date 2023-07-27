import json
import os
from _decimal import Decimal
from typing import Optional

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.types import ABI

from rubi.contracts.base_contract import BaseContract, ContractType
from rubi.contracts.contract_types import TransactionReceipt
from rubi.network import Network


class ERC20(BaseContract):
    """this class represents a contract that implements the ERC20 standard. it is used to read the contract instance.
    if a wallet and key are passed in instantiation then this class can also be used to write to the contract instance.

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
        contract_type: ContractType = ContractType.ERC20,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ):
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
            contract_type=ContractType.ERC20,
            wallet=wallet,
            key=key,
        )

        self.name: str = self.name()
        self.symbol: str = self.symbol()
        self.decimal: int = self.decimals()

    @classmethod
    def from_network(
        cls,
        name: str,
        network: Network,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ) -> "ERC20":
        """Create an ERC20 instance based on a Network instance and token name.

        :param name: The name of the token.
        :type name: str
        :param network: A Network instance.
        :type network: Network
        :param wallet: Optional wallet address to use for interacting with the contract (optional, default is None).
        :type wallet: Optional[ChecksumAddress]
        :param key: Optional private key for the wallet (optional, default is None).
        :type key: Optional[str]
        :return: An ERC20 instance based on the Network instance and token name.
        :rtype: ERC20
        :raises Exception: If the token name does not exist in the network configuration.
        :raises Exception: If the ERC20.json ABI file is not found in the network_config folder.
        """

        if network.token_addresses[name] is None:
            raise Exception(
                f"{name} in not a valid token according to the network config."
            )

        abi: ABI

        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/ERC20.json"

            with open(path) as f:
                abi = json.load(f)

        except FileNotFoundError:
            raise Exception(
                "ERC20.json abi not found. this file should in the network_config folder"
            )

        return cls.from_address_and_abi(
            w3=network.w3,
            address=network.token_addresses[name],
            contract_abi=abi,
            contract_type=ContractType.ERC20,
            wallet=wallet,
            key=key,
        )

    @classmethod
    def from_address(
        cls,
        w3: Web3,
        address: ChecksumAddress,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None,
    ) -> "ERC20":
        """Create an ERC20 instance based on an address and a network connection.

        :param w3: Web3 instance.
        :type w3: Web3
        :param address: The address of the contract.
        :type address: ChecksumAddress
        :param wallet: Optional wallet address to use for interacting with the contract (optional, default is None).
        :type wallet: Optional[ChecksumAddress]
        :param key: Optional private key for the wallet (optional, default is None).
        :type key: Optional[str]
        :return: An ERC20 instance based on the address and network connection.
        :rtype: ERC20
        """

        abi: ABI

        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/ERC20.json"

            with open(path) as f:
                abi = json.load(f)

        except FileNotFoundError:
            raise Exception(
                "ERC20.json abi not found. this file should in the network_config folder"
            )

        return cls.from_address_and_abi(
            w3=w3,
            address=address,
            contract_abi=abi,
            contract_type=ContractType.ERC20,
            wallet=wallet,
            key=key,
        )

    ######################################################################
    # read calls
    ######################################################################

    # allowance(owner (address), spender (address)) -> uint256
    def allowance(self, owner: ChecksumAddress, spender: ChecksumAddress) -> int:
        """Reads the allowance of the spender from the owner for the erc20 contract

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
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Approves the spender to spend the amount of the erc20 token from the signer's wallet

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param amount: amount of the erc20 token to approve the spender to spend
        :type amount: int
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
        approve = self.contract.functions.approve(spender, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=approve,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # transfer(recipient (address), amount (uint256)) -> bool
    def transfer(
        self,
        recipient: ChecksumAddress,
        amount: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Transfers the amount of the erc20 token to the recipient

        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
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
        :return: An object representing the transaction receipt
        :rtype: TransactionReceipt
        """
        transfer = self.contract.functions.transfer(recipient, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=transfer,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # transferFrom(sender (address), recipient (address), amount (uint256)) -> bool
    def transfer_from(
        self,
        sender: ChecksumAddress,
        recipient: ChecksumAddress,
        amount: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Transfers the amount of the erc20 token from the sender to the recipient

        :param sender: address of the sender
        :type sender: ChecksumAddress
        :param recipient: address of the recipient
        :type recipient: ChecksumAddress
        :param amount: amount of the erc20 token to transfer
        :type amount: int
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

        transfer_from = self.contract.functions.transferFrom(sender, recipient, amount)

        return self._default_transaction_handler(
            instantiated_contract_function=transfer_from,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # increaseAllowance(spender (address), addedValue (uint256)) -> bool
    def increase_allowance(
        self,
        spender: ChecksumAddress,
        added_value: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Increases the allowance of the spender by the added_value

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param added_value: amount to increase the allowance by, in the integer representation of the erc20 token
        :type added_value: int
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
        increase_allowance = self.contract.functions.increaseAllowance(
            spender, added_value
        )

        return self._default_transaction_handler(
            instantiated_contract_function=increase_allowance,
            gas=gas,
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

    # decreaseAllowance(spender (address), subtractedValue (uint256)) -> bool
    def decrease_allowance(
        self,
        spender: ChecksumAddress,
        subtracted_value: int,
        nonce: Optional[int] = None,
        gas: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> TransactionReceipt:
        """Decreases the allowance of the spender by the subtracted_value

        :param spender: address of the spender
        :type spender: ChecksumAddress
        :param subtracted_value: amount to decrease the allowance by, in the integer representation of the erc20 token
        :type subtracted_value: int
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
        decrease_allowance = self.contract.functions.decreaseAllowance(
            spender, subtracted_value
        )

        return self._default_transaction_handler(
            instantiated_contract_function=decrease_allowance,
            gas=gas,
            nonce=nonce,
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
            return Decimal(number) / Decimal(10**self.decimal)

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
            return int(number * (10**self.decimal))

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
