import logging
from _decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List, Union

import pandas as pd
from eth_typing import ChecksumAddress
from subgrounds import Subgrounds, Subgraph, SyntheticField
from subgrounds.pagination import ShallowStrategy
from web3 import Web3

from rubi.contracts import ERC20
from rubi.data.helpers import QueryValidation
from rubi.data.helpers import SubgraphOffer, SubgraphTrade
from rubi.network import Network

logger = logging.getLogger(__name__)

# Stop subgrounds from logging kak
logging.getLogger("subgrounds").setLevel(logging.WARNING)


class MarketData:
    """This class represents the RubiconV2 Subgraph, which contains data primarily related to the RubiconMarket.sol
    contract.

    :param url: a RubiconV2 Subgraph url endpoint that should be utilized for this class
    :type url: str
    :param fallback_url: a fallback url if we fail to connect to the primary url
    :type fallback_url: str
    :param tokens: A dictionary of token addresses and symbols to their ERC20 instantiation
    :type tokens: Dict[ChecksumAddress | str, ERC20]
    """

    def __init__(
        self,
        url: str,
        fallback_url: str,
        network: Optional[Network] = None,
    ):
        """constructor method"""

        self.subgrounds = Subgrounds()

        if network is not None:
            self.tokens = network.tokens
            self.netwrok = network
        else:
            self.tokens = None  # noqa
            self.network = None  # noqa

        self.subgraph: Subgraph = self._initialize_subgraph(
            url=url, fallback_url=fallback_url
        )

        # Subgraph objects
        self.offer = self._initialize_subgraph_offer()
        self.trade = self._initialize_subgraph_trade()

    @classmethod
    def from_network(
        cls,
        network: Network,
    ):
        """Initialize the MarketData object from a network object

        :param network: The network object
        :type network: Network
        """

        return cls(
            url=network.market_data_url,
            fallback_url=network.market_data_fallback_url,
            network=network,
        )

    def _initialize_subgraph(
        self, url: str, fallback_url: str, attempts: int = 3
    ) -> Subgraph:
        """Initialize the subgraph

        :param url: The subgraph url
        :type url: str
        :param fallback_url: The fallback subgraph url
        :type url: str
        :param attempts: The number of connection attempts to make
        :type attempts: int
        :return: A initialized subgraph instance
        :rtype: Subgraph
        """

        subgraph = None

        for attempt in range(attempts):
            try:
                # TODO: we should add a check here to guarantee the schema matches what we expect to be receiving
                subgraph = self.subgrounds.load_subgraph(url=url)
                break
            except Exception as e:
                logger.debug(f"Exception loading subgraph: {e}")
                continue

        if subgraph is None:
            for attempt in range(attempts):
                try:
                    subgraph = self.subgrounds.load_subgraph(url=fallback_url)
                    break
                except Exception as e:
                    logger.debug(f"Exception loading subgraph: {e}")
                    continue

        if subgraph is None:
            raise ValueError(
                f"Both subgraph_url: {url} and fallback_url: {fallback_url} failed when attempting to load."
            )

        return subgraph

    ######################################################################
    # Subgraph objects
    ######################################################################

    def _erc20_to_decimal(
        self, gem: Union[ChecksumAddress, str], amt: int
    ) -> Optional[Decimal]:
        """Helper to convert an amount to decimals for the given ERC20"""

        if self.tokens.get(Web3.to_checksum_address(gem)) is None:
            self.network.token_from_address(gem)

        try:
            return self.tokens[Web3.to_checksum_address(gem)].to_decimal(amt)
        except KeyError:
            return None

    def _erc20_to_symbol(self, gem: Union[ChecksumAddress, str]) -> Optional[str]:
        """Helper to get the symbol of the given ERC20"""

        if self.tokens.get(Web3.to_checksum_address(gem)) is None:
            self.network.token_from_address(gem)

        try:
            return self.tokens[Web3.to_checksum_address(gem)].symbol
        except KeyError:
            return None

    def _initialize_subgraph_offer(self):
        """Initialize the Subgraph offer object and add synthetic fields"""

        offer = self.subgraph.Offer  # noqa

        offer.datetime = SyntheticField(
            f=lambda timestamp: str(datetime.fromtimestamp(timestamp)),
            type_=SyntheticField.STRING,
            deps=[offer.timestamp],
        )

        if self.tokens is not None:
            offer.pay_amt_decimals = SyntheticField(
                f=lambda pay_amt, pay_gem: self._erc20_to_decimal(
                    gem=pay_gem, amt=pay_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[offer.pay_amt, offer.pay_gem],
            )

            offer.buy_amt_decimals = SyntheticField(
                f=lambda buy_amt, buy_gem: self._erc20_to_decimal(
                    gem=buy_gem, amt=buy_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[offer.buy_amt, offer.buy_gem],
            )

            offer.paid_amt_decimals = SyntheticField(
                f=lambda paid_amt, pay_gem: self._erc20_to_decimal(
                    gem=pay_gem, amt=paid_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[offer.paid_amt, offer.pay_gem],
            )

            offer.bought_amt_decimals = SyntheticField(
                f=lambda bought_amt, buy_gem: self._erc20_to_decimal(
                    gem=buy_gem, amt=bought_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[offer.bought_amt, offer.buy_gem],
            )

            offer.pay_gem_symbol = SyntheticField(
                f=lambda pay_gem: self._erc20_to_symbol(gem=pay_gem),
                type_=SyntheticField.STRING,
                deps=[offer.pay_gem],
            )

            offer.buy_gem_symbol = SyntheticField(
                f=lambda buy_gem: self._erc20_to_symbol(gem=buy_gem),
                type_=SyntheticField.STRING,
                deps=[offer.buy_gem],
            )

        return offer

    def _initialize_subgraph_trade(self):
        """Initialize the Subgraph trade object and add synthetic fields"""

        take = self.subgraph.Take  # noqa

        take.datetime = SyntheticField(
            f=lambda timestamp: str(datetime.fromtimestamp(timestamp)),
            type_=SyntheticField.STRING,
            deps=[take.timestamp],
        )

        if self.tokens is not None:
            take.take_amt_decimals = SyntheticField(
                f=lambda take_amt, take_gem: self._erc20_to_decimal(
                    gem=take_gem, amt=take_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[take.take_amt, take.take_gem],
            )

            take.give_amt_decimals = SyntheticField(
                f=lambda give_amt, give_gem: self._erc20_to_decimal(
                    gem=give_gem, amt=give_amt
                ),
                type_=SyntheticField.FLOAT,
                deps=[take.give_amt, take.give_gem],
            )

            take.take_gem_symbol = SyntheticField(
                f=lambda take_gem: self._erc20_to_symbol(gem=take_gem),
                type_=SyntheticField.STRING,
                deps=[take.take_gem],
            )

            take.give_gem_symbol = SyntheticField(
                f=lambda give_gem: self._erc20_to_symbol(gem=give_gem),
                type_=SyntheticField.STRING,
                deps=[take.give_gem],
            )

        return take

    ######################################################################
    # Subgraph Query Methods
    ######################################################################

    # TODO: refactor using a decorator to handle the parameter validation
    def get_offers(
        self,
        maker: Optional[ChecksumAddress] = None,
        from_address: Optional[ChecksumAddress] = None,
        pay_gem: Optional[ChecksumAddress] = None,
        buy_gem: Optional[ChecksumAddress] = None,
        side: Optional[str] = None,
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_block: Optional[int] = None,  # TODO: add in start_block and end_block
        end_block: Optional[int] = None,  # TODO: add in start_block and end_block
        first: int = 1000,
        # TODO: expand order_by options
        order_by: str = "timestamp",
        order_direction: str = "desc",
        as_dataframe: bool = True,
    ) -> Optional[pd.DataFrame] | List[SubgraphOffer]:
        """Returns a dataframe of offers placed on the market contract, with the option to pass in filters.

        :param maker: the address of the maker of the offer
        :type maker: Optional[ChecksumAddress]
        :param from_address: the address that originated the transaction that created the offer
        :type from_address: Optional[ChecksumAddress]
        :param pay_gem: the address of the token that the maker is offering (will override pair_name if both are passed)
        :type pay_gem: Optional[ChecksumAddress]
        :param buy_gem: the address of the token that the maker is requesting (will override pair_name if both are passed)
        :type buy_gem: Optional[ChecksumAddress]
        :param side: The side we are querying for
        :type side: Optional[str]
        :param open: whether the offer is still active
        :type open:Optional[bool]
        :param start_time: the timestamp of the earliest offer to return
        :type start_time: int
        :param end_time: the timestamp of the latest offer to return
        :type end_time: int
        :param first: the number of offers to return
        :type first: int
        :param order_by: the field to order the offers by (default: timestamp, options: timestamp, price)
        :type order_by: str
        :param order_direction: the direction to order the offers by (default: desc, options: asc, desc)
        :type order_direction: str
        :param as_dataframe: If the response should be a dataframe (default: True)
        :type as_dataframe: bool
        :return: a dataframe of offers placed on the market contract or a list of subgraph offer objects
        :rtype: Optional[pd.DataFrame] | List[SubgraphOffer]
        """

        offer_query = self._build_offers_query(
            order_by=order_by,
            order_direction=order_direction,
            first=first,
            maker=maker,
            from_address=from_address,
            pay_gem=pay_gem,
            buy_gem=buy_gem,
            open=open,
            start_time=start_time,
            end_time=end_time,
            start_block=start_block,
            end_block=end_block,
        )

        query_fields = SubgraphOffer.get_fields(offer_query=offer_query)
        if as_dataframe:
            response = self._query_offers_as_dataframe(query_fields=query_fields)
            # TODO: we could also pass this data to the offers_query method and handle it there, could help with price
            if response is not None and not response.empty:
                response["side"] = side if side else "N/A"

            return response
        else:
            response = self._query_offers(query_fields=query_fields)

            return response

    def get_trades(
        self,
        # TODO: resolve #63 and add in conditional filter for offer maker/from_address
        # maker: Optional[Union[ChecksumAddress, str]],
        taker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        take_gem: Optional[Union[ChecksumAddress, str]] = None,
        give_gem: Optional[Union[ChecksumAddress, str]] = None,
        side: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        maker: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
        maker_from_address: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
        first: int = 1000,
        # TODO: expand order_by options
        order_by: str = "timestamp",
        order_direction: str = "desc",
    ) -> pd.DataFrame:
        """Returns a dataframe of trades that have occurred on the market contract, with the option to pass in filters.

        :param taker: the address of the taker of the trade
        :type taker: str
        :param from_address: the address that originated the transaction that created the trade
        :type from_address: str
        :param take_gem: the address of the token that the taker received
        :type take_gem: str
        :param give_gem: the address of the token that the taker gave
        :type give_gem: str
        :param side: The side we are querying for
        :type side: Optional[str]
        :param start_time: the timestamp of the earliest trade to return
        :type start_time: int
        :param end_time: the timestamp of the latest trade to return
        :type end_time: int
        :param first: the number of trades to return
        :type first: int
        :param order_by: the field to order the trades by (default: timestamp, options: timestamp)
        :type order_by: str
        :param order_direction: the direction to order the trades by (default: desc, options: asc, desc)
        :type order_direction: str
        :return: a dataframe of trades that have occurred on the market contract
        :rtype: pd.DataFrame
        """

        trade_query = self._build_trades_query(
            order_by=order_by,
            order_direction=order_direction,
            first=first,
            taker=taker,
            from_address=from_address,
            take_gem=take_gem,
            give_gem=give_gem,
            start_time=start_time,
            end_time=end_time,
            start_block=start_block,
            end_block=end_block,
            maker=maker,
            maker_from_address=maker_from_address,
        )
        query_fields = SubgraphTrade.get_fields(trade_query=trade_query)
        df = self._query_trades_as_dataframe(query_fields=query_fields)
        if df is not None and not df.empty:
            df["side"] = side if side else "N/A"

        return df

    ######################################################################
    # helper methods
    ######################################################################

    def _build_offers_query(
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
        start_block: Optional[int] = None,  # TODO: add in start_block and end_block
        end_block: Optional[int] = None,  # TODO: add in start_block and end_block
    ):
        """Helper method build an offers query."""

        QueryValidation.validate_offer_query(
            order_by=order_by,
            order_direction=order_direction,
            first=first,
        )

        if order_by.lower() == "timestamp":
            order_by = self.offer.timestamp
        elif order_by.lower() == "price":
            order_by = self.offer.price

        order_direction = order_direction.lower()

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

        offers_query = self.subgraph.Query.offers(  # noqa
            orderBy=order_by,
            orderDirection=order_direction,
            first=first,
            where=where if where else {},
        )

        return offers_query

    def _build_trades_query(
        self,
        order_by: str,
        order_direction: str,
        first: int,
        taker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        take_gem: Optional[Union[ChecksumAddress, str]] = None,
        give_gem: Optional[Union[ChecksumAddress, str]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        maker: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
        maker_from_address: Optional[
            Union[ChecksumAddress, str]
        ] = None,  # TODO: implement this with nested filtering
    ):
        """Helper method build a trades query."""

        QueryValidation.validate_trade_query(
            order_by=order_by,
            order_direction=order_direction,
            first=first,
        )

        if order_by.lower() == "timestamp":
            order_by = self.trade.timestamp

        order_direction = order_direction.lower()

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

        trades_query = self.subgraph.Query.takes(  # noqa
            orderBy=order_by,
            orderDirection=order_direction,
            first=first,
            where=where if where else {},
        )

        return trades_query

    def _query_offers_as_dataframe(self, query_fields: List) -> Optional[pd.DataFrame]:
        """Helper method to query the offers subgraph entity and return a dataframe."""

        df = self.subgrounds.query_df(
            query_fields,
            # TODO: maybe we give the user the option to define a custom pagination strategy.
            pagination_strategy=ShallowStrategy,  # noqa
        )

        if df.empty:
            return df

        df.columns = [col.replace("offers_", "") for col in df.columns]
        df.columns = [col.replace("_id", "") for col in df.columns]

        # convert the id to an integer
        df["id"] = df["id"].apply(lambda x: int(x, 16))

        # TODO: apply any data type conversions to the dataframe - possibly converting unformatted values to integers
        return df

    def _query_offers(self, query_fields: List) -> List[SubgraphOffer]:
        """Helper method to query the offers subgraph entity."""

        response = self.subgrounds.query_json(
            query_fields,
            # TODO: maybe we give the user the option to define a custom pagination strategy.
            pagination_strategy=ShallowStrategy,  # noqa
        )

        if response:
            raw_offers = list(response[0].values())[0]
            offers: List[SubgraphOffer] = []

            for raw_offer in raw_offers:
                offers.append(
                    SubgraphOffer(
                        order_id=int(raw_offer["id"], 16),
                        order_owner=Web3.to_checksum_address(raw_offer["maker"]["id"]),
                        pay_gem=Web3.to_checksum_address(raw_offer["pay_gem"]),
                        pay_amt=raw_offer["pay_amt"],
                        paid_amt=raw_offer["paid_amt"],
                        buy_gem=Web3.to_checksum_address(raw_offer["buy_gem"]),
                        buy_amt=raw_offer["buy_amt"],
                        bought_amt=raw_offer["bought_amt"],
                        open=raw_offer["open"],
                    )
                )
            return offers

        return []

    def _query_trades_as_dataframe(
        self,
        query_fields: List,
    ) -> Optional[pd.DataFrame]:
        """Helper method to query the trades subgraph entity."""

        df = self.subgrounds.query_df(
            query_fields,
            # TODO: maybe we give the user the option to define a custom pagination strategy.
            pagination_strategy=ShallowStrategy,  # noqa
        )

        if df.empty:
            return df

        df.columns = [col.replace("takes_", "") for col in df.columns]
        df.columns = [col.replace("_id", "") for col in df.columns]

        return df
