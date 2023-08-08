from _decimal import Decimal
from typing import Optional

from eth_typing import ChecksumAddress


class Approval:
    def __init__(self, token: str, amount: Decimal, spender: Optional[ChecksumAddress]):
        self.token = token
        self.amount = amount
        self.spender = spender

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class RubiconMarketApproval(Approval):
    def __init__(self, token: str, amount: Decimal):
        super().__init__(token=token, amount=amount, spender=None)


class RubiconRouterApproval(Approval):
    def __init__(self, token: str, amount: Decimal):
        super().__init__(token=token, amount=amount, spender=None)


class ApprovalEvent(Approval):
    def __init__(
        self,
        token: str,
        amount: Decimal,
        spender: ChecksumAddress,
        source: ChecksumAddress,
    ):
        super().__init__(token=token, amount=amount, spender=spender)

        self.source = source


class Transfer:
    def __init__(self, token: str, amount: Decimal, recipient: ChecksumAddress):
        self.token = token
        self.amount = amount
        self.recipient = recipient

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class TransferEvent(Transfer):
    def __init__(
        self,
        token: str,
        amount: Decimal,
        recipient: ChecksumAddress,
        source: ChecksumAddress,
    ):
        super().__init__(token=token, amount=amount, recipient=recipient)

        self.source = source
