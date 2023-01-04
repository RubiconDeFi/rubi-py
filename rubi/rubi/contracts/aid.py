import os
import json 
import hexbytes
import logging as log
from eth_abi import decode
from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data

from rubi.contracts.helper import networks

class FactoryAid:
    """this class represents the MarketAidFactory.sol contract and has read functionality for the contract
    
    :param w3: Web3 instance
    :type w3: Web3
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 object, optional
    """

    def __init__(self, w3, contract=None):
        """constructor method"""

        chain = w3.eth.chain_id

        if contract:
            self.contract = contract
            self.address = self.contract.address
        else:
            # TODO: add error handling for unsupported chains
            network = networks[chain]()
            self.contract = w3.eth.contract(address=network.factory, abi=network.factory_abi)
            self.address = network.factory

        # set the class variables
        self.chain = chain
        self.w3 = w3

    ######################################################################
    # read calls
    ######################################################################

    # admin()
    def admin(self):
        """returns the admin address of the contract

        :return: the admin address
        :rtype: str
        """
            
        try: 
            admin = self.contract.functions.admin().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return admin             

    # getUserMarketAids(user (address))
    def get_user_market_aids(self, user):
        """returns the market aid addresses for a given user

        :return: an array of market aid addresses
        :rtype: list
        """

        try: 
            aids = self.contract.functions.getUserMarketAids(user).call()
        except ValueError: 
            aids = self.contract.functions.getUserMarketAids(self.w3.to_checksum_address(user)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return aids

    # rubiconMarket()
    def rubicon_market(self):
        """returns the address of the RubiconMarket contract

        :return: rubicon market address
        :rtype: str
        """

        try: 
            rubicon_market = self.contract.functions.rubiconMarket().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return rubicon_market

class FactoryAidSigner(FactoryAid):
    """this class represents the MarketAidFactory.sol contract and has read and write functionality for the contract. this class inherits from the FactoryAid class
    
    :param w3: a web3 instance
    :type w3: Web3
    :param wallet: the signers wallet address
    :type wallet: str
    :param key: the signers private key
    :type key: str
    :param contract: an optional parameter that allows you to pass in a contract instance, if none the contract will be instantiated from the rolodex.py file
    :type contract_address: str, optional  
    """

    def __init__(self, w3, wallet, key, contract=None):
        super().__init__(w3, contract)
        self.wallet = wallet
        self.key = key

    ######################################################################
    # write calls
    ######################################################################

    # createMarketAidInstance()
    def create_market_aid_instance(self, nonce=None, gas=3000000, gas_price=None):
        """this function creates a new market aid instance

        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the create market aid instance transaction, None if there is an error
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            create = self.contract.functions.createMarketAidInstance().build_transaction(txn)
            create = self.w3.eth.account.sign_transaction(create, self.key)
            self.w3.eth.send_raw_transaction(create.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(create.hash)['status'] == 0:
                    log.error(f"create_market_aid_instance transaction failed: {create.hash.hex()}")
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return create

class MarketAid: 

    # init function
    # TODO: possibly allow a chain variable to be passed in
    def __init__(self, w3, address, contract=None):

        # load in the aid abi 
        path = f"{os.path.dirname(os.path.realpath(__file__))}/helper/abis/MarketAid.json"
        with open(path) as f:
            aid_abi = json.load(f)
        f.close()
    
        # create contract instance or set based upon initiliazation
        if contract:
            self.contract = contract
            self.address = self.contract.address
            chain = w3.eth.chain_id
        else:
            chain = w3.eth.chain_id
            #network = networks[chain]()
            self.contract = w3.eth.contract(address=address, abi=aid_abi)
            self.address = address

        # set the class variables
        self.chain = chain
        self.w3 = w3
        self.log_strategist_trade_abi = self.contract.events.LogStrategistTrade()._get_event_abi()
        self.log_scrubbed_strat_trade_abi = self.contract.events.LogScrubbedStratTrade()._get_event_abi()
        self.log_batch_market_making_trades_abi = self.contract.events.LogBatchMarketMakingTrades()._get_event_abi()
        self.log_requote_abi = self.contract.events.LogRequote()._get_event_abi()
        self.log_batch_requote_offers_abi = self.contract.events.LogBatchRequoteOffers()._get_event_abi()
        self.codec: ABICodec = w3.codec

    ######################################################################
    # read calls
    ######################################################################

    # RubiconMarketAddress()
    def rubicon_market_address(self):
        """this function returns the address of the RubiconMarket contract

        :return: the address of the RubiconMarket contract
        :rtype: str
        """

        try: 
            rubicon_market_address = self.contract.functions.RubiconMarketAddress().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return rubicon_market_address

    # admin()
    def admin(self):
        """this function returns the address of the admin

        :return: the address of the admin
        :rtype: str
        """

        try: 
            admin = self.contract.functions.admin().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return admin

    # approvedStrategists()
    def approved_strategists(self, address):
        """this function returns the list of approved strategists

        :return: the list of approved strategists
        :rtype: list
        """

        try: 
            approved_strategists = self.contract.functions.approvedStrategists(address).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return approved_strategists
    
    # getOutstandingStrategistTrades(asset (address), quote (address), strategist (address))
    def get_outstanding_strategist_trades(self, asset, quote, strategist):
        """this function returns the list of outstanding trades for a strategist

        :param asset: the address of the asset
        :type asset: str
        :param quote: the address of the quote
        :type quote: str
        :param strategist: the address of the strategist
        :type strategist: str
        :return: the list of outstanding trades for a strategist
        :rtype: list
        """

        try: 
            outstanding_strategist_trades = self.contract.functions.getOutstandingStrategistTrades(asset, quote, strategist).call()
        except ValueError: 
            outstanding_strategist_trades = self.contract.functions.getOutstandingStrategistTrades(self.w3.to_checksum_address(asset), self.w3.to_checksum_address(quote), self.w3.to_checksum_address(strategist)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return outstanding_strategist_trades

    # getStrategistTotalLiquidity(asset (address), quote (address), strategist (address))
    def get_strategist_total_liquidity(self, asset, quote, strategist):
        """this function returns the total liquidity for a strategist 

        :param asset: the address of the asset
        :type asset: str
        :param quote: the address of the quote
        :type quote: str
        :param strategist: the address of the strategist
        :type strategist: str
        :return: the total liquidity for a strategist
        :rtype: int
        """

        try: 
            strategist_total_liquidity = self.contract.functions.getStrategistTotalLiquidity(asset, quote, strategist).call()
        except ValueError: 
            strategist_total_liquidity = self.contract.functions.getStrategistTotalLiquidity(self.w3.to_checksum_address(asset), self.w3.to_checksum_address(quote), self.w3.to_checksum_address(strategist)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return strategist_total_liquidity

    # isApprovedStrategist(strategist (address))
    def is_approved_strategist(self, strategist):
        """this function returns whether or not a strategist is approved

        :param strategist: the address of the strategist
        :type strategist: str
        :return: whether or not a strategist is approved
        :rtype: bool
        """

        try: 
            is_approved_strategist = self.contract.functions.isApprovedStrategist(strategist).call()
        except ValueError: 
            is_approved_strategist = self.contract.functions.isApprovedStrategist(self.w3.to_checksum_address(strategist)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return is_approved_strategist

    def get_strategist_trade(self, trade_id):
        """this function returns a strategist trade

        :param trade_id: the id of the trade
        :type trade_id: int
        :return: a an array containing the relevant information for a pair of offers: [ask_id, ask_pay_amt, ask_asset, bid_id, bid_pay_amt, bid_asset, strategist, timestamp]
        :rtype: dict
        """

        # check that the trade id is an integer
        if not isinstance(trade_id, int):
            log.error("trade id is not an integer")
            return None

        try: 
            strategist_trade = self.contract.functions.strategistTrades(trade_id).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return strategist_trade

    ######################################################################
    # events & helpers
    ######################################################################

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_strategist_trade_hash(self):
        return self.w3.keccak(text="LogStrategistTrade(uint256,bytes32,bytes32,address,address,uint256,address)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_strategist_trade(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_strategist_trade_abi, data['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            trade_id = decode(['uint256'], event['args']['strategistTradeID'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'ask_id': event['args']['askId'],  
                    'bid_id': event['args']['bidId'],
                    'ask_asset': event['args']['askAsset'],
                    'bid_asset': event['args']['bidAsset'],
                    'timestamp': event['args']['timestamp'],
                    'owner': event['args']['strategist']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    def parse_log_strategist_trade(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_strategist_trade_abi, log['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            trade_id = decode(['uint256'], event['args']['strategistTradeID'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'ask_id': event['args']['askId'],  
                    'bid_id': event['args']['bidId'],
                    'ask_asset': event['args']['askAsset'],
                    'bid_asset': event['args']['bidAsset'],
                    'timestamp': event['args']['timestamp'],
                    'owner': event['args']['strategist']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    '''
    event LogScrubbedStratTrade(
        uint256 strategistIDScrubbed,
        uint256 assetFill,
        address bathAssetAddress,
        uint256 quoteFill,
        address quoteAddress
    );
    '''

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_scrubbed_strat_trade_hash(self):
        return self.w3.keccak(text="LogStrategistTrade(uint256,uint256,address,uint256,address)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_scrubbed_strat_trade(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_scrubbed_strat_trade_abi, data['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            trade_id = decode(['uint256'], event['args']['strategistIDScrubbed'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'asset_fill': event['args']['assetFill'],  
                    'bath_asset_address': event['args']['bathAssetAddress'],
                    'quote_fill': event['args']['quoteFill'],
                    'quote_address': event['args']['quoteAddress']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 
        
    def parse_log_scrubbed_strat_trade(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_scrubbed_strat_trade_abi, log['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            trade_id = decode(['uint256'], event['args']['strategistIDScrubbed'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'asset_fill': event['args']['assetFill'],  
                    'bath_asset_address': event['args']['bathAssetAddress'],
                    'quote_fill': event['args']['quoteFill'],
                    'quote_address': event['args']['quoteAddress']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    '''
    event LogStrategistRewardClaim(
        address strategist,
        address asset,
        uint256 amountOfReward,
        uint256 timestamp
    );
    '''

    '''
    event LogBatchMarketMakingTrades(
        address strategist, 
        uint256[] trades
    );
    '''
    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_batch_market_making_trades_hash(self):
        return self.w3.keccak(text="LogBatchMarketMakingTrades(address,uint256[])").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_batch_market_making_trades(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_batch_market_making_trades_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'trades': event['args']['trades']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 
        
    def parse_log_batch_market_making_trades(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_batch_market_making_trades_abi, log['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'trades': event['args']['trades']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    '''
        event LogRequote(
        address strategist,
        uint256 scrubbedOfferID,
        uint256 newOfferID
    );
    '''
    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_requote_hash(self):
        return self.w3.keccak(text="LogRequote(address,uint256,uint256)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_requote(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_requote_abi, data['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            scrub_trade_id = decode(['uint256'], event['args']['scrubbedOfferID'])[0]
            trade_id = decode(['uint256'], event['args']['newOfferID'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'scrub_trade_id': scrub_trade_id,
                    'trade_id': trade_id
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 
    
    def parse_log_requote(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_requote_abi, log['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            scrub_trade_id = decode(['uint256'], event['args']['scrubbedOfferID'])[0]
            trade_id = decode(['uint256'], event['args']['newOfferID'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': trade_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'scrub_trade_id': scrub_trade_id,
                    'trade_id': trade_id
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    '''
    event LogBatchRequoteOffers(address strategist, uint256[] scrubbedOfferIDs);
    ''' 
    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_batch_requote_offers_hash(self):
        return self.w3.keccak(text="LogBatchRequoteOffers(address,uint256[])").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_batch_requote_offers(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_batch_requote_offers_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'scrub_trade_id': event['args']['scrubbedOfferIDs']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 
    
    def parse_log_batch_requote_offers(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_batch_requote_offers_abi, log['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'strategist': event['args']['strategist'],  
                    'scrub_trade_id': event['args']['scrubbedOfferIDs']
            }
            return trade

        except Exception as e:
            log.error(e, exc_info=True)
            return None 
     

class MarketAidSigner(MarketAid):
    """this class represents a MarketAid.sol contract with read and write functionality. it inherits from the MarketAid class and adds the ability to sign transactions.

    :param w3: a web3 instance
    :type w3: Web3
    :param address: the address of the contract
    :type address: str
    :param wallet: the signers wallet address
    :type wallet: str
    :param key: the signers private key
    :type key: str
    :param contract: an optional parameter that allows you to pass in a contract instance, if none the contract will be instantiated from the rolodex.py file
    :type contract_address: str, optional
    """

    def __init__(self, w3, address, wallet, key, contract=None):
        super().__init__(w3, address, contract)
        self.wallet = wallet
        self.key = key

    ######################################################################
    # write calls
    ######################################################################

    # adminMaxApproveTarget(target (address), token (address))
    def admin_max_approve_target(self, target, token, nonce=None, gas=3000000, gas_price=None):
        """this function sets the max approval for a target address to spend a token on behalf of the contract
        
        :param target: the address of the target
        :type target: str
        :param token: the address of the token
        :type token: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the approval transaction, returns None if the transaction fails
        :rtype: dict
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            max_approve = self.contract.functions.adminMaxApproveTarget(target, token).build_transaction(txn)
            max_approve = self.w3.eth.account.sign_transaction(max_approve, self.key)
            self.w3.eth.send_raw_transaction(max_approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(max_approve.hash)['status'] == 0:
                    log.error(f'admin_max_approve_target transaction {max_approve.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            max_approve = self.contract.functions.adminMaxApproveTarget(self.w3.to_checksum_address(target), self.w3.to_checksum_address(token)).build_transaction(txn)
            max_approve = self.w3.eth.account.sign_transaction(max_approve, self.key)
            self.w3.eth.send_raw_transaction(max_approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(max_approve.hash)['status'] == 0:
                    log.error(f'admin_max_approve_target transaction {max_approve.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return max_approve

    # adminPullAllFunds(erc20s address[])
    def admin_pull_all_funds(self, erc20s, nonce=None, gas=3000000, gas_price=None):
        """this function pulls all funds from the contract
        
        :param erc20s: a list of erc20 addresses
        :type erc20s: list
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the pull transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price
        
        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            pull_all_funds = self.contract.functions.adminPullAllFunds(erc20s).build_transaction(txn)
            pull_all_funds = self.w3.eth.account.sign_transaction(pull_all_funds, self.key)
            self.w3.eth.send_raw_transaction(pull_all_funds.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(pull_all_funds.hash)['status'] == 0:
                    log.error(f'admin_pull_all_funds transaction {pull_all_funds.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # adminRebalanceFunds(assetToSell (address), amountToSell (uint256), assetToTarget (address))
    def admin_rebalance_funds(self, asset_to_sell, amount_to_sell, asset_to_target, nonce=None, gas=3000000, gas_price=None):
        """this function rebalances funds from one asset to another on the RubiconMarket

        :param asset_to_sell: the address of the asset to sell
        :type asset_to_sell: str
        :param amount_to_sell: the amount of the asset to sell
        :type amount_to_sell: int
        :param asset_to_target: the address of the asset to target
        :type asset_to_target: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the rebalance transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            rebalance = self.contract.functions.adminRebalanceFunds(asset_to_sell, amount_to_sell, asset_to_target).build_transaction(txn)
            rebalance = self.w3.eth.account.sign_transaction(rebalance, self.key)
            self.w3.eth.send_raw_transaction(rebalance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(rebalance.hash)['status'] == 0:
                    log.error(f'admin_rebalance_funds transaction {rebalance.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            rebalance = self.contract.functions.adminRebalanceFunds(self.w3.to_checksum_address(asset_to_sell), amount_to_sell, self.w3.to_checksum_address(asset_to_target)).build_transaction(txn)
            rebalance = self.w3.eth.account.sign_transaction(rebalance, self.key)
            self.w3.eth.send_raw_transaction(rebalance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(rebalance.hash)['status'] == 0:
                    log.error(f'admin_rebalance_funds transaction {rebalance.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return rebalance

    # approveStrategist(strategist (address))
    def approve_strategist(self, strategist, nonce=None, gas=3000000, gas_price=None):
        """this function approves a strategist to use the aid contract instance

        :param strategist: the address of the strategist to approve
        :type strategist: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the approve transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            approve = self.contract.functions.approveStrategist(strategist).build_transaction(txn)
            approve = self.w3.eth.account.sign_transaction(approve, self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(approve.hash)['status'] == 0:
                    log.error(f'approve_strategist transaction {approve.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            approve = self.contract.functions.approveStrategist(self.w3.to_checksum_address(strategist)).build_transaction(txn)
            approve = self.w3.eth.account.sign_transaction(approve, self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(approve.hash)['status'] == 0:
                    log.error(f'approve_strategist transaction {approve.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return approve

    # batchMarketMakingTrades(tokenPairs (address[2]), askNumerators (uint256[]), askDenominators (uint256[]), bidNumerators (uint256[]), bidDenominators (uint256[]))
    def batch_market_making_trades(self, token_pairs, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=3000000, gas_price=None):
        """this function executes a batch of market making trades on the RubiconMarket

        :param token_pairs: the token pairs to trade [token0, token1]
        :type token_pairs: list
        :param ask_numerators: the numerators of the ask prices
        :type ask_numerators: list
        :param ask_denominators: the denominators of the ask prices
        :type ask_denominators: list
        :param bid_numerators: the numerators of the bid prices
        :type bid_numerators: list
        :param bid_denominators: the denominators of the bid prices
        :type bid_denominators: list
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the batch market making trades transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            batch = self.contract.functions.batchMarketMakingTrades(token_pairs, ask_numerators, ask_denominators, bid_numerators, bid_denominators).build_transaction(txn)
            batch = self.w3.eth.account.sign_transaction(batch, self.key)
            self.w3.eth.send_raw_transaction(batch.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(batch.hash)['status'] == 0:
                    log.error(f'batch_market_making_trades transaction {batch.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return batch
    
    # batchRequoteAllOffers(tokenPair (address[2]), askNumerators (uint256[]), askDenominators (uint256[]), bidNumerators (uint256[]), bidDenominators (uint256[]))
    def batch_requote_all_offers(self, token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=3000000, gas_price=None):
        """this function executes a batch requote while clearing all offers the strategist has on the RubiconMarket

        :param token_pair: the token pair to trade [token0, token1]
        :type token_pair: list
        :param ask_numerators: the numerators of the ask prices
        :type ask_numerators: list
        :param ask_denominators: the denominators of the ask prices
        :type ask_denominators: list
        :param bid_numerators: the numerators of the bid prices
        :type bid_numerators: list
        :param bid_denominators: the denominators of the bid prices
        :type bid_denominators: list
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the batch requote all offers transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            batch = self.contract.functions.batchRequoteAllOffers(token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators).build_transaction(txn)
            batch = self.w3.eth.account.sign_transaction(batch, self.key)
            self.w3.eth.send_raw_transaction(batch.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(batch.hash)['status'] == 0:
                    log.error(f'batch_requote_all_offers transaction {batch.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return batch

    # batchRequoteOffers(ids (uint256[]), tokenPair (address[2]), askNumerators (uint256[]), askDenominators (uint256[]), bidNumerators (uint256[]), bidDenominators (uint256[]))
    def batch_requote_offers(self, ids, token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators, nonce=None, gas=3000000, gas_price=None):
        """this function executes a batch requote of all offers that are provided in the ids array
        
        :param ids: the ids of the offers to requote
        :type ids: list
        :param token_pair: the token pair to trade [token0, token1]
        :type token_pair: list
        :param ask_numerators: the numerators of the ask prices
        :type ask_numerators: list
        :param ask_denominators: the denominators of the ask prices
        :type ask_denominators: list
        :param bid_numerators: the numerators of the bid prices
        :type bid_numerators: list
        :param bid_denominators: the denominators of the bid prices
        :type bid_denominators: list
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the batch requote offers transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            batch = self.contract.functions.batchRequoteOffers(ids, token_pair, ask_numerators, ask_denominators, bid_numerators, bid_denominators).build_transaction(txn)
            batch = self.w3.eth.account.sign_transaction(batch, self.key)
            self.w3.eth.send_raw_transaction(batch.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(batch.hash)['status'] == 0:
                    log.error(f'batch_requote_offers transaction {batch.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return batch

    # placeMarketMakingTrades(tokenPair (address[2]), askNumerator (uint256), askDenominator (uint256), bidNumerator (uint256), bidDenominator (uint256))
    # aid.batch_market_making_trades([weth.address, usdc.address], [the amount of the asset you will sell], [the amount of the quote you will receive], [the amount of quote you will pay], [the amount of asset you would receive])
    def place_market_making_trades(self, token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator, nonce=None, gas=3000000, gas_price=None):
        """this function executes a market making trade on the RubiconMarket
        
        :param token_pair: the token pair to trade [token0, token1]
        :type token_pair: list
        :param ask_numerator: the numerator of the ask price. this is the amount of the asset you will sell
        :type ask_numerator: int
        :param ask_denominator: the denominator of the ask price. this is the amount of the quote you will receive
        :type ask_denominator: int
        :param bid_numerator: the numerator of the bid price. this is the amount of quote you will pay
        :type bid_numerator: int
        :param bid_denominator: the denominator of the bid price. this is the amount of asset you would receive
        :type bid_denominator: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the place market making trades transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try: 
            trade = self.contract.functions.placeMarketMakingTrades(token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator).build_transaction(txn)
            trade = self.w3.eth.account.sign_transaction(trade, self.key)
            self.w3.eth.send_raw_transaction(trade.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(trade.hash)['status'] == 0:
                    log.error(f'place_market_making_trades transaction {trade.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return trade

    # removeStrategist(strategist (address))
    def remove_strategist(self, strategist, nonce=None, gas=3000000, gas_price=None):
        """this function removes a strategist from the approved strategist list on the market aid contract
        
        :param strategist: the address of the strategist to remove
        :type strategist: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the remove strategist transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            remove = self.contract.functions.removeStrategist(strategist).build_transaction(txn)
            remove = self.w3.eth.account.sign_transaction(remove, self.key)
            self.w3.eth.send_raw_transaction(remove.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(remove.hash)['status'] == 0:
                    log.error(f'remove_strategist transaction {remove.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            remove = self.contract.functions.removeStrategist(self.w3.to_checksum_address(strategist)).build_transaction(txn)
            remove = self.w3.eth.account.sign_transaction(remove, self.key)
            self.w3.eth.send_raw_transaction(remove.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(remove.hash)['status'] == 0:
                    log.error(f'remove_strategist transaction {remove.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return remove

    # requote(id (uint256), tokenPair (address[2]), askNumerator (uint256), askDenominator (uint256), bidNumerator (uint256), bidDenominator (uint256))
    def requote(self, id, token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator, nonce=None, gas=3000000, gas_price=None):
        """this function requotes an offer on the RubiconMarket
        
        :param id: the id of the offer to requote
        :type id: int
        :param token_pair: the token pair to trade [token0, token1]
        :type token_pair: list
        :param ask_numerator: the numerator of the ask price
        :type ask_numerator: int
        :param ask_denominator: the denominator of the ask price
        :type ask_denominator: int
        :param bid_numerator: the numerator of the bid price
        :type bid_numerator: int
        :param bid_denominator: the denominator of the bid price
        :type bid_denominator: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the requote transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce

        if gas_price is None:
            gas_price = self.w3.eth.gas_price
        
        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            requote = self.contract.functions.requote(id, token_pair, ask_numerator, ask_denominator, bid_numerator, bid_denominator).build_transaction(txn)
            requote = self.w3.eth.account.sign_transaction(requote, self.key)
            self.w3.eth.send_raw_transaction(requote.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(requote.hash)['status'] == 0:
                    log.error(f'requote transaction {requote.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return requote

    # scrubStrategistTrade(id (uint256))
    def scrub_strategist_trade(self, id, nonce=None, gas=3000000, gas_price=None):
        """this function scrubs a strategist trade from the RubiconMarket contract

        :param id: the id of the trade to scrub
        :type id: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            scrub = self.contract.functions.scrubStrategistTrade(id).build_transaction(txn)
            scrub = self.w3.eth.account.sign_transaction(scrub, self.key)
            self.w3.eth.send_raw_transaction(scrub.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(scrub.hash)['status'] == 0:
                    log.error(f'scrub_strategist_trade transaction {scrub.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return scrub

    # scrubStrategistTrades(ids (uint256[]))
    def scrub_strategist_trades(self, ids, nonce=None, gas=3000000, gas_price=None):
        """this function scrubs a list of strategist trades from the RubiconMarket contract

        :param ids: the ids of the trades to scrub
        :type ids: list
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the scrub transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            txn_nonce = self.w3.eth.get_transaction_count(self.wallet)
        else:
            txn_nonce = nonce
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': txn_nonce}

        try:
            scrub = self.contract.functions.scrubStrategistTrades(ids).build_transaction(txn)
            scrub = self.w3.eth.account.sign_transaction(scrub, self.key)
            self.w3.eth.send_raw_transaction(scrub.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(scrub.hash)['status'] == 0:
                    log.error(f'scrub_strategist_trades transaction {scrub.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return scrub