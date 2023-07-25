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


class OrderQuery:
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
        self.offer = self.offer_entity()

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

    def offer_entity(
        self,
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        Offer = self.data.Offer

        # if we have a network object we can get all the token information we need
        if self.network:
            Offer.pay_amt_formatted = SyntheticField(
                f=lambda pay_amt, pay_gem: self.get_token(pay_gem).to_decimal(pay_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.pay_amt, Offer.pay_gem],
            )

            Offer.buy_amt_formatted = SyntheticField(
                f=lambda buy_amt, buy_gem: self.get_token(buy_gem).to_decimal(buy_amt),
                type_=SyntheticField.FLOAT,
                deps=[Offer.buy_amt, Offer.buy_gem],
            )

            Offer.paid_amt_formatted = SyntheticField(
                f=lambda paid_amt, pay_gem: self.get_token(pay_gem).to_decimal(
                    paid_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[Offer.paid_amt, Offer.pay_gem],
            )

            Offer.bought_amt_formatted = SyntheticField(
                f=lambda bought_amt, buy_gem: self.get_token(buy_gem).to_decimal(
                    bought_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[Offer.bought_amt, Offer.buy_gem],
            )

            Offer.pay_gem_symbol = SyntheticField(
                f=lambda pay_gem: self.get_token(pay_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Offer.pay_gem],
            )

            Offer.buy_gem_symbol = SyntheticField(
                f=lambda buy_gem: self.get_token(buy_gem).symbol,
                type_=SyntheticField.STRING,
                deps=[Offer.buy_gem],
            )

            Offer.datetime = SyntheticField(
                f=lambda timestamp: str(datetime.fromtimestamp(timestamp)),
                type_=SyntheticField.STRING,
                deps=[Offer.timestamp],
            )

        return Offer

    def offers_query(
        self,
        order_by: str,
        order_direction: str,
        first: int,
        maker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        pay_gem: Optional[Union[ChecksumAddress, str]] = None,
        buy_gem: Optional[Union[ChecksumAddress, str]] = None,
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        # TODO: there is definitely a clear way to pass these parameters in a more concise way, prolly **kargs
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        # determine that the parameters are valid
        error_messages = []

        # check the order_by parameter
        if order_by.lower() not in ("timestamp", "price"):
            error_messages.append(
                "Invalid order_by, must be 'timestamp' or 'price' (default: timestamp)"
            )
        elif order_by.lower() == "timestamp":
            order_by = self.offer.timestamp
        elif order_by.lower() == "price":
            order_by = self.offer.price

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
            self.offer.maker == str(maker).lower() if maker else None,
            self.offer.from_address == str(from_address).lower()
            if from_address
            else None,
            self.offer.pay_gem == str(pay_gem).lower() if pay_gem else None,
            self.offer.buy_gem == str(buy_gem).lower() if buy_gem else None,
            self.offer.open == open if open is not None else None,
            self.offer.timestamp >= start_time if start_time else None,
            self.offer.timestamp <= end_time if end_time else None,
        ]
        where = [condition for condition in where if condition is not None]

        """Helper method to build a query for the offers subgraph entity."""
        offers = self.data.Query.offers(
            orderBy=order_by,
            orderDirection=order_direction,
            first=first,
            where=where if where else {},
        )

        return offers

    def offers_fields(
        self,
        offers: Any,  # TODO: check that this is the correct type (subgrounds may have types that we can utilize here)
        formatted: bool = False,
    ):  # TODO: return a typed object (see subgrounds documentation for more info)
        """Helper method to build a list of fields for the offers subgraph entity."""
        fields = [
            offers.id,
            offers.timestamp,
            offers.index,
            offers.maker.id,
            offers.from_address.id,
            offers.pay_gem,
            offers.buy_gem,
            offers.pay_amt,
            offers.buy_amt,
            offers.paid_amt,
            offers.bought_amt,
            offers.price,
            offers.open,
            offers.removed_timestamp,
            offers.removed_block,
            offers.transaction.id,
            offers.transaction.block_number,
            offers.transaction.block_index,
        ]

        if formatted:
            fields.append(offers.pay_amt_formatted)
            fields.append(offers.buy_amt_formatted)
            fields.append(offers.paid_amt_formatted)
            fields.append(offers.bought_amt_formatted)
            fields.append(offers.pay_gem_symbol)
            fields.append(offers.buy_gem_symbol)
            fields.append(offers.datetime)

        return fields

    def query_offers(
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
                "index",
                "maker",
                "from_address",
                "pay_gem",
                "buy_gem",
                "pay_amt",
                "buy_amt",
                "paid_amt",
                "bought_amt",
                "price",
                "open",
                "removed_timestamp",
                "removed_block",
                "transaction",
                "transaction_block_number",
                "transaction_block_index",
            ]
            df = pd.DataFrame(columns=cols)

        elif df.empty and formatted:
            cols = [
                "id",
                "maker",
                "from_address",
                "pay_gem",
                "buy_gem",
                "pay_amt",
                "buy_amt",
                "paid_amt",
                "bought_amt",
            ]
            df = pd.DataFrame(columns=cols)

        else:
            df.columns = [col.replace("offers_", "") for col in df.columns]
            df.columns = [col.replace("_id", "") for col in df.columns]

            # convert the id to an integer
            # TODO: i don't love the lambda (cc pickling, but it appears we are forced to use them in sythetic fields
            #  regardless)
            df["id"] = df["id"].apply(lambda x: int(x, 16))

            # TODO: decide whether we should return the unformatted fields or not
            if formatted:
                df = df.drop(
                    columns=[
                        "pay_amt",
                        "buy_amt",
                        "paid_amt",
                        "bought_amt",
                        "pay_gem",
                        "buy_gem",
                        "timestamp",
                        "index",
                        "price",
                        "removed_timestamp",
                        "removed_block",
                        "transaction_block_number",
                        "transaction_block_index",
                    ]
                )
                df = df.rename(
                    columns={
                        "pay_amt_formatted": "pay_amt",
                        "buy_amt_formatted": "buy_amt",
                        "paid_amt_formatted": "paid_amt",
                        "bought_amt_formatted": "bought_amt",
                        "pay_gem_symbol": "pay_gem",
                        "buy_gem_symbol": "buy_gem",
                        "datetime": "timestamp",
                    }
                )
                # TODO: we could also get smart with displaying price dependent upon the pair_name and direction of the
                #  order

        # TODO: apply any data type conversions to the dataframe - possibly converting unformatted values to integers
        return df
