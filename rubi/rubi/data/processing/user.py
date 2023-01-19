import pandas as pd
from ..sources import MarketData
from ..sources.helper import Gas, Price, networks

class User:
    """this class acts as the entry point for accessing data specific to a user or series of users. it is used to create a user data object that can be used to access a variety of data sources and tooling. more to come soon!
    """

    def __init__(self, subgrounds, MarketDataOP):
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        
        :param subgrounds: a subgrounds object
        :type subgrounds: subgrounds.Subgrounds
        :param MarketDataOP: a market data object for the optimism network
        :type MarketDataOP: rubi.data.sources.market.MarketData
        """
        
        self.network = networks
        self.subgrounds = subgrounds
        self.market_optimism = MarketDataOP

    def get_user_trading_transactions(self, user, pair = None, filled = None, cancelled = None, live = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000):
        # TODO: all aggregate functions will need to be modified in a multi-chain world :soon: hehe ;)
        """this function is used to return a dataframe of a user's trading activity transactions. it returns a dataframe containing the user's offers and takes transactions on the market.
        
        :param user: the user's wallet address
        :type user: str
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
        :param start_time: the start time of the offer, defaults to None
        :type start_time: int, optional
        :param end_time: the end time of the offer, defaults to None
        :type end_time: int, optional
        :return: a dataframe containing the user's offers and takes
        :rtype: pandas.DataFrame
        """

        op_offers = self.market_optimism.get_offers(maker = user, pair = pair, filled = filled, cancelled = cancelled, live = live, pay_gem = pay_gem, buy_gem = buy_gem, start_time = start_time, end_time = end_time, first = first)
        op_trades = self.market_optimism.get_trades(taker = user, pair = pair, pay_gem = pay_gem, buy_gem = buy_gem, start_time = start_time, end_time = end_time, first = first)

        if op_offers.empty: 
            op_offers = pd.DataFrame(columns=['offers_maker_id', 'offers_transaction_id', 'offers_transaction_timestamp'])
        if op_trades.empty:
            op_trades = pd.DataFrame(columns=['takes_taker_id', 'takes_transaction_id', 'takes_transaction_timestamp'])

        # transform the dataframe column names so they can be merged
        #df.rename(columns={'A': 'a', 'B': 'b', 'C': 'c'}, inplace=True)
        op_offers.rename(columns={
            'offers_maker_id' : 'user',
            'offers_transaction_id' : 'transaction_hash',
            'offers_transaction_timestamp' : 'transaction_timestamp'
        }, inplace=True)

        op_trades.rename(columns={
            'takes_taker_id' : 'user',
            'takes_transaction_id' : 'transaction_hash',
            'takes_transaction_timestamp' : 'transaction_timestamp'
        }, inplace=True)

        # add a column that labels the transaction as an offer or a trade
        op_offers = op_offers.assign(transaction_type='offer')
        op_trades = op_trades.assign(transaction_type='trade')

        # subset the offers and trades dataframes to only include the relevant columns
        op_offers = op_offers[['user', 'transaction_hash', 'transaction_timestamp', 'transaction_type']]
        op_trades = op_trades[['user', 'transaction_hash', 'transaction_timestamp', 'transaction_type']]

        # merge the offers and trades dataframes
        df = pd.concat([op_offers, op_trades])
        # TODO: reset the index
        df.drop_duplicates(inplace=True)

        return df

class SuperUser(User): 
    """this class acts as an extension of the user class with additional functionality that is enabled by being connected to a node. 
    """

    def __init__(self, w3, subgrounds, MarketDataOP):
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        
        :param w3: a web3 object
        :type w3: web3.main.Web3
        :param subgrounds: a subgrounds object
        :type subgrounds: subgrounds.Subgrounds
        :param MarketDataOP: a market data object for the optimism network
        :type MarketDataOP: rubi.data.sources.market.MarketData
        """
        
        # initialize the user class
        super().__init__(subgrounds, MarketDataOP)

        # set class variables
        self.w3 = w3
        self.gas = Gas(self.w3)

    def get_user_trading_gas_spend(self, user, pair = None, filled = None, cancelled = None, live = None, pay_gem = None, buy_gem = None, start_time = None, end_time = None, first = 1000000000,
        total_fee_eth = True, total_fee_usd = True, l2_gas_price = False, l2_gas_used = False, l1_gas_used = False, l1_gas_price = False, l1_fee_scalar = False, l1_fee = False, l2_fee = False, total_fee = False, l1_fee_eth = False, l2_fee_eth = False, eth_price = False, l1_fee_usd = False, l2_fee_usd = False):
        """this function is used to return a dataframe of a user's trading activity transactions. it returns a dataframe containing the user's offers and takes transactions on the market, along with relevant gas data for the transactions.
        
        :param user: the user's wallet address
        :type user: str
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
        :param start_time: the start time of the offer, defaults to None
        :type start_time: int, optional
        :param end_time: the end time of the offer, defaults to None
        :type end_time: int, optional
        :param first: the number of transactions to return, defaults to 1000000000
        :type first: int, optional
        :param total_fee_eth: whether to include the total fee in eth, defaults to True
        :type total_fee_eth: bool, optional
        :param total_fee_usd: whether to include the total fee in usd, defaults to True
        :type total_fee_usd: bool, optional
        :param l2_gas_price: whether to include the l2 gas price, defaults to False
        :type l2_gas_price: bool, optional
        :param l2_gas_used: whether to include the l2 gas used, defaults to False
        :type l2_gas_used: bool, optional
        :param l1_gas_used: whether to include the l1 gas used, defaults to False
        :type l1_gas_used: bool, optional
        :param l1_gas_price: whether to include the l1 gas price, defaults to False
        :type l1_gas_price: bool, optional
        :param l1_fee_scalar: whether to include the l1 fee scalar, defaults to False
        :type l1_fee_scalar: bool, optional
        :param l1_fee: whether to include the l1 fee, defaults to False
        :type l1_fee: bool, optional
        :param l2_fee: whether to include the l2 fee, defaults to False
        :type l2_fee: bool, optional
        :param total_fee: whether to include the total fee, defaults to False
        :type total_fee: bool, optional
        :param l1_fee_eth: whether to include the l1 fee in eth, defaults to False
        :type l1_fee_eth: bool, optional
        :param l2_fee_eth: whether to include the l2 fee in eth, defaults to False
        :type l2_fee_eth: bool, optional
        :param eth_price: whether to include the eth price, defaults to False
        :type eth_price: bool, optional
        :param l1_fee_usd: whether to include the l1 fee in usd, defaults to False
        :type l1_fee_usd: bool, optional
        :param l2_fee_usd: whether to include the l2 fee in usd, defaults to False
        :type l2_fee_usd: bool, optional
        :return: a dataframe containing the user's offers and takes
        :rtype: pandas.DataFrame
        """

        # get the user's trading transactions
        df = self.get_user_trading_transactions(user, pair = pair, filled = filled, cancelled = cancelled, live = live, pay_gem = pay_gem, buy_gem = buy_gem, start_time = start_time, end_time = end_time, first = first)

        # update the dataframe to contain the relevant gas data
        df = self.gas.txn_dataframe_update(df, 'transaction_hash', 'transaction_timestamp', total_fee_eth = total_fee_eth, total_fee_usd = total_fee_usd, l2_gas_price = l2_gas_price, l2_gas_used = l2_gas_used, l1_gas_used = l1_gas_used, l1_gas_price = l1_gas_price, l1_fee_scalar = l1_fee_scalar, l1_fee = l1_fee, l2_fee = l2_fee, total_fee = total_fee, l1_fee_eth = l1_fee_eth, l2_fee_eth = l2_fee_eth, eth_price = eth_price, l1_fee_usd = l1_fee_usd, l2_fee_usd = l2_fee_usd)

        return df