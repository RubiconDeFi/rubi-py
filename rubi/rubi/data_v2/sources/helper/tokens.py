# the main goal here is to handle accessing and formatting token lists for various networks, this will very much be a work in progress as we learn the best way to manage this as we scale
# for now, i think it makes the most sense to handle this on a per network basis, and then maybe we expand it in the future 
import requests
import polars as pl

class TokenList:
    """this class acts as an access point for token lists from various sources"""

    def get_optimism_token_list(network = 'optimism'):

        networks = {
            'ethereum' : [1], 
            'goerli' : [69],
            'optimism' : [10], 
            'optimism_goerli' : [42],
            'all' : [1, 69, 10, 42]
        }

        # check that the network parameter is valid
        if network not in list(networks.keys()):
            raise ValueError("Invalid network, must be 'ethereum', 'goerli', 'optimism', 'optimism_goerli', or 'all'")

        # load in the optimism token list
        url = 'https://raw.githubusercontent.com/ethereum-optimism/ethereum-optimism.github.io/7b9a11f40f6dddb4c50848f1d84ffdb03ab47bfb/optimism.tokenlist.json'
        data = requests.get(url).json()

        # Create the DataFrame with list comprehension, filtering chainId == 10 and lowercasing addresses
        token_list = pl.DataFrame(
            {
                'address': [token['address'].lower() for token in data['tokens'] if token['chainId'] in networks[network]],
                'symbol': [token['symbol'] for token in data['tokens'] if token['chainId'] in networks[network]],
                'decimals': [token['decimals'] for token in data['tokens'] if token['chainId'] in networks[network]],
                'chain_id': [token['chainId'] for token in data['tokens'] if token['chainId'] in networks[network]]
            }
        )

        return token_list