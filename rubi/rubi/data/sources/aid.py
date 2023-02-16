#from helper import Gas
from .helper import Gas
from subgrounds import Subgrounds
from subgrounds.pagination import ShallowStrategy

from rubi.data.sources.helper import networks

class AidData: 
    """this class acts as the main access point to a variety of data and tooling for MarketAid.sol contracts.
    the MarketAid.sol contracts are meant to be a hub for extended functionality for automated traders on the Rubicon protocol.
    the end goal of this class, and this SDK by extension, is to act as a collaborative platform for the advancement of shared data tooling and analysis.
    """

    def __init__(self, subgrounds, chain_id):
        """constructor method

        :param subgrounds: the subgrounds object
        :type subgrounds: subgrounds.Subgrounds
        :param chain_id: the chain id of the network that is of interest
        :type chain_id: int
        """
        self.network = networks[chain_id]()
        self.subgrounds = subgrounds
        self.market_aid = self.subgrounds.load_subgraph(self.network.market_aid)
    
    def get_aid_history(self, aid, bin_size=60, first=1000000000):
        """this method is used to get all of the asset history for a given aid. it tracks any change in asset balance on the market aid due to a transaction. currently, this is all supported through the event emittals on the market aid contract. any activity not recorded by a covered event will be missed...
        
        :param aid: the address of the market aid that is of interest
        :type aid: str
        :param bin_size: the size of the time bins that are of interest, defaults to 60. this is actually not really used at the moment, so reach out if you have a use case for it
        :type bin_size: int, optional
        :param first: the number of transactions to return, defaults to 1000000000
        :type first: int, optional
        """
        # TODO: we are going to need to extned the information we collect from the subgraph, and possibly modify the subgraph itself, in order to make sure we can account for deposits / withdrawals in any pnl calculation

        AidToken = self.market_aid.AidToken
        AidTokenHistory = self.market_aid.AidTokenHistory

        AidTokenHistory.time_bin = (AidTokenHistory.timestamp // bin_size) * bin_size
        AidTokenHistory.balance_formatted = AidTokenHistory.balance / 10 ** AidTokenHistory.aid_token.token.decimals
        AidTokenHistory.balance_change_formatted = AidTokenHistory.balance_change / 10 ** AidTokenHistory.aid_token.token.decimals

        histories = self.market_aid.Query.aidTokenHistories(first = first, where = [AidToken.aid == aid.lower()])

        field_paths = [
            histories.timestamp,
            histories.time_bin,
            histories.aid_token.token.symbol,
            histories.balance_formatted,
            histories.balance_change_formatted,
            histories.transaction.id
        ]

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy)

        return df

    # TODO: issue #19 dealing with filtering nested entities, that or modify the subgraph so that we can filter by timestamp
    def get_aid_offers(self, aid=None, pair=None, pay_gem=None, buy_gem=None, start_time=None, end_time=None, first=1000000000):
        # TODO: figure out if we want to filter by token symbol or token address, or both
        # address is going to be network specific, but if we are losing the ability to use the symbol through the subgraph then we will need to change several things in the SDK :( 
        """this method is used to get all of the offers for a given aid that have been tracked through the market aid subgraph. https://github.com/RubiconDeFi/rubi-subgraphs

        # relevant issue: need to add filtering for pay_gem, buy_gem, start_time, end_time either through added functionality in subgrounds for nested filtering or through the underlying subgraph 
        # i am currently hesistant to do much with expected changes that will occur to the subgraph schema that will necessitate changes here as well
        # if you are reading this, we are moving to event only based subgraphs x0

        :param aid: the address of the market aid that is of interest
        :type aid: str
        :param pay_gem: the address of the pay gem that is of interest
        :type pay_gem: str
        :param buy_gem: the address of the buy gem that is of interest
        :type buy_gem: str
        :param start_time: the start time of the time range that is of interest, defaults to None
        :type start_time: int, optional
        :param end_time: the end time of the time range that is of interest, defaults to None
        :type end_time: int, optional
        :param first: the number of offers to return, defaults to 1000000000
        :type first: int, optional
        """

        Offer = self.market_aid.Offer
        Offer.pay_amt_formatted = Offer.pay_amt / 10 ** Offer.pay_gem.decimals
        Offer.buy_amt_formatted = Offer.buy_amt / 10 ** Offer.buy_gem.decimals
        Offer.paid_amt_formatted = Offer.paid_amt / 10 ** Offer.pay_gem.decimals
        Offer.bought_amt_formatted = Offer.bought_amt / 10 ** Offer.buy_gem.decimals

        where = []
        if aid:
            where.append(Offer.maker == aid.lower())
        #if pair:
        #    where.append(Offer.pair == pair.lower())
        #if pay_gem:
        #    where.append(Offer.pay_gem == pay_gem.lower())
        #if buy_gem:
        #    where.append(Offer.buy_gem == buy_gem.lower())
        #if start_time:
        #    where.append(Offer.timestamp >= start_time)
        #if end_time:
        #    where.append(Offer.timestamp <= end_time)

        if where:
            offers = self.market_aid.Query.offers(first = first, where = where)
        else:
            offers = self.market_aid.Query.offers(first = first)
        
        field_paths = [
            offers.id,
            offers.transaction.timestamp,
            offers.removed_timestamp,
            offers.pay_gem.symbol,
            offers.pay_amt_formatted,
            offers.paid_amt_formatted,
            offers.buy_gem.symbol,
            offers.buy_amt_formatted,
            offers.bought_amt_formatted,
            offers.pay_gem.id,
            offers.buy_gem.id,
            offers.live
        ]

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy)

        return df

    def get_aid_txns(self, aid=None, start_time=None, end_time=None, first=1000000000): 
        """this method is used to get all of the transactions for a given aid that have been tracked through the market aid subgraph. https://github.com/RubiconDeFi/rubi-subgraphs
        
        :param aid: the address of the market aid that is of interest, defaults to None
        :type aid: str, optional
        :param start_time: the start time of the time range that is of interest, defaults to None
        :type start_time: int, optional
        :param end_time: the end time of the time range that is of interest, defaults to None
        :type end_time: int, optional
        :param first: the number of transactions to return, defaults to 1000000000
        :type first: int, optional
        """

        Transaction = self.market_aid.Transaction

        where = []
        if aid:
            where.append(Transaction.aid == aid)
        if start_time:
            where.append(Transaction.timestamp >= start_time)
        if end_time:
            where.append(Transaction.timestamp <= end_time)

        if where == []:
            txns = self.market_aid.Query.transactions(first=first)
        else:
            txns = self.market_aid.Query.transactions(first=first, where=where)

        field_paths = [
            txns.id,
            txns.timestamp,
            txns.aid.id
        ]

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy)

        return df

class SuperAidData(AidData): 
    """this class acts as an extension of the AidData class and has some additional functionality that is enabled by a node connection. 
    """

    def __init__(self, w3, subgrounds, chain_id):
        """a super class of the AidData class that has additional functionality enabled by a node connection.

        :param w3: a web3 object
        :type w3: web3.main.Web3
        :param subgrounds: the subgrounds object
        :type subgrounds: subgrounds.Subgrounds
        :param chain_id: the chain id of the network that is of interest
        :type chain_id: int
        """
        super().__init__(subgrounds, chain_id)

        # set class variables
        self.w3 = w3
        self.gas = Gas(self.w3)
    
    def get_aid_txns_gas_data(self, aid=None, start_time=None, end_time=None, total_fee_eth=True, total_fee_usd=True, l2_gas_price=None, l2_gas_used=None, l1_gas_used=None, 
        l1_gas_price=None, l1_fee_scalar=None, l1_fee=None, l2_fee=None, total_fee=None, l1_fee_eth=None, l2_fee_eth=None, eth_price=None, l1_fee_usd=None, l2_fee_usd=None, first=1000000000):

        # get the transactions for the market aid contract
        txns = self.get_aid_txns(aid, start_time, end_time, first)
    
        # update the dataframe to contain the relevant gas data
        df = self.gas.txn_dataframe_update(txns, 'transactions_id', 'transactions_timestamp', total_fee_eth = total_fee_eth, total_fee_usd = total_fee_usd, l2_gas_price = l2_gas_price, l2_gas_used = l2_gas_used, l1_gas_used = l1_gas_used, l1_gas_price = l1_gas_price, l1_fee_scalar = l1_fee_scalar, l1_fee = l1_fee, l2_fee = l2_fee, total_fee = total_fee, l1_fee_eth = l1_fee_eth, l2_fee_eth = l2_fee_eth, eth_price = eth_price, l1_fee_usd = l1_fee_usd, l2_fee_usd = l2_fee_usd)

        return df 

    def get_aid_gas_spend_binned(self, aid=None, start_time=None, end_time=None, granularity=60, type = 'USD', total_fee_eth=True, total_fee_usd=True, l2_gas_price=None, l2_gas_used=None, l1_gas_used=None, 
        l1_gas_price=None, l1_fee_scalar=None, l1_fee=None, l2_fee=None, total_fee=None, l1_fee_eth=None, l2_fee_eth=None, eth_price=None, l1_fee_usd=None, l2_fee_usd=None, first=1000000000):
        """this function takes in a market aid address, start time, end time, and granularity in order to return a dictionary of the gas spend dictionary that is binned by the granularity.
        this dictionary is a key-pair mapping of the time bin (start of a minute, hour, day, etc) to the gas spend of the contract during that period.
        """

        if start_time: 
            start_time = int(start_time)
        if end_time:
            end_time = int(end_time)

        gas_spend = self.get_aid_txns_gas_data(aid, start_time, end_time, total_fee_eth, total_fee_usd, l2_gas_price, l2_gas_used, l1_gas_used, l1_gas_price, l1_fee_scalar, l1_fee, l2_fee, total_fee, l1_fee_eth, l2_fee_eth, eth_price, l1_fee_usd, l2_fee_usd, first)

        # bin the data
        gas_spend['time_bin'] = gas_spend['transactions_timestamp'].apply(lambda x: (x // granularity) * granularity)

        # group by time_bin and get the aggregate gas spend during the period represented as a dictionary with time_bin as the key and the gas spend as the value
        grouped = gas_spend.groupby(['time_bin'])

        if type == 'USD':
            gas_spend = grouped['total_fee_usd'].sum().to_dict()

        if type == 'ETH':
            gas_spend = grouped['total_fee_eth'].sum().to_dict()

        return gas_spend

