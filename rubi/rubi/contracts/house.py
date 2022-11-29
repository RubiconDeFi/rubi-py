import hexbytes
from web3 import Web3 
import logging as log
from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data

from rubi.contracts.helper import networks

class BathHouse: 
    """this class represents the BathHouse.sol contract and has read functionality for the contract
    
    :param w3: Web3 instance
    :type w3: Web3
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 object, optional
    """

    # init function
    def __init__(self, w3, contract=None):
        """constructor method"""

        chain = w3.eth.chain_id

        if contract:
            self.contract = contract
            self.address = self.contract.address
        else:
            network = networks[chain]()
            self.contract = w3.eth.contract(address=network.house, abi=network.house_abi)
            self.address = network.house

        self.chain = chain
        self.w3 = w3
        self.log_new_bath_token_abi = self.contract.events.LogNewBathToken()._get_event_abi()
        self.codec: ABICodec = w3.codec

    ######################################################################
    # read calls
    ######################################################################  
    
    # RubiconMarketAddress()
    def rubicon_market_address(self):
        """returns the address of the RubiconMarket contract

        :return: rubicon market address
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
        """returns the admin address of the contract

        :return: admin address
        :rtype: str
        """

        try: 
            admin = self.contract.functions.admin().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return admin

    # getBathTokenFromAsset(asset (address))
    def get_bath_token_from_asset(self, asset):
        """returns the bathtoken that is associated with the asset, returns a zero address if no bathtoken is associated with the asset

        :param asset: asset address
        :type asset: str
        :return: bath token address
        :rtype: str
        """

        try: 
            bath_token = self.contract.functions.getBathTokenFromAsset(asset).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            bath_token = self.contract.functions.getBathTokenFromAsset(Web3.to_checksum_address(asset)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return bath_token
    
    # newBathTokenImplementation()
    def new_bath_token_implementation(self):
        """returns the newest bath token implementation address

        :return: address of the newest bath token implementation
        :rtype: str
        """

        try: 
            new_bath_token_implementation = self.contract.functions.newBathTokenImplementation().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return new_bath_token_implementation

    ######################################################################
    # events & helpers
    ######################################################################

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_new_bath_token_hash(self):
        return self.w3.keccak(text="LogNewBathToken(address,address,address,uint256,address)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_new_bath_token(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_new_bath_token_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            new_bath_token = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'underlying_token': event['args']['underlyingToken'],  
                    'bath_token_address': event['args']['bathTokenAddress'],
                    'fee_admin': event['args']['bathTokenFeeAdmin'],
                    'timestamp': event['args']['timestamp'],
                    'creator': event['args']['bathTokenCreator']
            }
            return new_bath_token

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    def parse_log_new_bath_token(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_new_bath_token_abi, log)

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            new_bath_token = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'underlying_token': event['args']['underlyingToken'],  
                    'bath_token_address': event['args']['bathTokenAddress'],
                    'fee_admin': event['args']['bathTokenFeeAdmin'],
                    'timestamp': event['args']['timestamp'],
                    'creator': event['args']['bathTokenCreator']
            }
            return new_bath_token
        
        except Exception as e:
            log.error(e, exc_info=True)
            return None

class BathHouseSigner(BathHouse):
    """this class represents the BathHouse.sol contract and has read and write functionality for the contract. this class inherits from the BathHouse class and adds the ability to sign transactions.
    
    :param w3: Web3 instance
    :type w3: Web3
    :parm wallet: the signers wallet address
    :type wallet: str
    :param key: the signers private key
    :type key: str
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 object, optional
    """

    # init function
    def __init__(self, w3, wallet, key, contract=None):
        super().__init__(w3, contract)
        self.wallet = wallet
        self.key = key
    
    ######################################################################
    # write calls
    ######################################################################

    # createBathToken(underlyingERC20 (address), _feeAdmin (address))
    def create_bath_token(self, underlying_erc20, fee_admin,  nonce=None, gas=3000000, gas_price=None):
        """creates a new bath token

        :param underlying_erc20: address of the underlying token
        :type underlying_erc20: str
        :param fee_admin: address of the fee admin
        :type fee_admin: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the create bath token transaction, None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price
        
        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            bath_token = self.contract.functions.createBathToken(underlying_erc20, fee_admin).buildTransaction(txn)
            bath_token = self.w3.eth.account.sign_transaction(bath_token, self.wallet.privateKey)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            bath_token = self.contract.functions.createBathToken(Web3.to_checksum_address(underlying_erc20), Web3.to_checksum_address(fee_admin)).buildTransaction(txn)
            bath_token = self.w3.eth.account.sign_transaction(bath_token, self.wallet.privateKey)
            self.w3.eth.send_raw_transaction(bath_token.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return bath_token
