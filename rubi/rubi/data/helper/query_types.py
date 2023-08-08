from typing import Any, List


class Offer:
    @staticmethod
    def get_fields(offer_query: Any) -> List:
        """Helper method to build a list of fields for the offers subgraph entity."""
        return [
            offer_query.id,
            offer_query.timestamp,
            offer_query.index,
            offer_query.maker.id,
            offer_query.from_address.id,
            offer_query.pay_gem,
            offer_query.buy_gem,
            offer_query.pay_amt,
            offer_query.buy_amt,
            offer_query.paid_amt,
            offer_query.bought_amt,
            offer_query.price,
            offer_query.open,
            offer_query.removed_timestamp,
            offer_query.removed_block,
            offer_query.transaction.id,
            offer_query.transaction.block_number,
            offer_query.transaction.block_index,
            offer_query.pay_amt_decimals,
            offer_query.buy_amt_decimals,
            offer_query.paid_amt_decimals,
            offer_query.bought_amt_decimals,
            offer_query.pay_gem_symbol,
            offer_query.buy_gem_symbol,
            offer_query.datetime,
        ]


class Trade:
    @staticmethod
    def get_fields(trade_query: Any) -> List:
        """Helper method to build a list of fields for the offers subgraph entity."""
        return [
            trade_query.id,
            trade_query.timestamp,
            trade_query.take_gem,
            trade_query.give_gem,
            trade_query.take_amt,
            trade_query.give_amt,
            trade_query.taker.id,
            trade_query.from_address.id,
            trade_query.transaction.block_number,
            trade_query.transaction.block_index,
            trade_query.index,
            trade_query.offer.maker.id,
            trade_query.offer.from_address.id,
            trade_query.offer.transaction.block_number,
            trade_query.offer.transaction.block_index,
            trade_query.offer.index,
            trade_query.take_amt_decimal,
            trade_query.give_amt_decimal,
            trade_query.take_gem_symbol,
            trade_query.datetime,
        ]
