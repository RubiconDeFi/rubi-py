from subgrounds import Subgrounds
from rubi.data.sources.market import MarketData
from rubi.data.sources.helper import Gas, Price, networks 

class Data: 
    """this class acts as the main access point to a variety of data and data tooling for the Rubicon protocol. it acts as a data processing layer built using the subgrounds library and the subgraphs maintained at the follwing repo: https://github.com/RubiconDeFi/rubi-subgraphs
    """

    def __init__(self): 
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        """
        self.subgrounds = Subgrounds()
        self.price = Price()
        self.networks = networks

        # initialize the data sources
        self.market_optimism = MarketData(self.subgrounds, 10)

class SuperData(Data):
    """this class acts as an extension of the data class with additional functionality that is enabled by being connected to a node. 
    """

    def __init__(self, w3): 
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        """

        # initialize the data class
        super().__init__()

        # set class variables
        self.w3 = w3
        self.gas = Gas(self.w3)