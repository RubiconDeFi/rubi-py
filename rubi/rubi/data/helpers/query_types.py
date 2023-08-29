from typing import Any, List, Dict

from eth_typing import ChecksumAddress
from subgrounds import FieldPath


class SubgraphResponse:
    def __init__(self, block_number: int, body: List[Any]):
        self.block_number = block_number
        self.body = body

    def __add__(self, other: "SubgraphResponse") -> "SubgraphResponse":
        block_number = (
            self.block_number
            if self.block_number < other.block_number
            else other.block_number
        )

        return SubgraphResponse(block_number=block_number, body=self.body + other.body)


class SubgraphOffer:
    """Helper object for querying subgraph Offers"""

    def __init__(
        self,
        order_id: int,
        order_owner: ChecksumAddress,
        pay_gem: ChecksumAddress,
        pay_amt: int,
        paid_amt: int,
        buy_gem: ChecksumAddress,
        buy_amt: int,
        bought_amt: int,
        open: bool,
    ):
        self.order_id = order_id
        self.order_owner = order_owner
        self.pay_gem = pay_gem
        self.pay_amt = pay_amt
        self.paid_amt = paid_amt
        self.buy_gem = buy_gem
        self.buy_amt = buy_amt
        self.bought_amt = bought_amt
        self.open = open

    @staticmethod
    def get_fields(field_paths: Dict[str, FieldPath]) -> List:
        """Helper method to build a list of fields for the offers subgraph entity."""
        return [
            field_paths["offer"].id,
            field_paths["offer"].timestamp,
            field_paths["offer"].index,
            field_paths["offer"].maker.id,
            field_paths["offer"].from_address.id,
            field_paths["offer"].pay_gem,
            field_paths["offer"].buy_gem,
            field_paths["offer"].pay_amt,
            field_paths["offer"].buy_amt,
            field_paths["offer"].paid_amt,
            field_paths["offer"].bought_amt,
            field_paths["offer"].price,
            field_paths["offer"].open,
            field_paths["offer"].removed_timestamp,
            field_paths["offer"].removed_block,
            field_paths["offer"].transaction.id,
            field_paths["offer"].transaction.block_number,
            field_paths["offer"].transaction.block_index,
            field_paths["offer"].pay_amt_decimals,
            field_paths["offer"].buy_amt_decimals,
            field_paths["offer"].paid_amt_decimals,
            field_paths["offer"].bought_amt_decimals,
            field_paths["offer"].pay_gem_symbol,
            field_paths["offer"].buy_gem_symbol,
            field_paths["offer"].datetime,
            field_paths["block"].number,
        ]


class SubgraphTrade:
    """Helper object for querying subgraph Trades"""

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
            trade_query.take_amt_decimals,
            trade_query.give_amt_decimals,
            trade_query.take_gem_symbol,
            trade_query.datetime,
        ]
