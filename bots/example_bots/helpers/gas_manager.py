from _decimal import Decimal

from rubi import TransactionReceipt


# TODO: this needs to be reworked as it currently isn't very useful
class GasManager:

    # TODO: add eth price to track gas price in dollar terms not in eth terms
    def __init__(self, allowed_fluctuation: Decimal, alpha: Decimal):
        self.allowed_fluctuation = allowed_fluctuation
        self.alpha = alpha

        self.eth_price: Decimal = Decimal("2000")

        self.gas_used_ema = None
        self.transaction_cost_ema = None

    def add_transaction(self, transaction: TransactionReceipt):
        self.transaction_cost_ema = (
            transaction.transaction_cost_in_eth * self.alpha
        ) + (self.transaction_cost_ema * (Decimal("1") - self.alpha))

    def is_acceptable_cost(self, transaction_receipt: TransactionReceipt) -> bool:
        return (
            self.calculate_difference_from_ema(transaction_receipt=transaction_receipt)
            < self.allowed_fluctuation
        )

    def calculate_difference_from_ema(
        self, transaction_receipt: TransactionReceipt
    ) -> Decimal:
        transaction_cost = transaction_receipt.transaction_cost_in_eth

        if self.transaction_cost_ema:
            return (
                transaction_cost - self.transaction_cost_ema
            ) / self.transaction_cost_ema
        else:
            return Decimal("0")

    def transaction_cost_estimate(self) -> Decimal:
        if self.transaction_cost_ema is None:
            return Decimal("0.4")

        return self.transaction_cost_ema * self.eth_price
