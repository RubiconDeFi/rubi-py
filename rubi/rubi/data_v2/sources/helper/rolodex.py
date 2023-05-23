
class Rolodex:
    """this class represents a rolodex of useful addresses, endpoints, and other information that is commonly used"""

    def __init__(self):

        # set the v2 subgraph endpoints
        self.optimism_mainnet_rubicon_v2 = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconv2-optimism-mainnet'
        self.optimism_goerli_rubicon_v2 = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconv2-optimism-goerli'
        self.arbitrum_goerli_rubicon_v2 = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconv2-arbitrum-goerli'
        self.polygon_mumbai_rubicon_v2 = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconv2-polygon-mumbai'

        # set the market aid endpoints
        self.market_aid_optimism_mainnet = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/optimismmarketaid'