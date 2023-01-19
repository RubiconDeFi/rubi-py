import time
import requests
import asyncio
import aiohttp

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

    async def get_price(self, pair, granularity, start, end, price_type='open'):
        """the get_price function will take in a pair, granularity, and timestamp and return a price for the pair at the specified timestamp. this is done by gathering historical data from coinbase's OHLC historical data api

        :param pair: the pair to get the price for ('ETH-USD')
        :type pair: str
        :param granularity: the granularity of the data to get (60)
        :type granularity: int
        :param start: the start of the time range to get the price for (unix timestamp)
        :type start: int
        :param end: the end of the time range to get the price for (unix timestamp)
        :type end: int
        :param price_type: the type of price to get (open, high, low, close)
        :type price_type: str, optional
        :return: the price for the pair at the specified timestamp
        :rtype: float
        """

        # TODO: we will need to enable the end user to specify what data from the candle they want
        url = f"https://api.pro.coinbase.com/products/{pair}/candles?granularity={granularity}&start={start}&end={end}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp: 
                    
                    data = await resp.json()

                    # TODO: we will want to enable retry logic here where the time range is incrementally stepped out until we get a response
                    # we will need to determine what the maximum amount of retries is and ensure we do not exceed that

                    if price_type == 'open':
                        price = data[0][3]
                    elif price_type == 'high':
                        price = data[0][2]
                    elif price_type == 'low':
                        price = data[0][1]
                    elif price_type == 'close':
                        price = data[0][4]

                    return price

            except aiohttp.ClientError as e:
                raise Exception(f"Failed to retrieve data due to client error: {e}")
            except Exception as e:
                raise Exception(f"Failed to retrieve data due to error: {e}")

    async def get_prices(self, pairs, granularities, starts, ends, price_type='open'):
        # TODO: there is currently no way to actually pass in the price_type parameter currently, we will need to add that in. if anyone else wants to do that, i will send you a hand drawn nft for your efforts :)
        """the get_prices function will take in a list of pairs, granularities, and timestamps and return a list of prices for each pair at the specified timestamp. this is done by gathering historical data from coinbase's OHLC historical data api

        :param pairs: a list of pairs to retrieve prices for, for example ['ETH-USD', 'ETH-USD', 'ETH-USD']
        :type pairs: list, str
        :param granularities: a list of granularities to retrieve prices for, for example [60, 60, 60]
        :type granularities: list, int
        :param starts: a list of start timestamps for the range of candles one would like to retrieve prices for, for example [1673931600, 1673931600, 1673931600]
        :type starts: list, int
        :param ends: a list of end timestamps for the range of candles one would like to retrieve prices for, for example [1673931600, 1673931600, 1673931600]
        :type ends: list, int
        :param price_type: the type of price to retrieve, for example 'open', 'high', 'low', 'close'
        :type price_type: str
        :return: a list of prices for each pair at the specified timestamp
        :rtype: list, float
        """

        tasks = [self.get_price(pair, granularity, start, end) for pair, granularity, start, end in zip(pairs, granularities, starts, ends)]

        try:
            prices = await asyncio.gather(*tasks)
        except Exception as e:
            raise Exception(f"Failed to retrieve prices due to error: {e}")

        return prices

    def retrieve_prices(self, pairs, granularities, timestamps, price_type='open'):
        """the retrieve_prices function will take in a list of pairs, granularities, and timestamps and return a list of prices for each pair at the specified timestamp. this is done by gathering historical data from coinbase's OHLC historical data api

        :param pairs: a list of pairs to retrieve prices for, for example ['ETH-USD', 'ETH-USD', 'ETH-USD']
        :type pairs: list, str
        :param granularities: a list of granularities to retrieve prices for, for example [60, 60, 60]
        :type granularities: list, int
        :param timestamps: a list of timestamps to retrieve prices for, for example [1673931650, 1673931420, 1673931690]
        :type timestamps: list, int
        :param price_type: the price data to collect from the candle, must be one of the following: ["open", "high", "low", "close" ], defaults to "open"
        :type price_type: str, optional
        :raises Exception: an exception will be raised if the price type is not valid
        :raises Exception: an exception will be raised if the lists of pairs, granularities, and timestamps are not the same length
        :raises Exception: a generic exception will be raised if there is an error retrieving the prices
        :return: a list of prices for each pair for the specified timestamp
        :rtype: list, float
        """

        # ensure that the price type is valid
        # TODO: add in additional pricing strategies based upon the different pricing algorithms
        if price_type not in ['open', 'high', 'low', 'close']:
            raise Exception("The price type must be either 'open', 'high', 'low', or 'close'")
        
        # check that the lists are the same length, if not, raise an error
        if len(pairs) != len(granularities) or len(pairs) != len(timestamps):
            raise Exception("The lists of pairs, granularities, starts, and ends must be the same length")

        starts = [] 
        ends = []

        # based upon the granularities and timestamps, we need to determine the start and end times for each timestamp in the list
        # TODO: for today, we are going to call the api for every index of the arrays, but we will want to optimize this so that we only call the api once for each unique pair over a set granularity
        for i in range(len(timestamps)):
            period_start = (timestamps[i] // granularities[i]) * granularities[i]
            starts.append(period_start)
            ends.append(period_start)

        try: 
            try: 
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            prices = loop.run_until_complete(self.get_prices(pairs, granularities, starts, ends))
            # TODO: really not sure why we don't need to close the loop here, but we don't get errors if we don't close it, i think it is because are managing a client session, but i am not sure
            #loop.close()

            return prices
        except Exception as e:
            raise Exception(f"Failed to retrieve prices due to error: {e}")
        