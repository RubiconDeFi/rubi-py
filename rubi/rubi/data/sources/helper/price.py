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
        self.rate_limit = 1 / 3
        self.next_delay = 0

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

    async def get_prices(self, pairs, granularities, starts, ends, price_type='open'):

        async with aiohttp.ClientSession() as session:

            async def get_price(pair, granularity, start, end):

                self.next_delay += self.rate_limit
                await asyncio.sleep(self.next_delay)
                
                url = f"https://api.pro.coinbase.com/products/{pair}/candles?granularity={granularity}&start={start}&end={end}"
                try:

                    async with session.get(url) as resp: 
                        data = await resp.json()

                except aiohttp.ClientError as e:
                    raise Exception(f"Failed to retrieve data due to client error: {e}")
                except Exception as e:
                    raise Exception(f"Failed to retrieve data due to error: {e}. parameters {pair}, {granularity}, {start}, {end}")
                
                if len(data) == 0:
                    return 0

                if price_type == 'open':
                    price = data[0][3]
                elif price_type == 'high':
                    price = data[0][2]
                elif price_type == 'low':
                    price = data[0][1]
                elif price_type == 'close':
                    price = data[0][4]
                
                return price
            
            tasks = [get_price(pair, granularity, start, end) for pair, granularity, start, end in zip(pairs, granularities, starts, ends)]
            
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

            self.next_delay = 0
            prices = loop.run_until_complete(self.get_prices(pairs, granularities, starts, ends))

            return prices
        except Exception as e:
            raise Exception(f"Failed to retrieve prices due to error: {e}")

    def txn_dataframe_priced(self, txn_dataframe, timestamp_column, total_fee_usd = True, eth_price = False, l1_fee_usd = False, l2_fee_usd = False): 
        """the txn_dataframe_priced function will take in a transaction dataframe and return a dataframe with the total fee in usd, the eth price at the time of the transaction, and the l1 and l2 fees in usd

        :param txn_dataframe: a dataframe containing the transactions to price
        :type txn_dataframe: pandas.DataFrame
        :param timestamp_column: the name of the column containing the timestamp of the transaction
        :type timestamp_column: str
        :param total_fee_usd: whether or not to include the total fee in usd, defaults to True
        :type total_fee_usd: bool, optional
        :param eth_price: whether or not to include the eth price at the time of the transaction, defaults to False
        :type eth_price: bool, optional
        :param l1_fee_usd: whether or not to include the l1 fee in usd, defaults to False
        :type l1_fee_usd: bool, optional
        :param l2_fee_usd: whether or not to include the l2 fee in usd, defaults to False
        :type l2_fee_usd: bool, optional
        :return: a dataframe containing the transaction data with the total fee in usd, the eth price at the time of the transaction, and the l1 and l2 fees in usd
        :rtype: pandas.DataFrame
        """

        # get the unique timestamps from the dataframe
        timestamps = list(txn_dataframe[timestamp_column].unique())

        # create an array of "ETH-USD" strings that represent the pair, the array is the same length as the timestamps array
        pairs = ['ETH-USD'] * len(timestamps)
        granularities = [60] * len(timestamps)

        # from the timestamps and create a dictionary that maps the timestamp to the associated eth price
        eth_prices = self.retrieve_prices(pairs, granularities, timestamps)
        eth_price_data = dict(zip(timestamps, eth_prices))

        return eth_price_data