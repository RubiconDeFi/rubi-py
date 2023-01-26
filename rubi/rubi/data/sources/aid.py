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
    def get_aid_history(self, aid=None, first=1000000000):

        Aid = self.market_aid.Aid
        AidToken = self.market_aid.AidToken
        AidTokenHistory = self.market_aid.AidTokenHistory

        AidToken.balance_formatted = AidToken.balance / 10 ** AidToken.token.decimals
        AidTokenHistory.balance_formatted = AidTokenHistory.balance / 10 ** AidTokenHistory.aid_token.token.decimals
        AidTokenHistory.balance_change_formatted = AidTokenHistory.balance_change / 10 ** AidTokenHistory.aid_token.token.decimals

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

        df = self.market_aid.query_df(field_paths, pagination_strategy=ShallowStrategy)
        
        return df