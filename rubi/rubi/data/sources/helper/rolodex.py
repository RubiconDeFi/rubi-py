import os
import json

class OptimismMainnet:
    """this class represents a rolodex of relevant informatino regarding the Optimism Mainnet network, such as contract addresses, token addresses, and abis."""

    # TODO: set these to be dynamically pulled in a trustless fashion
    def __init__(self):
        self.network = 'Optimism'
        self.chain_id = 10
        self.currency = 'ETH'
        self.rpc_url = 'https://mainnet.optimism.io'
        self.explorer_url = 'https://optimistic.etherscan.io'
        
        # set the rubicon contract addresses
        self.market = '0x7a512d3609211e719737E82c7bb7271eC05Da70d'
        self.router = '0x7Af14ADc8Aea70f063c7eA3B2C1AD0D7A59C4bFf'
        self.pair = '0xF8780E00Ce8ed2e79aeC10908a169900eD1D4AFe'
        self.factory = '0x267D94C6e67e4436EFfE092b08d040cFF36B2DA7'

        # set up some common asset addresses that may be used 
        # TODO: it would be nice to be able to dynamically pull in a token list in a trustless fashion and populate this list
        self.eth = '0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000'
        self.weth = '0x4200000000000000000000000000000000000006'
        self.wbtc = '0x68f180fcCe6836688e9084f035309E29Bf0A2095'
        self.usdc = '0x7F5c764cBc14f9669B88837ca1490cCa17c31607'
        self.dai = '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
        self.usdt = '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'
        self.snx = '0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4'
        self.op = '0x4200000000000000000000000000000000000042'

        # set the subgraph query endpoints
        # TODO: this will been to be updated in the future to deal with GRT payments for subgraph queries
        # it would be nice if through this SDK we managed a synergistic relationship between queriers, for common queries that are supported in the SDK 
        # we could possibly hash the most recent query response to an IPFS instance that is then udpated by subsequent qureries, negating the need to query the entire history 
        # of the subgraph, and only querying, and paying, for the most recent data. 
        self.rubicon_market_light = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconmarket-light-optimism'
        # self.rubicon_metrics = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconmetricsoptimism'
        self.boiler_plate = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/boilerplateoptimism'

        # create a dictionary of token addresses and symbols to be mapped to a coinbase usd base ticker
        self.coinbase_tickers = {
            '0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000': 'ETH-USD',
            '0x68f180fcCe6836688e9084f035309E29Bf0A2095': 'BTC-USD',
            '0x7F5c764cBc14f9669B88837ca1490cCa17c31607': 'USDC-USD',
            '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1': 'DAI-USD',
            '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58': 'USDT-USD',
            '0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4': 'SNX-USD',
            '0x4200000000000000000000000000000000000042': 'OP-USD', 
            'ETH': 'ETH-USD',
            'WETH': 'ETH-USD',
            'WBTC': 'BTC-USD',
            'USDC': 'USDC-USD',
            'DAI': 'DAI-USD',
            'USDT': 'USDT-USD',
            'SNX': 'SNX-USD',
            'OP': 'OP-USD'
        }
        
    ######################################################################
    # sure there is plenty of helpful things we can do here in the future ;)
    ######################################################################

    # create some type of token list dictionary that can be used to dynamically pull in token addresses and information

class OptimismGoerli:
    """this class represents a rolodex of relevant informatino regarding the Optimism Goerli network, such as contract addresses, token addresses, and abis."""

    # TODO: set these to be dynamically pulled in a trustless fashion
    def __init__(self):
        """Initialize the Optimism Mainnet class."""
        self.network = 'Optimism Goerli'
        self.chain_id = 420
        self.currency = 'ETH'
        self.rpc_url = 'https://goerli.optimism.io'
        self.explorer_url = 'https://goerli-explorer.optimism.io/'

        # set the rubicon contract addresses
        self.market = '0x6cD8666aBB003073e45D69E5b3aa0b0Fe9CDBF91'
        self.router = '0x6aaEd1985a0e011ca82BB5Df8ebd92063134fd7c'
        self.house = '0x1229036F63679B61910CB1463e5BB57f68D19bb2'
        self.pair = '0x9dBf17d518f722B5Aae5573D808B94024b635529'
        self.utility = '0xd282dB449cC64D136b9D9a4399E7e3F133472EaE'
        self.factory = '0x6838dd21aa01Bde8E600d499A95f9AE02f2bB376'

        # set the subgraph query endpoints
        self.rubicon_market_light = 'https://api.thegraph.com/subgraphs/name/denverbaumgartner/rubiconmarket-light-op-goerli'

        # set up some common asset addresses that may be used 
        # TODO: it would be nice to be able to dynamically pull in a token list in a trustless fashion and populate this list
        self.eth = '0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000'
        self.weth = '0x4200000000000000000000000000000000000006'
        self.op = '0xCeE7148028Ff1B08163343794E85883174a61393'
        self.usdc = '0x708394f89acd3E0644f774EA6c876BFACE70e600'

        ######################################################################
        # sure there is plenty of helpful things we can do here in the future ;)
        ######################################################################

# set a dictionary that maps the chain id to the network class
networks = {
    10: OptimismMainnet,
    420: OptimismGoerli
}