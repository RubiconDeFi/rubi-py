from _decimal import Decimal
from typing import Optional

from eth_typing import ChecksumAddress


class Approval:
    """Class representing an ERC20 approval.

    :param token: The token being approved
    :type token: str
    :param amount: The approval amount
    :type amount: Decimal
    :param spender: The spender being approved
    :type: spender: Optional[ChecksumAddress]
    """

    def __init__(self, token: str, amount: Decimal, spender: Optional[ChecksumAddress]):
        """constructor method."""
        self.token = token
        self.amount = amount
        self.spender = spender

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class RubiconMarketApproval(Approval):
    """A subclass for a RubiconMarket approval"""

    def __init__(self, token: str, amount: Decimal):
        """constructor method."""
        super().__init__(token=token, amount=amount, spender=None)


class RubiconRouterApproval(Approval):
    """A subclass for a RubiconRouter approval"""

    def __init__(self, token: str, amount: Decimal):
        """constructor method."""
        super().__init__(token=token, amount=amount, spender=None)


class ApprovalEvent(Approval):
    """A Subclass for approval events."""

    def __init__(
        self,
        token: str,
        amount: Decimal,
        spender: ChecksumAddress,
        source: ChecksumAddress,
    ):
        """constructor method."""
        super().__init__(token=token, amount=amount, spender=spender)

        self.source = source


class Transfer:
    """Class representing an ERC20 transfer.

    :param token: The token being transferred
    :type token: str
    :param amount: The transfer amount
    :type amount: Decimal
    :param recipient: The recipient of the transfer
    :type: recipient: ChecksumAddress
    """

    def __init__(self, token: str, amount: Decimal, recipient: ChecksumAddress):
        """constructor method."""
        self.token = token
        self.amount = amount
        self.recipient = recipient

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class TransferEvent(Transfer):
    """A Subclass for transfer events."""

    def __init__(
        self,
        token: str,
        amount: Decimal,
        recipient: ChecksumAddress,
        source: ChecksumAddress,
    ):
        """constructor method."""
        super().__init__(token=token, amount=amount, recipient=recipient)

        self.source = source
