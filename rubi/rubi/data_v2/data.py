from subgrounds import Subgrounds

class Data: 
    """this class is intended to be the access point for on chain data, with a majority of it in its current state being related to the handling of subgraph data (https://github.com/RubiconDeFi/rubi-subgraphs)"""

    def __init__(self):
        """constructor method, handles the initialization of the subgrounds object
        """
        
        self.subgrounds = Subgrounds()