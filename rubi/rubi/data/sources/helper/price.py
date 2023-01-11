import time
import requests

class Price: 
    """Price helper class"""

    def __init__(self):
        """constructor for the price helper class
        
        :param w3: a web3 instance
        :type w3: Web3 object
        """
        self.eth_price = 0

    def get_coinbase_price(self, pair='ETH-USD', date=None): 
        """this function takes a pair and returns the current spot price for the pair from coinbase, if no date is provided
        
        :param pair: the pair to get the price for ('ETH-USD')
        :type pair: str
        :param date: the date to get the price for (YYYY-MM-DD), or converts unix timestamp to date
        :type date: str
        :return: a dictionary of the price data {'base': 'ETH', 'currency': 'USD', 'amount': '1234.56', 'time': 1673477434}
        :rtype: dict
        """

        if date and type(date) == int:
            query_date = time.strftime('%Y-%m-%d %H:%M:%S')

        if date:
            url = f'https://api.coinbase.com/v2/prices/{pair}/spot?date={query_date}'
        else:
            date = int(time.time())
            url = f'https://api.coinbase.com/v2/prices/{pair}/spot'
        
        # get the response from the api
        try:
            response = requests.get(url).json()['data']
            response['time'] = date
            response['amount'] = float(response['amount'])
        except:
            return None

        return response

    def get_defi_llama_price(self, network='ethereum', address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', timestamp=None):
        """this function takes a network and address and returns the current spot price for the token from defi llama, if no timestamp is provided. if a timestamp is provided, it will return the price at that time.
        
        :param network: the network to get the price for ('ethereum')
        :type network: str
        :param address: the address to get the price for (mainnet weth -> '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
        :type address: str
        :param timestamp: the timestamp to get the price for (unix timestamp)
        :type timestamp: int, optional
        :return: a dictionary of the price data {'base': 'ETH', 'currency': 'USD', 'amount': '1234.56', 'time': 1673477434}
        :rtype: dict
        """

        coins = f'{network}:{address}'

        if timestamp: 
            timestamp = int(timestamp)
            url = f'https://coins.llama.fi/prices/historical/{timestamp}/{coins}'
        else:
            url = f"https://coins.llama.fi/prices/current/{coins}"

        # get the response from the api
        try:
            response = requests.get(url).json()['coins'][coins]
        except: 
            return None

        # TODO: add in confidence check
        #if response['confidence'] < 0.9:
        #    return None
        #else: 
        return {'base': response['symbol'], 'currency': 'USD', 'amount': response['price'], 'time': response['timestamp']}
