from subgrounds import Subgrounds
from rubi.data.sources.aid import AidData, SuperAidData
from rubi.data.sources.market import MarketData
from rubi.data.sources.helper import Gas, Price, networks 
from rubi.data.processing.user import User, SuperUser
from rubi.data.processing.aid import AidProcessing

class Data: 
    """this class acts as the main access point to a variety of data and data tooling for the Rubicon protocol. it acts as a data processing layer built using the subgrounds library and the subgraphs maintained at the follwing repo: https://github.com/RubiconDeFi/rubi-subgraphs
    """

    def __init__(self, super=False): 
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling

        :param super: whether the data object is a super data object, defaults to False
        :type super: bool, optional
        """
        self.subgrounds = Subgrounds()
        self.price = Price()
        self.networks = networks

        # initialize the data sources
        self.market_optimism = MarketData(self.subgrounds, 10)
        self.market_optimism_goerli = MarketData(self.subgrounds, 420)
        
        # initialize the data processing if the data object is not a super data object
        if not super:
            self.user = User(self.subgrounds, self.market_optimism)
            self.market_aid_optimism = AidData(self.subgrounds, 10) 
            self.market_aid_optimism_goerli = AidData(self.subgrounds, 420)

            # TODO: we most likely want to rearrange this so that the processing class uses the AidData class as a parent class
            # this issue here is that we are using a parent/child relationship already to distinguish between a web3 enabled data object and a non web3 enabled data object
            # we should probably simplify this to just use a conditional statement to determine whether or not we are using a web3 enabled data object
            # if anyone has a lot of thoughts here please feel free to open an issue on the repo :)
            self.market_aid_optimism_processing = AidProcessing(self.subgrounds, 10, self.market_aid_optimism)
            self.market_aid_optimism_goerli_processing = AidProcessing(self.subgrounds, 420, self.market_aid_optimism_goerli)

class SuperData(Data):
    """this class acts as an extension of the data class with additional functionality that is enabled by being connected to a node. 
    """

    def __init__(self, w3): 
        """constructor method. creates a subgrounds object that is then used to initialize a variety of data sources and tooling
        """

        # initialize the data class
        super().__init__(super=True)

        # set class variables
        self.w3 = w3
        self.gas = Gas(self.w3)

        # initialize the data processing
        self.user = SuperUser(self.w3, self.subgrounds, self.market_optimism)
        
        # TODO: see if there is a more ellegant want to do this, we are going to split these based upon which network we are on 
        chain = w3.eth.chain_id

        if chain == 10:
            self.market_aid_optimism = SuperAidData(self.w3, self.subgrounds, 10) 
            self.market_aid_optimism_goerli = AidData(self.subgrounds, 420)

            self.market_aid_optimism_processing = AidProcessing(self.subgrounds, 10, self.market_aid_optimism)
            self.market_aid_optimism_goerli_processing = AidProcessing(self.subgrounds, 420, self.market_aid_optimism_goerli)
        elif chain == 420:
            self.market_aid_optimism = AidData(self.subgrounds, 10) 
            self.market_aid_optimism_goerli = SuperAidData(self.w3, self.subgrounds, 420)

            self.market_aid_optimism_processing = AidProcessing(self.subgrounds, 10, self.market_aid_optimism)
            self.market_aid_optimism_goerli_processing = AidProcessing(self.subgrounds, 420, self.market_aid_optimism_goerli)