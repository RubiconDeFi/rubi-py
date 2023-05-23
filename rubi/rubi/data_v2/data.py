from subgrounds import Subgrounds

from rubi.data_v2.sources.market import MarketData

class Data: 
    """this class is intended to be the access point for on chain data, with a majority of it in its current state being related to the handling of subgraph data (https://github.com/RubiconDeFi/rubi-subgraphs)"""

    def __init__(self):
        """constructor method, handles the initialization of the subgrounds object
        """
        
        self.subgrounds = Subgrounds()
        self.market = MarketData(self.subgrounds)


# test that things run as expected 

data = Data()

# get the offers 
offers = data.market.get_offers(first = 1000)
trades = data.market.get_trades(first = 1000)

print(offers.head())
print(trades.head())

print('here are the columns for offers and trades:')
print(offers.columns)
print(trades.columns)