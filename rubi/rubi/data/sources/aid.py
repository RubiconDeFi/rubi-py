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
    
    # TODO: improvement outlined in issue #19
    def get_aid_history(self, aid=None, bin_size=None, first=1000000000):

        Aid = self.market_aid.Aid
        AidToken = self.market_aid.AidToken
        AidTokenHistory = self.market_aid.AidTokenHistory

        AidToken.balance_formatted = AidToken.balance / 10 ** AidToken.token.decimals
        AidTokenHistory.balance_formatted = AidTokenHistory.balance / 10 ** AidTokenHistory.aid_token.token.decimals
        AidTokenHistory.balance_change_formatted = AidTokenHistory.balance_change / 10 ** AidTokenHistory.aid_token.token.decimals

        # if the user wants to bin the data, create the bin field
        if bin_size:
            AidTokenHistory.time_bin = ((AidTokenHistory.timestamp // bin_size) * bin_size)

        where = []
        if aid:
            where.append(Aid.id == aid)
        
        if where == []:
            aids = self.market_aid.Query.aids(first=first)
        else:
            aids = self.market_aid.Query.aids(first=first, where=where)

        field_paths = [
            aids.id,
            aids.balances.token.id,
            aids.balances.token.symbol,
            aids.balances.history.timestamp,
            aids.balances.history.balance_formatted,
            aids.balances.history.balance_change_formatted,
            aids.balances.history.balance_change
        ]

        if bin_size:
            field_paths.append(aids.balances.history.time_bin)

        df = self.subgrounds.query_df(field_paths, pagination_strategy=ShallowStrategy)
        
        return df

    def get_aid_txns(self, aid=None, start_time=None, end_time=None, first=1000000000): 

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

