from datetime import datetime
from typing import List, Optional, Dict, Any, Union

import pandas as pd
from eth_typing import ChecksumAddress
from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy
from subgrounds.subgraph import SyntheticField

from rubi.contracts import (
    ERC20,
)
from rubi.network import (
    Network,
)


class TradeQuery:
    def __init__(
        self,
        subgrounds: Subgrounds,
        subgraph,  # TODO: determine the type that should be used here
        network: Optional[Network] = None,
        network_tokens: Optional[Dict[ChecksumAddress, ERC20]] = None,
    ):
        self.sg = subgrounds
        self.data = subgraph
        self.network = network
        self.tokens = network_tokens
        self.trade = self.trade_entity()

    # TODO: we will want to move this somewhere else most likely - we can't access the client from here though so we
    #  will need to figure out how to do that
    #####################################
    # General Helper Methods
    #####################################

    def get_token(self, token_address: str) -> ERC20:
        """Returns an ERC20 object for the token address passed from the token_map if it exists or add it to the
        self.tokens if it does not exist.
        """

        if not self.tokens:
            raise ValueError("No network object initialized on the class.")
        else:
            try:
                token_address = self.network.w3.to_checksum_address(token_address)

                if token_address not in self.tokens:
                    self.tokens[token_address] = ERC20.from_address(
                        w3=self.network.w3, address=token_address
                    )

                return self.tokens[token_address]

            except:
                raise ValueError(f"Token address: {token_address} is invalid.")

    #####################################
    # Query Methods                     #
    #####################################

    """
    {
    takes {
        id
        index
        timestamp
        transaction {
            id
            timestamp
            block_number
            block_index
        }
        taker {
            id
        }
        from_address {
            id
        }
        take_gem
        give_gem
        take_amt
        give_amt
        offer {
            maker {
                id
            }
            from_address {
                id
            }
            index
            transaction {
                id
                block_number
                block_index
            }
        }
    }
    }   
    """

    def trade_entity(
        self,
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        Take = self.data.Take

        # if we have a network object we can get all the token information we need
        if self.network:
            Take.take_amt_formatted = SyntheticField(
                f=lambda take_amt, take_gem: self.get_token(take_gem).to_decimal(
                    take_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[Take.take_amt, Take.take_gem],
            )

            Take.give_amt_formatted = SyntheticField(
                f=lambda give_amt, give_gem: self.get_token(give_gem).to_decimal(
                    give_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[Take.give_amt, Take.give_gem],
            )

            Take.take_gem_symbol = SyntheticField(
                f=lambda take_gem: self.get_token(take_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Take.take_gem],
            )

            Take.give_gem_symbol = SyntheticField(
                f=lambda give_gem: self.get_token(give_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Take.give_gem],
            )

            Take.datetime = SyntheticField(
                f=lambda timestamp: str(datetime.fromtimestamp(timestamp)),
                type_=SyntheticField.STRING,
                deps=[Take.timestamp],
            )

        return Take

    def trades_query(
        self,
        order_by: str,
        order_direction: str,
        first: int,
        # maker: Optional[str] = None, TODO: resolve #63 and add in conditional filter for offer maker/from_address
        taker: Optional[Union[str, ChecksumAddress]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        take_gem: Optional[Union[ChecksumAddress, str]] = None,
        give_gem: Optional[Union[ChecksumAddress, str]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        # TODO: there is definitely a clear way to pass these parameters in a more concise way, prolly **kargs
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        # determine that the parameters are valid
        error_messages = []

        # check the order_by parameter
        if order_by.lower() not in ("timestamp"):
            error_messages.append(
                "Invalid order_by, must be 'timestamp' (default: timestamp)"
            )
        elif order_by.lower() == "timestamp":
            order_by = self.trade.timestamp

        # check the order_direction parameter
        if order_direction.lower() not in ("asc", "desc"):
            error_messages.append(
                "Invalid order_direction, must be 'asc' or 'desc' (default: desc)"
            )
        else:
            order_direction = order_direction.lower()

        # check the first parameter
        if first < 1:
            error_messages.append(
                "Invalid first, must be greater than 0 (default: 1000)"
            )
        if not isinstance(first, int):
            error_messages.append("Invalid first, must be an integer (default: 1000)")

        # raise an error if there are any
        if error_messages:
            raise ValueError("\n".join(error_messages))

        # build the list of where conditions
        where = [
            self.trade.taker == str(taker).lower() if taker else None,
            self.trade.from_address == str(from_address).lower()
            if from_address
            else None,
            self.trade.take_gem == str(take_gem).lower() if take_gem else None,
            self.trade.give_gem == str(give_gem).lower() if give_gem else None,
            self.trade.timestamp >= start_time if start_time else None,
            self.trade.timestamp <= end_time if end_time else None,
        ]
        where = [condition for condition in where if condition is not None]

        """Helper method to build a query for the take subgraph entity."""
        trades = self.data.Query.takes(
            orderBy=order_by,
            orderDirection=order_direction,
            first=first,
            where=where if where else {},
        )

        return trades

    def trades_fields(
        self,
        trades: Any,  # TODO: check that this is the correct type (subgrounds may have types that we can utilize here)
        formatted: bool = False,
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        """Helper method to build a list of fields for the offers subgraph entity."""
        fields = [
            trades.id,
            trades.timestamp,
            trades.take_gem,
            trades.give_gem,
            trades.take_amt,
            trades.give_amt,
            trades.taker.id,
            trades.from_address.id,
            trades.transaction.block_number,
            trades.transaction.block_index,
            trades.index,
            trades.offer.maker.id,
            trades.offer.from_address.id,
            trades.offer.transaction.block_number,
            trades.offer.transaction.block_index,
            trades.offer.index,
        ]

        if formatted:
            fields.append(trades.take_amt_formatted)
            fields.append(trades.give_amt_formatted)
            fields.append(trades.take_gem_symbol)
            fields.append(trades.give_gem_symbol)
            fields.append(trades.datetime)

        return fields

    def query_trades(
        self,
        fields: List,
        formatted: bool = False,
        # TOOD: maybe we give the user the option to define a custom pagination strategy?
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        """Helper method to query the offers subgraph entity."""
        df = self.sg.query_df(fields, pagination_strategy=ShallowStrategy)

        # if the dataframe is empty, return an empty dataframe with the correct columns
        if df.empty and not formatted:
            cols = [
                "id",
                "timestamp",
                "take_gem",
                "give_gem",
                "take_amt",
                "give_amt",
                "taker",
                "from_address",
                "block_number",
                "block_index",
                "log_index",
                "maker",
                "maker_from_address",
                "offer_block_number",
                "offer_block_index",
                "offer_log_index",
            ]
            df = pd.DataFrame(columns=cols)

        elif df.empty and formatted:
            cols = [
                "taker",
                "from_address",
                "take_gem",
                "give_gem",
                "take_amt",
                "give_amt",
                "timestamp",
                "maker",
                "maker_from_address",
                "block_number",
                "block_index",
                "log_index",
            ]
            df = pd.DataFrame(columns=cols)

        else:
            df.columns = [col.replace("takes_", "") for col in df.columns]
            df.columns = [col.replace("_id", "") for col in df.columns]

            # TODO: decide whether we should return the unformatted fields or not
            if formatted:
                df = df.drop(
                    columns=[
                        "id",
                    ]
                )
                df = df.rename(
                    columns={
                        "take_amt_formatted": "take_amt",
                        "give_amt_formatted": "give_amt",
                        "take_amt": "take_amt_raw",
                        "give_amt": "give_amt_raw",
                        "take_gem": "take_gem_address",
                        "give_gem": "give_gem_address",
                        "take_gem_symbol": "take_gem",
                        "give_gem_symbol": "give_gem",
                        "index": "log_index",
                        "transaction_block_number": "block_number",
                        "transaction_block_index": "block_index",
                        "offer_transaction_block_number": "offer_block_number",
                        "offer_transaction_block_index": "offer_block_index",
                        "offer_index": "offer_log_index",
                    }
                )
                # TODO: we could also get smart with displaying price dependent upon the pair_name and direction of the
                #  order

        # TODO: apply any data type conversions to the dataframe - possibly converting unformatted values to integers
        return df
