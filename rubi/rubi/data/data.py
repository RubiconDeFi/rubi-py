from subgrounds import Subgrounds
from rubi.data.sources.market import MarketData

class Data: 
    """this class acts as the main access point to a variety of data and data tooling for the Rubicon protocol. it acts as a data processing layer built using the subgrounds library and the subgraphs maintained at the follwing repo: https://github.com/RubiconDeFi/rubi-subgraphs
    """

    def __init__(self): 
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        """
        self.subgrounds = Subgrounds()

        # initialize the data sources
        self.market_optimism = MarketData(self.subgrounds, 10)