from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy

from rubi.data.sources.helper import networks

class MarketData: 
    """this class acts as an access point to a variety of data from the RubiconMarket.sol contract. it acts as a data processing layer built using the subgrounds library and the subgraphs maintained at the follwing repo: https://github.com/RubiconDeFi/rubi-subgraphs
    """

    def __init__(self, subgrounds, chain_id):
        """constructor method
        
        :param subgrounds: the subgrounds object
        :type subgrounds: Subgrounds
        """
        self.network = networks[chain_id]()
        self.subgrounds = subgrounds
        self.rubicon_market_light = self.subgrounds.load_subgraph(self.network.rubicon_market_light)
        self.boiler_plate = self.subgrounds.load_subgraph(self.network.boiler_plate)

    ######################################################################
    # data collection 
    ######################################################################

    def get_offers(self, maker = None, pair = None, filled = None, cancelled = None, live = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000): 
        """returns a dataframe of all offers placed on the market contract. allows for the following filters: 

        :param maker: the address of the maker of the offer, defaults to None
        :type maker: str, optional
        :param pair: the address of the pair of the offer, defaults to None. direction of the pair matters and corresponds to the array passed in the following order: [pay_gem, buy_gem]. defaults to None
        :type pair: array, optional
        :param filled: whether the offer has been filled, defaults to None
        :type filled: bool, optional
        :param cancelled: whether the offer has been cancelled, defaults to None
        :type cancelled: bool, optional
        :param live: whether the offer is live, defaults to None
        :type live: bool, optional
        :param pay_gem: the address of the pay_gem of the offer, defaults to None
        :type pay_gem: str, optional
        :param buy_gem: the address of the buy_gem of the offer, defaults to None
        :type buy_gem: str, optional
        :param start_time: the start time of the offer, defaults to None. in unix time
        :type start_time: int, optional
        :param end_time: the end time of the offer, defaults to None. in unix time
        :type end_time: int, optional
        """

        # set the offer entity 
        Offer = self.rubicon_market_light.Offer

        # create the synthetic fields for the offer entity
        Offer.pay_amt_formatted = Offer.pay_amt / 10 ** Offer.pay_gem.decimals
        Offer.buy_amt_formatted = Offer.buy_amt / 10 ** Offer.buy_gem.decimals
        Offer.paid_amt_formatted = Offer.paid_amt / 10 ** Offer.pay_gem.decimals
        Offer.bought_amt_formatted = Offer.bought_amt / 10 ** Offer.buy_gem.decimals

        # for each of the filters, add the filter to the where clause
        # TODO: there is most likely a more elegant way to do the lower case conversion of the variables, probably using a decorator?
        where = []
        if maker is not None:
            maker = maker.lower()
            where.append(Offer.maker == maker)
        # TODO: this should be modified to return all offers for a given pair, not just the given direction
        if pair is not None:
            pair[0] = pair[0].lower()
            pair[1] = pair[1].lower()
            where.append(Offer.pay_gem == pair[0])
            where.append(Offer.buy_gem == pair[1])
        if filled is not None:
            where.append(Offer.filled == filled)
        if cancelled is not None:
            where.append(Offer.cancelled == cancelled)
        if live is not None:
            where.append(Offer.live == live)
        if pay_gem is not None:
            pay_gem = pay_gem.lower()
            where.append(Offer.pay_gem == pay_gem)
        if buy_gem is not None:
            buy_gem = buy_gem.lower()
            where.append(Offer.buy_gem == buy_gem)
        if start_time is not None:
            where.append(Offer.timestamp >= start_time)
        if end_time is not None:
            where.append(Offer.timestamp <= end_time)

        # TODO: this is a current limit of the subgrounds library, it does not support querying all as a funtion option, so a large number must be provided
        # TODO: help a frend, this would be a good pr to add to the subgrounds library :)
        if where == []:
            offers = self.rubicon_market_light.Query.offers(first = first)
        else:
            offers = self.rubicon_market_light.Query.offers(first = first, where = where)

        field_paths = [
            offers.id,
            offers.pay_gem.symbol,
            offers.pay_amt_formatted,
            offers.paid_amt_formatted,
            offers.buy_gem.symbol,
            offers.buy_amt_formatted,
            offers.bought_amt_formatted,
            offers.maker.id,
            offers.transaction.id,
            offers.transaction.timestamp,
            offers.pay_gem.id,
            offers.buy_gem.id,
            offers.pay_amt,
            offers.buy_amt,
            offers.paid_amt, 
            offers.bought_amt
        ]  

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy) 

        return df

    def get_trades(self, taker = None, maker = None, pair = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000): 
        """returns a dataframe of all trades on the market contract. allows for the following filters: 

        :param taker: the address of the taker of the trade, defaults to None
        :type taker: str, optional
        :param maker: the address of the maker of the offer, defaults to None
        :type maker: str, optional
        :param pair: the address of the pair of the offer, defaults to None. direction of the pair matters and corresponds to the array passed in the following order: [pay_gem, buy_gem]. defaults to None
        :type pair: array, optional
        :param filled: whether the offer has been filled, defaults to None
        :type filled: bool, optional
        :param cancelled: whether the offer has been cancelled, defaults to None
        :type cancelled: bool, optional
        :param live: whether the offer is live, defaults to None
        :type live: bool, optional
        :param pay_gem: the address of the pay_gem of the offer, defaults to None
        :type pay_gem: str, optional
        :param buy_gem: the address of the buy_gem of the offer, defaults to None
        :type buy_gem: str, optional
        :param start_time: the start time of the offer, defaults to None. in unix time
        :type start_time: int, optional
        :param end_time: the end time of the offer, defaults to None. in unix time
        :type end_time: int, optional
        """

        # set the trade entity 
        Take = self.rubicon_market_light.Take

        # create the synthetic fields for the trade entity
        Take.pay_amt_formatted = Take.pay_amt / 10 ** Take.pay_gem.decimals
        Take.buy_amt_formatted = Take.buy_amt / 10 ** Take.buy_gem.decimals

        # for each of the filters, add the filter to the where clause
        where = []
        if taker is not None:
            taker = taker.lower()
            where.append(Take.taker == taker)
        if maker is not None:
            maker = maker.lower()
            where.append(Take.maker == maker)
        # TODO: this should be modified to return all offers for a given pair, not just the given direction
        if pair is not None:
            pair[0] = pair[0].lower()
            pair[1] = pair[1].lower()
            where.append(Take.pay_gem == pair[0])
            where.append(Take.buy_gem == pair[1])
        if pay_gem is not None:
            pay_gem = pay_gem.lower()
            where.append(Take.pay_gem == pay_gem)
        if buy_gem is not None:
            buy_gem = buy_gem.lower()
            where.append(Take.buy_gem == buy_gem)
        if start_time is not None:
            where.append(Take.timestamp >= start_time)
        if end_time is not None:
            where.append(Take.timestamp <= end_time)

        # TODO: this is a current limit of the subgrounds library, it does not support querying all as a funtion option, so a large number must be provided
        # TODO: help a frend, this would be a good pr to add to the subgrounds library :)
        if where == []:
            takes = self.rubicon_market_light.Query.takes(first = first)
        else:
            takes = self.rubicon_market_light.Query.takes(first = first, where = where)

        field_paths = [
            takes.id,
            takes.pay_gem.symbol,
            takes.pay_amt_formatted,
            takes.buy_gem.symbol,
            takes.buy_amt_formatted,
            takes.taker.id,
            takes.transaction.id,
            takes.transaction.timestamp,
            takes.pay_gem.id,
            takes.buy_gem.id,
            takes.pay_amt,
            takes.buy_amt,
            takes.offer.id, 
            takes.offer.maker.id
        ]  

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy) 

        return df

    def get_detailed_offers(self, maker = None, pair = None, filled = None, cancelled = None, live = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000): 
            """returns a dataframe of all offers placed on the market contract with price data. allows for the following filters:
            
            :param maker: the address of the maker of the offer, defaults to None
            :type maker: str, optional
            :param pair: the address of the pair of the offer, defaults to None. direction of the pair matters and corresponds to the array passed in the following order: [pay_gem, buy_gem]. defaults to None
            :type pair: array, optional
            :param filled: whether the offer has been filled, defaults to None
            :type filled: bool, optional
            :param cancelled: whether the offer has been cancelled, defaults to None
            :type cancelled: bool, optional
            :param live: whether the offer is live, defaults to None
            :type live: bool, optional
            :param pay_gem: the address of the pay_gem of the offer, defaults to None
            :type pay_gem: str, optional
            :param buy_gem: the address of the buy_gem of the offer, defaults to None
            :type buy_gem: str, optional
            :param start_time: the start time of the offer, defaults to None. in unix time
            :type start_time: int, optional
            :param end_time: the end time of the offer, defaults to None. in unix time
            :type end_time: int, optional
            """

            # set the offer entity 
            Offer = self.boiler_plate.Offer

            # for each of the filters, add the filter to the where clause
            # TODO: there is most likely a more elegant way to do the lower case conversion of the variables, probably using a decorator?
            where = []
            if maker is not None:
                maker = maker.lower()
                where.append(Offer.maker == maker)
            # TODO: this should be modified to return all offers for a given pair, not just the given direction
            if pair is not None:
                pair[0] = pair[0].lower()
                pair[1] = pair[1].lower()
                where.append(Offer.pay_gem == pair[0])
                where.append(Offer.buy_gem == pair[1])
            if filled is not None:
                where.append(Offer.filled == filled)
            if cancelled is not None:
                where.append(Offer.cancelled == cancelled)
            if live is not None:
                where.append(Offer.live == live)
            if pay_gem is not None:
                pay_gem = pay_gem.lower()
                where.append(Offer.pay_gem == pay_gem)
            if buy_gem is not None:
                buy_gem = buy_gem.lower()
                where.append(Offer.buy_gem == buy_gem)
            if start_time is not None:
                where.append(Offer.timestamp >= start_time)
            if end_time is not None:
                where.append(Offer.timestamp <= end_time)

            if where == []:
                offers = self.boiler_plate.Query.offers(first = first)
            else:
                offers = self.boiler_plate.Query.offers(first = first, where = where)

            field_paths = [
                offers.id,
                offers.pay_gem.id,
                offers.pay_amt_formatted,
                offers.pay_amt_usd,
                offers.buy_gem.id,
                offers.buy_amt_formatted,
                offers.buy_amt_usd,
                offers.bought_amt_formatted,
                offers.maker.id,
                offers.transaction.id,
                offers.transaction.timestamp,
                offers.pay_amt,
                offers.buy_amt,
                offers.paid_amt, 
                offers.paid_amt_formatted,
                offers.paid_amt_usd,
                offers.bought_amt,
                offers.bought_amt_formatted,
                offers.bought_amt_usd,
                offers.filled,
                offers.cancelled,
                offers.live,
                offers.removed_timestamp
            ]  

            df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy) 

            return df

    def get_detailed_trades(self, taker = None, maker = None, pair = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000): 
            """returns a dataframe of all trades on the market contract with price data. allows for the following filters: 

            :param taker: the address of the taker of the trade, defaults to None
            :type taker: str, optional
            :param maker: the address of the maker of the offer, defaults to None
            :type maker: str, optional
            :param pair: the address of the pair of the offer, defaults to None. direction of the pair matters and corresponds to the array passed in the following order: [pay_gem, buy_gem]. defaults to None
            :type pair: array, optional
            :param filled: whether the offer has been filled, defaults to None
            :type filled: bool, optional
            :param cancelled: whether the offer has been cancelled, defaults to None
            :type cancelled: bool, optional
            :param live: whether the offer is live, defaults to None
            :type live: bool, optional
            :param pay_gem: the address of the pay_gem of the offer, defaults to None
            :type pay_gem: str, optional
            :param buy_gem: the address of the buy_gem of the offer, defaults to None
            :type buy_gem: str, optional
            :param start_time: the start time of the offer, defaults to None. in unix time
            :type start_time: int, optional
            :param end_time: the end time of the offer, defaults to None. in unix time
            :type end_time: int, optional
            """

            # set the trade entity 
            Take = self.boiler_plate.Take

            # for each of the filters, add the filter to the where clause
            where = []
            if taker is not None:
                taker = taker.lower()
                where.append(Take.taker == taker)
            if maker is not None:
                maker = maker.lower()
                where.append(Take.maker == maker)
            # TODO: this should be modified to return all offers for a given pair, not just the given direction
            if pair is not None:
                pair[0] = pair[0].lower()
                pair[1] = pair[1].lower()
                where.append(Take.pay_gem == pair[0])
                where.append(Take.buy_gem == pair[1])
            if pay_gem is not None:
                pay_gem = pay_gem.lower()
                where.append(Take.pay_gem == pay_gem)
            if buy_gem is not None:
                buy_gem = buy_gem.lower()
                where.append(Take.buy_gem == buy_gem)
            if start_time is not None:
                where.append(Take.timestamp >= start_time)
            if end_time is not None:
                where.append(Take.timestamp <= end_time)

            # TODO: this is a current limit of the subgrounds library, it does not support querying all as a funtion option, so a large number must be provided
            # TODO: help a frend, this would be a good pr to add to the subgrounds library :)
            if where == []:
                takes = self.boiler_plate.Query.takes(first = first)
            else:
                takes = self.boiler_plate.Query.takes(first = first, where = where)

            field_paths = [
                takes.id,
                takes.pay_gem.id,
                takes.pay_amt_formatted,
                takes.pay_amt_usd,
                takes.pay_gem_price,
                takes.buy_gem.id,
                takes.buy_amt_formatted,
                takes.buy_amt_usd,
                takes.buy_gem_price,
                takes.taker.id,
                takes.transaction.id,
                takes.transaction.timestamp,
                takes.pay_amt,
                takes.buy_amt,
                takes.offer.id, 
                takes.offer.maker.id
            ]  

            df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy) 

            return df