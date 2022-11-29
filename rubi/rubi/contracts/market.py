import hexbytes
import logging as log
from eth_abi import decode
from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data

from rubi.contracts.helper import networks

class RubiconMarket: 
    """this class represents the RubiconMarket.sol contract and has read functionality.

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
            network = networks[chain]()
            self.contract = w3.eth.contract(address=network.market, abi=network.market_abi)
            self.address = network.market

        self.chain = chain
        self.w3 = w3
        self.log_make_abi = self.contract.events.LogMake._get_event_abi()
        self.log_take_abi = self.contract.events.LogTake._get_event_abi()
        self.log_kill_abi = self.contract.events.LogKill._get_event_abi()
        self.offer_deleted_abi = self.contract.events.OfferDeleted._get_event_abi()
        self.codec: ABICodec = w3.codec

    ######################################################################
    # read calls
    ######################################################################

    # getBestOffer(sell_gem (address), buy_gem(address))
    def get_best_offer(self, sell_gem, buy_gem):
        """returns the best offer for the given pair of tokens

        :param sell_gem: the address of the token being sold by the maker
        :type sell_gem: str
        :param buy_gem: the address of the token being bought by the maker
        :type buy_gem: str
        :return: the id of the best offer on the book, None if there is no offer on the book
        :rtype: int, None
        """

        try: 
            best_offer = self.contract.functions.getBestOffer(sell_gem, buy_gem).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            sell_gem = self.w3.to_checksum_address(sell_gem)
            buy_gem = self.w3.to_checksum_address(buy_gem)
            best_offer = self.contract.functions.getBestOffer(sell_gem, buy_gem).call()
            # TODO: add error handling, local logging, and OT tracing
            # TODO: when you pass in two zero addresses, it returns zero, is this a bug or a feature?
                   # basically if you pass in any two addresses that don't have an offer, it returns zero
                   # the question now is, do we want to return zero or do we want to return an errror
                   # and handle this when the function then views the offer
                   # prolly the latter...
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return best_offer

    # getBetterOffer(id (uint256))
    def get_better_offer(self, id):
        """returns the id of the offer that is better than the given offer

        :param id: the id of the offer
        :type id: int
        :return: the id of the offer that is better than the given offer, none if there is no better offer
        :rtype: int, None
        """
            
        try: 
            better_offer = self.contract.functions.getBetterOffer(id).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return better_offer

    # getWorseOffer(id (uint256))
    def get_worse_offer(self, id):
        """returns the id of the offer that is worse than the given offer

        :param id: the id of the offer
        :type id: int
        :return: the id of the offer that is worse than the given offer, none if there is no worse offer
        :rtype: int, None
        """

        try: 
            worse_offer = self.contract.functions.getWorseOffer(id).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return worse_offer

    # getBuyAmount(buy_gem (address), pay_gem (address), pay_amt (uint256))
    def get_buy_amount(self, buy_gem, pay_gem, pay_amt):
        """returns the amount of buy_gem that can be bought with pay_amt of pay_gem

        :param buy_gem: the address of the token being bought
        :type buy_gem: str
        :param pay_gem: the address of the token being paid
        :type pay_gem: str
        :param pay_amt: the amount of pay_gem being paid, in the integer representation of the token amount
        :type pay_amt: int
        :return: the amount of buy_gem that can be bought with pay_amt of pay_gem, in the integer representation of the buy_gem amount
        :rtype: int
        """

        try: 
            buy_amount = self.contract.functions.getBuyAmount(buy_gem, pay_gem, pay_amt).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            pay_gem = self.w3.to_checksum_address(pay_gem)
            buy_gem = self.w3.to_checksum_address(buy_gem)
            buy_amount = self.contract.functions.getBuyAmount(buy_gem, pay_gem, pay_amt).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return buy_amount

    # getFeeBPS()
    def get_fee_bps(self):
        """returns the fee in basis points
        
        :return: the fee in basis points
        :rtype: int
        """

        try: 
            fee_bps = self.contract.functions.getFeeBPS().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return fee_bps

    # getOffer(id (uint256))
    # returns: [pay_amt (uint256), pay_gem (address), buy_amt (uint256), buy_gem (address)] - pay gem is what the offerer is selling, buy gem is what the offerer is buying
    def get_offer(self, id):
        """returns the offer with the given id in the form of a list - [pay_amt, pay_gem, buy_amt, buy_gem]

        :param id: the id of the offer
        :type id: int
        :return: the offer with the given id
        :rtype: array
        """

        try: 
            offer = self.contract.functions.getOffer(id).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return offer

    # getOfferCount(sell_gem (address), buy_gem (address))
    def get_offer_count(self, sell_gem, buy_gem):
        """returns the number of offers on the book for the given pair of tokens

        :param sell_gem: the address of the token being sold by the maker
        :type sell_gem: str
        :param buy_gem: the address of the token being bought by the maker
        :type buy_gem: str
        :return: the number of offers on the book for the given pair of tokens, None if there are no offers on the book for the given pair of tokens
        :rtype: int, None 
        """

        try: 
            offer_count = self.contract.functions.getOfferCount(sell_gem, buy_gem).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            sell_gem = self.w3.to_checksum_address(sell_gem)
            buy_gem = self.w3.to_checksum_address(buy_gem)
            offer_count = self.contract.functions.getOfferCount(sell_gem, buy_gem).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return offer_count

    # getOwner(id (uint256))
    def get_owner(self, id):
        """returns the address of the owner of the offer with the given id

        :param id: the id of the offer
        :type id: int
        :return: the address of the owner of the offer with the given id
        :rtype: str
        """

        try: 
            owner = self.contract.functions.getOwner(id).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return owner

    # getPayAmount(pay_gem (address), buy_gem (address), buy_amt (uint256))
    def get_pay_amount(self, pay_gem, buy_gem, buy_amt):
        """returns the amount of pay_gem that can be paid to buy buy_amt of buy_gem
        
        :param pay_gem: the address of the token being paid
        :type pay_gem: str
        :param buy_gem: the address of the token being bought
        :type buy_gem: str
        :param buy_amt: the amount of buy_gem being bought, in the integer representation of the token amount, returns None if the offer could not be filled
        :type buy_amt: int, None
        """

        try: 
            pay_amount = self.contract.functions.getPayAmount(pay_gem, buy_gem, buy_amt).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            pay_gem = self.w3.to_checksum_address(pay_gem)
            buy_gem = self.w3.to_checksum_address(buy_gem)
            pay_amount = self.contract.functions.getPayAmount(pay_gem, buy_gem, buy_amt).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return pay_amount

    # matchingEnabled()
    def matching_enabled(self):
        """returns whether or not matching is enabled, True if matching is enabled, False if matching is disabled

        :return: whether or not matching is enabled
        :rtype: bool
        """

        try: 
            matching_enabled = self.contract.functions.matchingEnabled().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return matching_enabled

    ######################################################################
    # events & helpers
    ######################################################################

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_make_hash(self):
        return self.w3.keccak(text="LogMake(bytes32,bytes32,address,address,address,uint128,uint128,uint64)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # i feel like this could be done much faster... 
    def stream_log_make(self, data): 

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_make_abi, data['params']['result'])

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            offer = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],  
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['pay_amt'],
                    'buy_amt': event['args']['buy_amt'],
                    'timestamp': event['args']['timestamp'],
                    'owner': event['args']['maker']
            }
            return offer

        except Exception as e:
            log.error(e, exc_info=True)
            return None 

    def parse_log_make(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_make_abi, log)

            # decode the offer id
            # TODO: there is probably a way to do this that does not hardcode the type of the id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            offer = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],  
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['pay_amt'],
                    'buy_amt': event['args']['buy_amt'],
                    'timestamp': event['args']['timestamp'],
                    'owner': event['args']['maker']
            }
            return offer
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None 


    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_take_hash(self):
        return self.w3.keccak(text="LogTake(bytes32,bytes32,address,address,address,address,uint128,uint128,uint64)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_take(self, data):

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_take_abi, data['params']['result'])

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['take_amt'],
                    'buy_amt': event['args']['give_amt'],
                    'timestamp': event['args']['timestamp'],
                    'maker': event['args']['maker'],
                    'taker': event['args']['taker']
            }
            return trade
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
    def parse_log_take(self, log):

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_take_abi, log)

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            trade = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['take_amt'],
                    'buy_amt': event['args']['give_amt'],
                    'timestamp': event['args']['timestamp'],
                    'maker': event['args']['maker'],
                    'taker': event['args']['taker']
            }
            return trade
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_kill_hash(self): 
        return self.w3.keccak(text="LogKill(bytes32,bytes32,address,address,address,uint128,uint128,uint64)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_kill(self, data): 

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:  
            event = get_event_data(self.codec, self.log_kill_abi, data['params']['result'])

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the killed trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            kill = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['pay_amt'],
                    'buy_amt': event['args']['buy_amt'],
                    'timestamp': event['args']['timestamp'],
                    'maker': event['args']['maker']
            }
            return kill
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None
    
    def parse_log_kill(self, log):

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_kill_abi, log)

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the killed trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            kill = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'pay_gem': event['args']['pay_gem'],
                    'buy_gem': event['args']['buy_gem'],
                    'pay_amt': event['args']['pay_amt'],
                    'buy_amt': event['args']['buy_amt'],
                    'timestamp': event['args']['timestamp'],
                    'maker': event['args']['maker']
            }
            return kill
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_offer_deleted_hash(self): 
        return self.w3.keccak(text="OfferDeleted(bytes32)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_offer_deleted(self, data): 

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:  
            event = get_event_data(self.codec, self.offer_deleted_abi, data['params']['result'])

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the deleted trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            deleted = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event']
            }
            return deleted
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None
    
    def parse_offer_deleted(self, log):

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.offer_deleted_abi, log)

            # decode the offer id
            offer_id = decode(['uint256'], event['args']['id'])[0]

            # now pass the killed trade back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            deleted = {
                    'id': offer_id,
                    'txn': event['transactionHash'].hex(),
                    'event': event['event']
            }
            return deleted
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None

class RubiconMarketSigner(RubiconMarket): 
    """this class represents the RubiconMarket.sol contract and is a super class of the RubiconMarket class. this class has read functionality and inherents the read functionality of the RubiconMarket class. 

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

    # buy(id (uint256), amount (uint256))
    # the user must put in the amount of pay_gem that they want and will be charged the amount of buy_gem that the offer is asking for
    def buy(self, id, amount, nonce=None, gas=3000000, gas_price=None):
        """buy the amount of pay_gem from the offer with the id, in exchange for the amount of buy_gem at the price of the offer

        :param id: id of the offer
        :type id: int
        :param amount: amount of pay_gem to buy, in the integer representation of the token
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the buy transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}
        
        try:
            buy = self.contract.functions.buy(id, amount).build_transaction(txn)
            buy = self.w3.eth.account.sign_transaction(buy, self.key)
            self.w3.eth.send_raw_transaction(buy.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return buy  

    # buyAllAmount(buy_gem (address), buy_amt (uint256), pay_gem (address), max_fill_amount (uint256))
        # TODO: add clear explanation for function names and parameters
        # buy_gem is the token you want to buy
        # buy_amt is the amount of the token you want to buy
        # pay_gem is the token you want to pay with
        # max_fill is the maximum amount of the token you want to pay with
    def buy_all_amount(self, buy_gem, buy_amt, pay_gem, max_fill_amount, nonce=None, gas=3000000, gas_price=None):
        """buy the buy_amt of the buy_gem token in exchange for the pay_gem token only if it does not exceed the max_fill_amount of the pay_gem token
        
        :param buy_gem: address of the token you want to buy
        :type buy_gem: str
        :param buy_amt: amount of the token you want to buy, in the integer representation of the token
        :type buy_amt: int
        :param pay_gem: address of the token you want to pay with
        :type pay_gem: str
        :param max_fill_amount: maximum amount of the pay_gem token you want to pay with, in the integer representation of the token
        :type max_fill_amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the buyAllAmount transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try: 
            buy_all_amount = self.contract.functions.buyAllAmount(buy_gem, buy_amt, pay_gem, max_fill_amount).build_transaction(txn)
            buy_all_amount = self.w3.eth.account.sign_transaction(buy_all_amount, self.key)
            self.w3.eth.send_raw_transaction(buy_all_amount.rawTransaction)
        except ValueError: 
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            buy_all_amount = self.contract.functions.buyAllAmount(self.w3.to_checksum_address(buy_gem), buy_amt, self.w3.to_checksum_address(pay_gem), max_fill_amount).build_transaction(txn)
            buy_all_amount = self.w3.eth.account.sign_transaction(buy_all_amount, self.key)
            self.w3.eth.send_raw_transaction(buy_all_amount.rawTransaction)
        except Exception as e: 
            log.error(e, exc_info=True)
            return None
        
        return buy_all_amount

    # cancel(id (uint256))
    def cancel(self, id, nonce=None, gas=3000000, gas_price=None):
        """cancel the offer with the id, user can only cancel offers they have created

        :param id: id of the offer
        :type id: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the cancel transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            cancel = self.contract.functions.cancel(id).build_transaction(txn)
            cancel = self.w3.eth.account.sign_transaction(cancel, self.key)
            self.w3.eth.send_raw_transaction(cancel.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return cancel

    # offer(pay_amt (uint256), pay_gem (address), buy_amt (uint256), buy_gem (address))
    def offer(self, pay_amt, pay_gem, buy_amt, buy_gem, pos=0, nonce=None, gas=3000000, gas_price=None):
        """create an offer to buy the buy_amt of the buy_gem token in exchange for the pay_amt of the pay_gem token

        :param pay_amt: amount of the pay_gem token you want to pay with, in the integer representation of the token
        :type pay_amt: int
        :param pay_gem: address of the token you want to pay with
        :type pay_gem: str
        :param buy_amt: amount of the buy_gem token you want to buy, in the integer representation of the token
        :type buy_amt: int
        :param buy_gem: address of the token you want to buy
        :type buy_gem: str
        :param pos: position of the offer in the linked list, default to 0 unless the maker knows the position they want to insert the offer at
        :type pos: int, optional
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the offer transaction, returns None if the transaction fails
        :rtype: dict, None    
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            offer = self.contract.functions.offer(pay_amt, pay_gem, buy_amt, buy_gem, pos).build_transaction(txn)
            offer = self.w3.eth.account.sign_transaction(offer, self.key)
            self.w3.eth.send_raw_transaction(offer.rawTransaction)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            offer = self.contract.functions.offer(pay_amt, self.w3.to_checksum_address(pay_gem), buy_amt, self.w3.to_checksum_address(buy_gem), pos).build_transaction(txn)
            offer = self.w3.eth.account.sign_transaction(offer, self.key)
            self.w3.eth.send_raw_transaction(offer.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return offer

    # sellAllAmount(pay_gem (address), pay_amt (uint256), buy_gem (address), min_fill_amount (uint256))
    def sell_all_amount(self, pay_gem, pay_amt, buy_gem, min_fill_amount, nonce=None, gas=3000000, gas_price=None):
        """sell the pay_amt of the pay_gem token in exchange for buy_gem, on the condition that you receive at least the min_fill_amount of the buy_gem token

        :param pay_gem: address of the token you want to pay with
        :type pay_gem: str
        :param pay_amt: amount of the pay_gem token you want to pay with, in the integer representation of the token
        :type pay_amt: int
        :param buy_gem: address of the token you want to buy
        :type buy_gem: str
        :param min_fill_amount: minimum amount of the buy_gem token you want to receive, in the integer representation of the token
        :type min_fill_amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the sellAllAmount transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            sell_all_amount = self.contract.functions.sellAllAmount(pay_gem, pay_amt, buy_gem, min_fill_amount).build_transaction(txn)
            sell_all_amount = self.w3.eth.account.sign_transaction(sell_all_amount, self.key)
            self.w3.eth.send_raw_transaction(sell_all_amount.rawTransaction)
        except ValueError:
            print('most likely a checksum error... retrying with checksummed addresses')
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            sell_all_amount = self.contract.functions.sellAllAmount(self.w3.to_checksum_address(pay_gem), pay_amt, self.w3.to_checksum_address(buy_gem), min_fill_amount).build_transaction(txn)
            sell_all_amount = self.w3.eth.account.sign_transaction(sell_all_amount, self.key)
            self.w3.eth.send_raw_transaction(sell_all_amount.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return sell_all_amount