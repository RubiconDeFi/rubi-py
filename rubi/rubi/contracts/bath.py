import hexbytes
import logging as log
from web3 import Web3 
from eth_abi.codec import ABICodec
from web3._utils.events import get_event_data

from rubi.contracts.helper import networks

class BathToken: 
    """this class represents the BathToken.sol contract and has read functionality for the contract
    
    :param w3: Web3 instance
    :type w3: Web3
    :param contract: an optional contract instance, if not provided, the contract will be instantiated using the address and abi from the networks.py file given the chain id of the w3 instance
    :type contract: Web3 object, optional
    """

    # init function
    def __init__(self, address, w3, contract=None):
        """constructor method"""

        chain = w3.eth.chain_id

        if contract:
            self.contract = contract
            self.address = self.contract.address
        else:  
            network = networks[chain]()
            self.contract = w3.eth.contract(address=address, abi=network.bath_abi)
            self.address = address

        # set the class variables
        self.chain = chain 
        self.w3 = w3
        self.log_deposit_abi = self.contract.events.LogDeposit()._get_event_abi()
        self.log_withdraw_abi = self.contract.events.LogWithdraw()._get_event_abi()
        self.transfer_abi = self.contract.events.Transfer()._get_event_abi()
        self.codec: ABICodec = w3.codec

    ######################################################################
    # read calls
    ######################################################################  

    # allowance(owner (address), spender (address))
    def allowance(self, owner, spender):
        """returns the allowance of the spender for the owner 

        :param owner: the owner of the tokens
        :type owner: str
        :param spender: the spender of the tokens
        :type spender: str
        :return: the allowance of the spender for the owner in the integer representation of the asset, None if there is an error
        :rtype: int, None
        """

        try: 
            allowance = self.contract.functions.allowance(owner, spender).call()
        except ValueError: 
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            allowance = self.contract.functions.allowance(Web3.to_checksum_address(owner), Web3.to_checksum_address(spender)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return allowance

    # asset()
    def asset(self):
        """returns the asset address of the contract

        :return: the asset address of the contract
        :rtype: str
        """

        try: 
            asset = self.contract.functions.asset().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return asset

    # balanceOf(account (address))
    def balanceOf(self, account):
        """returns the balance of the account in the integer representation of the asset

        :param account: the account to check the balance of
        :type account: str
        :return: the balance of the account in the integer representation of the asset, None if there is an error
        :rtype: int, None
        """

        try: 
            balance = self.contract.functions.balanceOf(account).call()
        except ValueError:  
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            balance = self.contract.functions.balanceOf(Web3.to_checksum_address(account)).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return balance

    # convertToAssets(shares (uint256))
    def convertToAssets(self, shares):

        """converts shares to their claim on underlying assets amounts

        :param shares: the number of shares to convert to assets
        :type shares: int
        :return: the number of assets that the shares represent 
        :rtype: int
        """

        try: 
            assets = self.contract.functions.convertToAssets(shares).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return assets

    # convertToShares(assets (uint256))
    def convertToShares(self, assets):
        """convert assets to their potential share amounts

        :param assets: the number of assets to convert to shares
        :type assets: int
        :return: the number of shares that the assets represent
        :rtype: int
        """

        try: 
            shares = self.contract.functions.convertToShares(assets).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return shares

    # decimals()
    def decimals(self):
        """returns the number of decimals of the asset

        :return: the number of decimals of the asset
        :rtype: int
        """

        try: 
            decimals = self.contract.functions.decimals().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return decimals

    # feeBPS()
    def feeBPS(self):
        """gets the withdrawal fee in basis points

        :return: the withdrawal fee in basis points
        :rtype: int
        """

        try: 
            feeBPS = self.contract.functions.feeBPS().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return feeBPS

    # feeTo()
    def feeTo(self):
        """gets the address that receives the withdrawal fee

        :return: the address that receives the withdrawal fee
        :rtype: str
        """

        try: 
            feeTo = self.contract.functions.feeTo().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return feeTo

    # initialized()
    def initialized(self):
        """check if the contract has been initialized
        
        :return: True if the contract has been initialized, False otherwise
        :rtype: bool
        """

        try: 
            initialized = self.contract.functions.initialized().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return initialized

    # outstandingAmount()
    def outstandingAmount(self):
        """gets the amount of the underlying asset that is outstanding on the books
        
        :return: the amount of the underlying asset that is outstanding on the books, in the integer representation of the asset
        :rtype: int
        """

        try: 
            outstandingAmount = self.contract.functions.outstandingAmount().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return outstandingAmount

    # underlyingBalance()
    def underlyingBalance(self):
        """gets the underlying balance of assets on the contract
        
        :return: the underlying balance of assets on the contract, in the integer representation of the asset
        :rtype: int
        """

        try: 
            underlyingBalance = self.contract.functions.underlyingBalance().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return underlyingBalance

    # totalSupply()
    def totalSupply(self):
        """gets the total supply of shares
        
        :return: the total supply of shares
        :rtype: int
        """

        try: 
            totalSupply = self.contract.functions.totalSupply().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return totalSupply
    
    ######################################################################
    # events & helpers
    ######################################################################

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_transfer_hash(self):
        return self.w3.keccak(text="Transfer(address,address,uint256)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_transfer(self, data): 

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.transfer_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            transfer = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'from': event['args']['from'],  
                    'to': event['args']['to'],
                    'value': event['args']['value']
            }
            return transfer

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    def parse_log_deposit(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.transfer_abi, log['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            transfer = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'from': event['args']['from'],  
                    'to': event['args']['to'],
                    'value': event['args']['value']
            }
            return transfer

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_deposit_hash(self):
        return self.w3.keccak(text="LogDeposit(uint256,IERC20,uint256,address,uint256,uint256,uint256)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_deposit(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_deposit_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            deposit = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'deposit_amt': event['args']['depositedAmt'],  
                    'asset': event['args']['asset'],
                    'shares_received': event['args']['sharesReceived'],
                    'depositor': event['args']['depositor'],
                    'underlying_balance': event['args']['underlyingBalance'],
                    'outstanding_amount': event['args']['outstandingAmount'],
                    'total_supply': event['args']['totalSupply']
            }
            return deposit

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    def parse_log_deposit(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_deposit_abi, log['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            deposit = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'deposit_amt': event['args']['depositedAmt'],  
                    'asset': event['args']['asset'],
                    'shares_received': event['args']['sharesReceived'],
                    'depositor': event['args']['depositor'],
                    'underlying_balance': event['args']['underlyingBalance'],
                    'outstanding_amount': event['args']['outstandingAmount'],
                    'total_supply': event['args']['totalSupply']
            }
            return deposit

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # TODO: today the event signature is hardcoded, but we should be able to get it from the contract
    # the graph does something similar to this when you run codegen, it should be a simple string manipulation problem from the abis 
    def get_log_withdraw_hash(self):
        return self.w3.keccak(text="LogWithdraw(uint256,IERC20,uint256,address,uint256,address,uint256,uint256,uint256)").hex()

    # TODO: determine if this is the right assumtption to make about how the data is being received 
    # this assumes that the function is being used directly in the context of being passed raw data from a websocket stream that has been loaded and converted to an AttributeDict
    # TODO: i feel like this could be done much faster... tracing will tell us
    def stream_log_withdraw(self, data): 

        # load the data into an attribute dictionary that web3 can use
        # data = AttributeDict(json.loads(data))

        # convert the topics, transaction hash, and block hash to hex strings
        data['params']['result']['topics'] = [hexbytes.HexBytes(topic) for topic in data['params']['result']['topics']]
        data['params']['result']['transactionHash'] = hexbytes.HexBytes(data['params']['result']['transactionHash'])
        data['params']['result']['blockHash'] = hexbytes.HexBytes(data['params']['result']['blockHash'])

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_withdraw_abi, data['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            withdraw = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'amt_withdrawn': event['args']['amountWithdrawn'],  
                    'asset': event['args']['asset'],
                    'shares_withdrawn': event['args']['sharesWithdrawn'],
                    'withdrawer': event['args']['withdrawer'],
                    'fee': event['args']['fee'],
                    'fee_to': event['args']['feeTo'],
                    'underlying_balance': event['args']['underlyingBalance'],
                    'outstanding_amount': event['args']['outstandingAmount'],
                    'total_supply': event['args']['totalSupply']
            }
            return withdraw

        except Exception as e:
            log.error(e, exc_info=True)
            return None

    def parse_log_withdraw(self, log): 

        # get the event data from the log
        try:
            event = get_event_data(self.codec, self.log_withdraw_abi, log['params']['result'])

            # now pass an offer back in the form of a dictionary
            # TODO: this is probably not the most performant, we will optimize later
            withdraw = {
                    'txn': event['transactionHash'].hex(),
                    'event': event['event'],
                    'amt_withdrawn': event['args']['amountWithdrawn'],  
                    'asset': event['args']['asset'],
                    'shares_withdrawn': event['args']['sharesWithdrawn'],
                    'withdrawer': event['args']['withdrawer'],
                    'fee': event['args']['fee'],
                    'fee_to': event['args']['feeTo'],
                    'underlying_balance': event['args']['underlyingBalance'],
                    'outstanding_amount': event['args']['outstandingAmount'],
                    'total_supply': event['args']['totalSupply']
            }
            return withdraw

        except Exception as e:
            log.error(e, exc_info=True)
            return None

class BathTokenSigner(BathToken):
    """this class represents the BathToken.sol contract and is the super class of the BathToken class. it has both read and write functionality, and inherits its read functionality from the BahtToken class

    :param address: the addres of the bathtoken contract instance to interact with
    :type address: str
    :param w3: the web3 instance to use for interacting with the contract
    :type w3: Web3 object
    :param wallet: the signers wallet address
    :type wallet: str
    :param key: the signers private key
    :type key: str
    :param contract: an optional parameter that allows you to pass in a contract instance, if none the contract will be instantiated from the rolodex.py file
    :type contract_address: str, optional
    """

    def __init__(self, address, w3, wallet, key, contract=None):
        super().__init__(address, w3, contract)
        self.wallet = wallet
        self.key = key

    ######################################################################
    # write calls
    ######################################################################

    # approve(spender (address), amount (uint256))
    def approve(self, spender, amount, nonce=None, gas=3000000, gas_price=None):
        
        """this function approves the spender to spend the amount of tokens on behalf of the signer

        :param spender: the address of the spender
        :type spender: str
        :param amount: the amount of tokens to approve the spender to spend
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the approve transaction, or None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try: 
            approve = self.contract.functions.approve(spender, amount).buildTransaction(txn)
            approve = self.w3.eth.account.sign_transaction(approve, private_key=self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            approve = self.contract.functions.approve(self.w3.to_checksum_address(spender), amount).buildTransaction(txn)
            approve = self.w3.eth.account.sign_transaction(approve, private_key=self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return approve

    # transfer(recipient (address), amount (uint256))
    def transfer(self, recipient, amount, nonce=None, gas=3000000, gas_price=None):
        """a function to transfer tokens from the signer to the recipient

        :param recipient: the address of the recipient
        :type recipient: str
        :param amount: the amount of tokens to transfer
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the transfer transaction, or None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            transfer = self.contract.functions.transfer(recipient, amount).buildTransaction(txn)
            transfer = self.w3.eth.account.sign_transaction(transfer, private_key=self.key)
            self.w3.eth.send_raw_transaction(transfer.rawTransaction)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            transfer = self.contract.functions.transfer(self.w3.to_checksum_address(recipient), amount).buildTransaction(txn)
            transfer = self.w3.eth.account.sign_transaction(transfer, private_key=self.key)
            self.w3.eth.send_raw_transaction(transfer.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return transfer

    # transferFrom(sender (address), recipient (address), amount (uint256))
    def transfer_from(self, sender, recipient, amount, nonce=None, gas=3000000, gas_price=None):

        """a function to transfer tokens from the sender to the recipient on behalf of the signer

        :param sender: the address of the sender
        :type sender: str
        :param recipient: the address of the recipient
        :type recipient: str
        :param amount: the amount of tokens to transfer, in the integer representation of the token
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the transferFrom transaction, or None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)
    
        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            transfer_from = self.contract.functions.transferFrom(sender, recipient, amount).buildTransaction(txn)
            transfer_from = self.w3.eth.account.sign_transaction(transfer_from, private_key=self.key)
            self.w3.eth.send_raw_transaction(transfer_from.rawTransaction)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            transfer_from = self.contract.functions.transferFrom(self.w3.to_checksum_address(sender), self.w3.to_checksum_address(recipient), amount).buildTransaction(txn)
            transfer_from = self.w3.eth.account.sign_transaction(transfer_from, private_key=self.key)
            self.w3.eth.send_raw_transaction(transfer_from.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return transfer_from

    # deposit(assets (uint256), receiver (address))
    def deposit(self, assets, receiver, nonce=None, gas=3000000, gas_price=None):
        """a function to deposit assets into the bathtoken contract and receive tokens in return
        
        :param assets: the amount of assets to deposit, in the integer representation of the token
        :type assets: int
        :param receiver: the address of the receiver of the tokens
        :type receiver: str
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)

        if gas_price is None:
            gas_price = self.w3.eth.gas_price

        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            deposit = self.contract.functions.deposit(assets, receiver).buildTransaction(txn)
            deposit = self.w3.eth.account.sign_transaction(deposit, private_key=self.key)
            self.w3.eth.send_raw_transaction(deposit.rawTransaction)
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            deposit = self.contract.functions.deposit(assets, self.w3.to_checksum_address(receiver)).buildTransaction(txn)
            deposit = self.w3.eth.account.sign_transaction(deposit, private_key=self.key)
            self.w3.eth.send_raw_transaction(deposit.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None

    # withdraw(shares (uint256))
    def withdraw(self, shares, nonce=None, gas=3000000, gas_price=None):
        """a function to withdraw the underlying asset from the bathtoken contract in exchange for tokens

        :param shares: the amount of tokens to burn, in the integer representation of the token
        :type shares: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the withdraw transaction, or None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price
        
        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}
    
        try:
            withdraw = self.contract.functions.withdraw(shares).buildTransaction(txn)
            withdraw = self.w3.eth.account.sign_transaction(withdraw, private_key=self.key)
            self.w3.eth.send_raw_transaction(withdraw.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return withdraw

    # getAllBonusTokenReward()
    def get_all_bonus_token_reward(self, nonce=None, gas=3000000, gas_price=None):
        """a function to get all the bonus tokens that have been earned by the user

        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the getAllBonusTokenReward transaction, or None if the transaction failed
        :rtype: dict, None
        """

        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(self.wallet)
        
        # TODO: figure out a way to dynamically set gas
        if gas is None:
            gas = 3000000
        
        if gas_price is None:
            gas_price = self.w3.eth.gas_price
        
        txn = {'chainId': self.chain, 'gas' : gas, 'gasPrice': gas_price, 'nonce': nonce}

        try:
            get_all_bonus_token_reward = self.contract.functions.getAllBonusTokenReward().buildTransaction(txn)
            get_all_bonus_token_reward = self.w3.eth.account.sign_transaction(get_all_bonus_token_reward, private_key=self.key)
            self.w3.eth.send_raw_transaction(get_all_bonus_token_reward.rawTransaction)
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return get_all_bonus_token_reward

    ######################################################################
    # 
    ######################################################################