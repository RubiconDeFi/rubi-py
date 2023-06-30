from _decimal import Decimal

from event_trading_framework import TransactionResult

# TODO: this needs to be reworked as it currently isn't very useful
class GasManager:

    # TODO: add eth price to track gas price in dollar terms not in eth terms
    def __init__(self, allowed_fluctuation: Decimal, ema_multiplier: Decimal):
        self.allowed_fluctuation = allowed_fluctuation
        self.ema_multiplier = ema_multiplier

        self.eth_price: Decimal = Decimal("2000")

        self.gas_used_ema = None
        self.transaction_cost_ema = None

    def add_transaction(self, transaction: TransactionResult):
        transaction_cost = (
            (transaction.transaction_receipt.effective_gas_price / 10 ** 18) *
            transaction.transaction_receipt.gas_used
        )

        if self.gas_used_ema is None:
            self.gas_used_ema = transaction.transaction_receipt.gas_used
            self.transaction_cost_ema = transaction_cost
        else:
            self.gas_used_ema = self.ema_multiplier * transaction.transaction_receipt.gas_used + (
                (1 - self.ema_multiplier) * self.gas_used_ema
            )
            self.transaction_cost_ema = self.ema_multiplier * transaction_cost + (
                (1 - self.ema_multiplier) * self.transaction_cost_ema
            )

    def is_acceptable_cost(self, transaction: TransactionResult) -> bool:
        return self.calculate_difference_from_ema(transaction=transaction) < self.allowed_fluctuation

    def calculate_difference_from_ema(self, transaction: TransactionResult) -> Decimal:
        transaction_cost = (
            transaction.transaction_receipt.effective_gas_price *
            transaction.transaction_receipt.gas_used
        )

        if self.transaction_cost_ema:
            return (transaction_cost - self.transaction_cost_ema) / self.transaction_cost_ema
        else:
            return Decimal("0")

    def transaction_cost_estimate(self) -> Decimal:
        if self.transaction_cost_ema is None:
            return Decimal("0.4")

        return self.transaction_cost_ema * self.eth_price
