from typing import Optional, Dict

import pandas as pd
from eth_typing import ChecksumAddress
from subgrounds import Subgrounds

from rubi.contracts import (
    ERC20,
)
from rubi.network import (
    Network,
)
from rubi.rubicon_types import (
    OrderSide,
    OrderQuery,
    TradeQuery,
)


class MarketData:
    """This class represents the RubiconV2 Subgraph, which contains data primarily related to the RubiconMarket.sol
    contract. If a Network object is not passed in instantiation then this class will only be used to query data related
     to the subgraph.

    :param subgrounds: a Subgrounds instance
    :type subgrounds: Subgrounds
        param subgraph_url: a RubiconV2 Subgraph url endpoint that should be utilized for this class
    :type subgraph_url: str
    :param network: a Network object, native to the package
    :type network: Network
    """

    def __init__(
        self,
        subgrounds: Subgrounds,
        subgraph_url: str,
        subgraph_fallback_url: str,
        network: Optional[Network] = None,
        network_tokens: Optional[Dict[ChecksumAddress, ERC20]] = None,
    ):
        """constructor method"""
        self.sg = subgrounds
        self.subgraph_url = subgraph_url
        self.subgraph_fallback_url = subgraph_fallback_url
        self.network = network  # type: Network | None
        self.tokens = network_tokens  # type: Dict[ChecksumAddress, ERC20] | None

        # initialize the subgraph
        for attempt in range(3):
            try:
                self.data = self.sg.load_subgraph(
                    self.subgraph_url
                )  # TODO: we should add a check here to guarantee the schema matches what we expect to be receiving
                break
            except Exception as e:
                if attempt < 2:
                    continue
                else:
                    try:
                        self.data = self.sg.load_subgraph(self.subgraph_fallback_url)
                        break
                    except:
                        raise ValueError(
                            f"Both subgraph_url: {self.subgraph_url} and fallback_url: {self.subgraph_fallback_url} failed when attempting to load. Error: {str(e)}"
                        )

        # Initialize the query classes
        self.offer_query = OrderQuery(self.sg, self.data, self.network, self.tokens)
        self.trade_query = TradeQuery(self.sg, self.data, self.network, self.tokens)

    @classmethod
    def from_network_with_tokens(
        cls, network: Network, network_tokens: Dict[ChecksumAddress, ERC20]
    ) -> "MarketData":
        """Initialize a MarketData object using a Network object."""
        return cls(
            subgrounds=network.subgrounds,
            subgraph_url=network.market_data_url,
            subgraph_fallback_url=network.market_data_fallback_url,
            network=network,
            network_tokens=network_tokens,
        )

    #####################################
    # Subgraph Query Methods            #
    #####################################

    # TODO: refactor using a decorator to handle the parameter validation
    def get_offers(
        self,
        maker: Optional[str] = None,
        from_address: Optional[str] = None,
        pair_name: Optional[str] = None,
        book_side: Optional[OrderSide] = OrderSide.NEUTRAL,
        pay_gem: Optional[
            str
        ] = None,  # TODO: maybe we should allow the user to pass in an address here?
        buy_gem: Optional[
            str
        ] = None,  # TODO: maybe we should allow the user to pass in an address here?
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        first: Optional[int] = 1000,
        order_by: Optional[str] = "timestamp",
        order_direction: Optional[str] = "desc",
        formatted: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Returns a dataframe of offers placed on the market contract, with the option to pass in filters.

        :param maker: the address of the maker of the offer
        :type maker: str
        :param from_address: the address that originated the transaction that created the offer
        :type from_address: str
        :param pay_gem: the address of the token that the maker is offering (will override pair_name if both are passed)
        :type pay_gem: str
        :param buy_gem: the address of the token that the maker is requesting (will override pair_name if both are passed)
        :type buy_gem: str
        :param open: whether or not the offer is still active
        :type open: bool
        :param start_time: the timestamp of the earliest offer to return
        :type start_time: int
        :param end_time: the timestamp of the latest offer to return
        :type end_time: int
        :param first: the number of offers to return
        :type first: int
        :param order_by: the field to order the offers by (default: timestamp, options: timestamp, price) TODO: expand this list
        :type order_by: str
        :param order_direction: the direction to order the offers by (default: desc, options: asc, desc)
        :type order_direction: str
        :param formatted: whether or not to return the formatted fields (default: False, requires a network object to be passed)
        :return: a dataframe of offers placed on the market contract
        :rtype: pd.DataFrame
        """

        # if we want formatted fields, make sure we have a network object
        # TODO: we could pass this to the offers_query method and handle it there - if we start to utilize something like **kargs lets do that
        if formatted and not self.network:
            raise ValueError(
                "Cannot return formatted fields without a network object initialized on the class."
            )

        # handle the pair_name parameter
        if pair_name:
            base, quote = pair_name.split("/")
            base_asset = ERC20.from_network(name=base, network=self.network)
            quote_asset = ERC20.from_network(name=quote, network=self.network)

        # handle the book_side parameter
        if (
            book_side and pair_name
        ):  # TODO: we need to handle the case where neither of these are passed
            match book_side:
                case OrderSide.BUY:
                    buy_query = self.offer_query.offers_query(
                        order_by,
                        order_direction,
                        first,
                        maker,
                        from_address,
                        pay_gem=quote_asset.address,
                        buy_gem=base_asset.address,
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    buy_fields = self.offer_query.offers_fields(buy_query, formatted)
                    buy_df = self.offer_query.query_offers(buy_fields, formatted)
                    buy_df[
                        "side"
                    ] = "buy"  # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    return buy_df

                case OrderSide.SELL:
                    sell_query = self.offer_query.offers_query(
                        order_by,
                        order_direction,
                        first,
                        maker,
                        from_address,
                        pay_gem=base_asset.address,
                        buy_gem=quote_asset.address,
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    sell_fields = self.offer_query.offers_fields(sell_query, formatted)
                    sell_df = self.offer_query.query_offers(sell_fields, formatted)
                    sell_df[
                        "side"
                    ] = "sell"  # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    return sell_df

                case OrderSide.NEUTRAL:
                    buy_query = self.offer_query.offers_query(
                        order_by,
                        order_direction,
                        first,
                        maker,
                        from_address,
                        pay_gem=quote_asset.address,
                        buy_gem=base_asset.address,
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    buy_fields = self.offer_query.offers_fields(buy_query, formatted)
                    buy_df = self.offer_query.query_offers(buy_fields, formatted)
                    buy_df[
                        "side"
                    ] = "buy"  # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    sell_query = self.offer_query.offers_query(
                        order_by,
                        order_direction,
                        first,
                        maker,
                        from_address,
                        pay_gem=base_asset.address,
                        buy_gem=quote_asset.address,
                        open=open,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    sell_fields = self.offer_query.offers_fields(sell_query, formatted)
                    sell_df = self.offer_query.query_offers(sell_fields, formatted)
                    sell_df[
                        "side"
                    ] = "sell"  # TODO: we could also pass this data to the offers_query method and handle it there, could help with price

                    # TODO: decide what we want to do here, maybe we just return both dataframes?

                    # reset the index  # need to pass a somewhat more complicated ordering here to comply with what happened in the same block time
                    return pd.concat([buy_df, sell_df]).reset_index(drop=True)

        # handle the pay_gem and buy_gem parameters
        elif pay_gem and buy_gem:
            query = self.offer_query.offers_query(
                order_by,
                order_direction,
                first,
                maker,
                from_address,
                pay_gem=pay_gem,
                buy_gem=buy_gem,
                open=open,
                start_time=start_time,
                end_time=end_time,
            )
            fields = self.offer_query.offers_fields(query)
            df = self.offer_query.query_offers(fields)

            return df

    def get_trades(
        self,
        taker: Optional[str] = None,
        from_address: Optional[str] = None,
        pair_name: Optional[str] = None,
        book_side: Optional[OrderSide] = OrderSide.NEUTRAL,
        take_gem: Optional[
            str
        ] = None,  # TODO: not sure we really need this given the pair_name parameter
        give_gem: Optional[
            str
        ] = None,  # TODO: not sure we really need this given the pair_name parameter
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        first: Optional[
            int
        ] = 1000,  # TODO: maybe this should be a large number by default?
        order_by: Optional[str] = "timestamp",
        order_direction: Optional[str] = "desc",
        formatted: Optional[bool] = False,
    ) -> pd.DataFrame:
        """Returns a dataframe of trades that have occurred on the market contract, with the option to pass in filters.

        :param taker: the address of the taker of the trade
        :type taker: str
        :param from_address: the address that originated the transaction that created the trade
        :type from_address: str
        :param pair_name: the name of the pair that the trade occurred on (will override take_gem and give_gem if both are passed)
        :type pair_name: str
        :param book_side: the side of the order book that the trade occurred on (defaults to neutral, options: buy, sell, neutral)
        :type book_side: OrderSide
        :param take_gem: the address of the token that the taker received
        :type take_gem: str
        :param give_gem: the address of the token that the taker gave
        :type give_gem: str
        :param start_time: the timestamp of the earliest trade to return
        :type start_time: int
        :param end_time: the timestamp of the latest trade to return
        :type end_time: int
        :param first: the number of trades to return
        :type first: int
        :param order_by: the field to order the trades by (default: timestamp, options: timestamp) TODO: expand this list
        :type order_by: str
        :param order_direction: the direction to order the trades by (default: desc, options: asc, desc)
        :type order_direction: str
        :param formatted: whether or not to return the formatted fields (default: False, requires a network object to be passed)
        :type formatted: bool
        :return: a dataframe of trades that have occurred on the market contract
        :rtype: pd.DataFrame
        """

        # if we want formatted fields, make sure we have a network object
        if formatted and not self.network:
            raise ValueError(
                "Cannot return formatted fields without a network object initialized on the class."
            )

        # handle the pair_name parameter
        if pair_name:
            base, quote = pair_name.split("/")
            base_asset = ERC20.from_network(name=base, network=self.network)
            quote_asset = ERC20.from_network(name=quote, network=self.network)

        # handle the book_side parameter
        if (
            book_side and pair_name
        ):  # TODO: we need to handle the case where neither of these are passed
            match book_side:
                case OrderSide.BUY:
                    buy_query = self.trade_query.trades_query(
                        order_by,
                        order_direction,
                        first,
                        taker,
                        from_address,
                        take_gem=base_asset.address,
                        give_gem=quote_asset.address,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    buy_fields = self.trade_query.trades_fields(buy_query, formatted)
                    buy_df = self.trade_query.query_trades(buy_fields, formatted)
                    buy_df["side"] = "buy"

                    return buy_df

                case OrderSide.SELL:
                    sell_query = self.trade_query.trades_query(
                        order_by,
                        order_direction,
                        first,
                        taker,
                        from_address,
                        take_gem=quote_asset.address,
                        give_gem=base_asset.address,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    sell_fields = self.trade_query.trades_fields(sell_query, formatted)
                    sell_df = self.trade_query.query_trades(sell_fields, formatted)
                    sell_df["side"] = "sell"

                    return sell_df

                case OrderSide.NEUTRAL:
                    buy_query = self.trade_query.trades_query(
                        order_by,
                        order_direction,
                        first,  # TODO: decide if we only want to pass half the values here
                        taker,
                        from_address,
                        take_gem=base_asset.address,
                        give_gem=quote_asset.address,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    buy_fields = self.trade_query.trades_fields(buy_query, formatted)
                    buy_df = self.trade_query.query_trades(buy_fields, formatted)
                    buy_df["side"] = "buy"

                    sell_query = self.trade_query.trades_query(
                        order_by,
                        order_direction,
                        first,
                        taker,
                        from_address,
                        take_gem=quote_asset.address,
                        give_gem=base_asset.address,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    sell_fields = self.trade_query.trades_fields(sell_query, formatted)
                    sell_df = self.trade_query.query_trades(sell_fields, formatted)
                    sell_df["side"] = "sell"

                    return pd.concat([buy_df, sell_df]).reset_index(
                        drop=True
                    )  # TODO: decide what we want to do here, maybe we just return both dataframes?

        # handle the take_gem and give_gem parameters
        elif take_gem and give_gem:
            query = self.trade_query.trades_query(
                order_by,
                order_direction,
                first,
                taker,
                from_address,
                take_gem=take_gem,
                give_gem=give_gem,
                start_time=start_time,
                end_time=end_time,
            )
            fields = self.trade_query.trades_fields(query, formatted)
            df = self.trade_query.query_trades(fields, formatted)

            return df
