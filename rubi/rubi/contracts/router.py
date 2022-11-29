import hexbytes
import logging as log
from web3 import Web3 
from eth_abi import decode
from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data

from rubi.contracts.helper import networks

class RubiconRouter: 
    """this class represents a RubiconRouter.sol contract with read functionality.
    
    :param w3: Web3 instance
    :type w3: Web3
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 Object, optional
    """

    # init function
    def __init__(self, w3, contract=None):

        chain = w3.eth.chain_id

        if contract:
            self.contract = contract
            self.address = self.contract.address
        else:
            network = networks[chain]()
            self.contract = w3.eth.contract(address=network.router, abi=network.router_abi)
            self.address = network.router

        # set the class variables
        self.w3 = w3
        self.log_swap_abi = self.contract.events.LogSwap._get_event_abi()
        self.codec: ABICodec = w3.codec

    ######################################################################
    # read calls
    ######################################################################  
    
    # checkClaimAllUserBonusTokens(user (address), targetBathTokens (address[]), token (address))
    def check_claim_all_user_bonus_tokens(self, user, targetBathTokens, token):
        """check the claim the user has to bonus tokens 

        :param user: the user address of interest
        :type user: str
        :param targetBathTokens: the bath tokens of interest, this is an array of addresses
        :type targetBathTokens: list
        :param token: the bonus token of interest
        :type token: str
        :return: the amount of bonus tokens the user has available to claim
        :rtype: int
        """

        try: 
            claimable = self.contract.functions.checkClaimAllUserBonusTokens(user, targetBathTokens, token).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return claimable

    # getBestOffer(asset (address), quote(address))
    def get_best_offer(self, asset, quote):
        """get the best offer for a given asset and quote pair
        
        :param asset: the asset address of interest
        :type asset: str
        :param quote: the quote address of interest
        :type quote: str
        :return: the best offer id for the given asset and quote pair
        :rtype: int
        """

        try: 
            best_offer = self.contract.functions.getBestOfferAndInfo(asset, quote).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            asset = self.w3.to_checksum_address(asset)
            quote = self.w3.to_checksum_address(quote)
            best_offer = self.contract.functions.getBestOfferAndInfo(asset, quote).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return best_offer

    # getBookFromPair(asset (address), quote(address), topNOrders (uint256))
    def get_book_from_pair(self, asset, quote, topNOrders):
        """get the book for a given asset and quote pair, to the depth of topNOrders
        
        :param asset: the asset address of interest
        :type asset: str
        :param quote: the quote address of interest
        :type quote: str
        :param topNOrders: the depth of the book to return
        :type topNOrders: int
        :return: the book for the given asset and quote pair, returned as a sorted list of [[asset_amount, quote_amount, offer_id], ...]]]
        :rtype: list
        """

        try: 
            book = self.contract.functions.getBookFromPair(asset, quote, topNOrders).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            asset = self.w3.to_checksum_address(asset)
            quote = self.w3.to_checksum_address(quote)
            book = self.contract.functions.getBookFromPair(asset, quote, topNOrders).call()
        except Exception as e:
            return None
        
        return book

    ######################################################################
    # events & helpers
    ######################################################################

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_swap_hash(self): 
        return self.w3.keccak(text="LogSwap(uint256,address,uint256,address,bytes32,uint256,address)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_swap(self, data): 

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:  
            event = get_event_data(self.codec, self.log_swap_abi, data['params']['result'])

            # TODO: parse out the pair from the bytes encoding that is passed in the event (bytes32)
            # now pass the swap back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            swap = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'inputAmount': event['args']['inputAmount'],
                    'inputERC20': event['args']['inputERC20'],
                    'hurdleBuyAmtMin': event['args']['hurdleBuyAmtMin'],
                    'targetERC20': event['args']['targetERC20'],
                    'pair': event['args']['pair'],
                    'realizedFill': event['args']['realizedFill'],
                    'recipient': event['args']['recipient'],
            }
            return swap
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None
    
    def parse_log_swap(self, log):

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_swap_abi, log)

            # decode the pair 
            # TODO: this be broke 
            pair = decode(['bytes32'], event['args']['pair'])[0]

            # now pass the swap back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            swap = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'inputAmount': event['args']['inputAmount'],
                    'inputERC20': event['args']['inputERC20'],
                    'hurdleBuyAmtMin': event['args']['hurdleBuyAmtMin'],
                    'targetERC20': event['args']['targetERC20'],
                    'pair': pair,
                    'realizedFill': event['args']['realizedFill'],
                    'recipient': event['args']['recipient'],
            }
            return swap
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None

class RubiconRouterSigner(RubiconRouter):
    """this class represents a RubiconRouter.sol contract with read and write functionality. it is the super class of the RubiconRouter class, and inherints the read functionality from it.

    :param w3: Web3 instance
    :type w3: Web3
    :param wallet: the signers wallet address 
    :type wallet: str
    :param key: the signers private key
    :type key: str
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 Object, optional
    """

    def __init__(self, w3, wallet, key, contract=None):
        super().__init__(w3, contract)
        self.chain = w3.eth.chain_id
        self.wallet = wallet
        self.key = key

    ######################################################################
    # write calls
    ######################################################################

    # swap(pay_amt (uint256), buy_amt_min (uint256), route (address[]), expectedMarketFeeBPS (uint256))
    def swap(self, pay_amt, buy_amt_min, route, expected_market_fee_bps=1, nonce=None, gas=3000000, gas_price=None):
        """this function swaps the pay_amt of the first token in the route array for at least the buy_amt_min of the last token in the route array

        :param pay_amt: the amount of the first token in the route array to swap, as an integer amount of the token's smallest unit
        :type pay_amt: int
        :param buy_amt_min: the minimum amount of the last token in the route array to receive, as an integer amount of the token's smallest unit
        :type buy_amt_min: int
        :param route: array of addresses representing the path of tokens to swap through
        :type route: list
        :param expected_market_fee_bps: the market fee, defaults to 1
        :type expected_market_fee_bps: int, optional
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the swap transaction, returns None if the transaction fails
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try: 
            swap = self.contract.functions.swap(pay_amt, buy_amt_min, route, expected_market_fee_bps).build_transaction(txn)
            swap = self.w3.eth.account.sign_transaction(swap, self.key)
            self.w3.eth.send_raw_transaction(swap.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return swap