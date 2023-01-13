import requests 
from .price import Price

class Gas:
    """Gas helper class"""

    def __init__(self, w3):
        """constructor for the gas helper class
        
        :param w3: a web3 instance
        :type w3: Web3 object
        """
        self.w3 = w3
        self.price = Price()

    def get_optimism_txn_gas_data(self, txn, priced=True): 
        """this function takes a transaction hash and returns a dictionary of gas data for the transaction
        
        :param txn: the transaction hash
        :type txn: str
        :return: a dictionary of gas data for the transaction
        :rtype: dict
        """

        # TODO: Issue #18: multicall -> also there is better logic we can use to pull the eth_price data for a single timestamp to avoid repeat calls
        txn_object = self.w3.eth.get_transaction(txn)
        txn_receipt = self.w3.eth.get_transaction_receipt(txn)

        txn_data = {}
        txn_data['l2_gas_price'] = txn_object['gasPrice']
        txn_data['l2_gas_used'] = txn_receipt['gasUsed']
        txn_data['l1_gas_used'] = int(txn_receipt['l1GasUsed'], 0)
        txn_data['l1_gas_price'] = int(txn_receipt['l1GasPrice'], 0)
        txn_data['l1_fee_scalar'] = float(txn_receipt['l1FeeScalar'])
        txn_data['timestamp'] = int(txn_object['l1Timestamp'], 0)
        txn_data['l1_fee'] = int(txn_data['l1_gas_used'] * txn_data['l1_gas_price'] * txn_data['l1_fee_scalar'])
        txn_data['l2_fee'] = txn_data['l2_gas_used'] * txn_data['l2_gas_price']
        txn_data['total_fee'] = txn_data['l1_fee'] + txn_data['l2_fee']
        txn_data['l1_fee_eth'] = txn_data['l1_fee'] / 10**18
        txn_data['l2_fee_eth'] = txn_data['l2_fee'] / 10**18
        txn_data['total_fee_eth'] = txn_data['total_fee'] / 10**18

        # if priced, get the price of eth at the time of the transaction
        if priced: 
            eth_price = self.price.get_defi_llama_price(timestamp=txn_data['timestamp'])

            # check that a valid price was returned
            if not eth_price:     
                eth_price = self.price.get_coinbase_price(date=txn_data['timestamp'])

            # check that a valid price was returned
            if not eth_price: 
                return None
            
            # calculate the usd value of the fees
            txn_data['eth_price'] = eth_price['amount']
            txn_data['l1_fee_usd'] = txn_data['l1_fee_eth'] * txn_data['eth_price']
            txn_data['l2_fee_usd'] = txn_data['l2_fee_eth'] * txn_data['eth_price']
            txn_data['total_fee_usd'] = txn_data['total_fee_eth'] * txn_data['eth_price']

        return txn_data

    def txn_dataframe_update(self, txn_dataframe, txn_column, total_fee_eth = True, total_fee_usd = True, l2_gas_price = False, l2_gas_used = False, l1_gas_used = False, l1_gas_price = False, l1_fee_scalar = False, l1_fee = False, l2_fee = False, total_fee = False, l1_fee_eth = False, l2_fee_eth = False, eth_price = False, l1_fee_usd = False, l2_fee_usd = False): 
        """this function takes a dataframe of transactions and adds gas data to it. by default, it only adds the total gas fee in eth and usd to the dataframe. if any of the other parameters are set to true, it will add those values to the dataframe as well
        
        :param txn_dataframe: a dataframe of transactions
        :type txn_dataframe: pandas dataframe
        :param txn_column: the name of the column that contains the transaction hashes
        :type txn_column: str
        :param total_fee_eth: whether or not to add the total fee in eth to the dataframe
        :type total_fee_eth: bool
        :param total_fee_usd: whether or not to add the total fee in usd to the dataframe
        :type total_fee_usd: bool
        :param l2_gas_price: whether or not to add the l2 gas price to the dataframe
        :type l2_gas_price: bool
        :param l2_gas_used: whether or not to add the l2 gas used to the dataframe
        :type l2_gas_used: bool
        :param l1_gas_used: whether or not to add the l1 gas used to the dataframe
        :type l1_gas_used: bool
        :param l1_gas_price: whether or not to add the l1 gas price to the dataframe
        :type l1_gas_price: bool
        :param l1_fee_scalar: whether or not to add the l1 fee scalar to the dataframe
        :type l1_fee_scalar: bool
        :param l1_fee: whether or not to add the l1 fee to the dataframe
        :type l1_fee: bool
        :param l2_fee: whether or not to add the l2 fee to the dataframe
        :type l2_fee: bool
        :param total_fee: whether or not to add the total fee to the dataframe
        :type total_fee: bool
        :param l1_fee_eth: whether or not to add the l1 fee in eth to the dataframe
        :type l1_fee_eth: bool
        :param l2_fee_eth: whether or not to add the l2 fee in eth to the dataframe
        :type l2_fee_eth: bool
        :param eth_price: whether or not to add the eth price to the dataframe
        :type eth_price: bool
        :param l1_fee_usd: whether or not to add the l1 fee in usd to the dataframe
        :type l1_fee_usd: bool
        :param l2_fee_usd: whether or not to add the l2 fee in usd to the dataframe
        :type l2_fee_usd: bool
        :return: a dataframe of transactions with gas data added
        :rtype: pandas dataframe
        """

        # get the unique transaction hashes from the dataframe
        txn_hashes = list(txn_dataframe[txn_column].unique())

        # iterate through the transaction hashes and create a dictionary that maps the transaction the associated gas data
        txn_gas_data = {}
        for txn in txn_hashes:
            txn_gas_data[txn] = self.get_optimism_txn_gas_data(txn)

        # now add all columns that we are interested in to the dataframe
        if total_fee_eth:
            txn_dataframe['total_fee_eth'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['total_fee_eth'])
        if total_fee_usd: 
            txn_dataframe['total_fee_usd'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['total_fee_usd'])
        if l2_gas_price:
            txn_dataframe['l2_gas_price'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l2_gas_price'])
        if l2_gas_used:
            txn_dataframe['l2_gas_used'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l2_gas_used'])
        if l1_gas_used:
            txn_dataframe['l1_gas_used'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_gas_used'])
        if l1_gas_price:
            txn_dataframe['l1_gas_price'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_gas_price'])
        if l1_fee_scalar:
            txn_dataframe['l1_fee_scalar'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_fee_scalar'])
        if l1_fee:
            txn_dataframe['l1_fee'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_fee'])
        if l2_fee:
            txn_dataframe['l2_fee'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l2_fee'])
        if total_fee:
            txn_dataframe['total_fee'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['total_fee'])
        if l1_fee_eth:
            txn_dataframe['l1_fee_eth'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_fee_eth'])
        if l2_fee_eth:
            txn_dataframe['l2_fee_eth'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l2_fee_eth'])
        if eth_price:
            txn_dataframe['eth_price'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['eth_price'])
        if l1_fee_usd:
            txn_dataframe['l1_fee_usd'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l1_fee_usd'])
        if l2_fee_usd:
            txn_dataframe['l2_fee_usd'] = txn_dataframe[txn_column].map(lambda x: txn_gas_data[x]['l2_fee_usd'])
        
        return txn_dataframe
