import os
import json
import logging as log
from web3 import Web3 

class ERC20:
    """this class represents a contract that implements the ERC20 standard. it is used to read the contract instance. 

    :param w3: Web3 instance
    :type w3: Web3
    :param address: address of the contract
    :type address: str
    """

    # init function
    def __init__(self, w3, address, contract=None):
        """constructor method"""

        if contract:
            self.contract = contract
            self.address = contract.address
        else:
            path = f"{os.path.dirname(os.path.realpath(__file__))}/abis/"

            with open(path + 'ERC20.json') as f:
                abi = json.load(f)
            f.close()
            #abi = json.load(open(path + 'ERC20.json'))

            try: 
                contract = w3.eth.contract(address=address, abi=abi)
            except ValueError:
                log.warning('most likely a checksum error... retrying with checksummed addresses')
                address = w3.to_checksum_address(address)
                contract = w3.eth.contract(address=address, abi=abi)
            except Exception as e:
                log.error(e, exc_info=True)
                return None

            # set the class variables
            self.contract = contract
            self.address = address

        self.w3 = w3

        # TODO: i believe decimals is an optional function that may not be implemented, so this may need an error handler
        self.decimal = self.contract.functions.decimals().call()
        self.token_symbol = self.contract.functions.symbol().call()
        self.token_name = self.contract.functions.name().call()

    ######################################################################
    # read calls
    ######################################################################  

    # allowance(owner (address), spender (address))
    def allowance(self, owner, spender):
        """reads the allowance of the spender from the owner for the erc20 contract

        :param owner: address that owns the erc20 tokens
        :type owner: str
        :param spender: address that is allowed to spend the erc20 tokens
        :type spender: str
        :return: the allowance of the spender from the owner for the contract, in the integer representation of the token
        :rtype: int
        """

        # TODO: see if there is a way to make the exception more specific to only the checksum error 
        try: 
            allowance = self.contract.functions.allowance(owner, spender).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            owner = self.w3.to_checksum_address(owner)
            spender = self.w3.to_checksum_address(spender)
            allowance = self.contract.functions.allowance(owner, spender).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return allowance

    # balanceOf(account (address))
    def balance_of(self, account):
        """reads the erc20 balance of the account 

        :param account: the address of the account to read the balance of
        :type account: str
        :return: the balance of the account, in the integer representation of the token
        :rtype: int
        """

        try: 
            balance = self.contract.functions.balanceOf(account).call()
        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            account = self.w3.to_checksum_address(account)
            balance = self.contract.functions.balanceOf(account).call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return balance

    # totalSupply()
    def total_supply(self):
        """reads the total supply of the erc20 token
        
        :return: the total supply of the erc20 token, in the integer representation of the token
        :rtype: int
        """

        try: 
            total_supply = self.contract.functions.totalSupply().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return total_supply
    
    # decimals() 
    def decimals(self):
        """reads the number of decimals of the erc20 token - warning this is not a constant function, so it may result in an error in its current implementation

        :return: the number of decimals of the erc20 token
        :rtype: int
        """

        try: 
            decimals = self.contract.functions.decimals().call()
        except Exception as e:
            log.warning('error message: ', e)
            return None
        
        return decimals

    # name()
    def name(self):
        """reads the name of the erc20 token

        :return: the name of the erc20 token
        :rtype: str
        """
            
        try: 
            name = self.contract.functions.name().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return name

    # symbol()
    def symbol(self):
        """reads the symbol of the erc20 token

        :return: the symbol of the erc20 token
        :rtype: str
        """

        try: 
            symbol = self.contract.functions.symbol().call()
        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return symbol

    # convert an integer representation of the token to a float representation of the token
    def to_float(self, integer):
        """converts an integer representation of the token to a float representation of the token by dividing the integer by 10 to the power of the number of decimals of the token
        
        :param integer: the integer representation of the token
        :type integer: int
        :return: the float representation of the token
        :rtype: float
        """

        if integer == 0:
            return 0
        else: 
            return integer / (10 ** self.decimal)

    # convert a float representation of the token to an integer representation of the token
    def to_integer(self, float):
        """converts a float representation of the token to an integer representation of the token by multiplying the float by 10 to the power of the number of decimals of the token
        
        :param float: the float representation of the token
        :type float: float
        :return: the integer representation of the token
        :rtype: int
        """

        if float == 0:
            return 0
        else:
            return int(float * (10 ** self.decimal))

class ERC20Signer(ERC20): 
    """this class represents a contract that implements the ERC20 standard. it is a super class of the ERC20 class as it has write functionality. it is used to read and write to the contract instance.
    
    :param w3: Web3 instance
    :type w3: Web3
    :param address: address of the erc20 contract
    :type address: str
    :param wallet: wallet address of the signer
    :type wallet: str
    :param key: private key of the signer
    :type key: str
    """

    def __init__(self, w3, address, wallet, key, contract=None):
        super().__init__(w3, address)
        self.chain = w3.eth.chain_id
        self.wallet = wallet
        self.key = key

    ######################################################################
    # write calls
    ######################################################################

    # approve(spender (address), amount (uint256))
    def approve(self, spender, amount, nonce=None, gas=3000000, gas_price=None):
        """approves the spender to spend the amount of the erc20 token from the signer's wallet

        :param spender: address of the spender
        :type spender: str
        :param amount: amount of the erc20 token to approve the spender to spend
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :return: the transaction object of the approve transaction
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
            # TODO: issue #7
            approve = self.contract.functions.approve(spender, amount).build_transaction(txn) 
            approve = self.w3.eth.account.sign_transaction(approve, self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(approve.hash)['status'] == 0:
                    log.error(f'approve transaction {approve.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            approve = self.contract.functions.approve(self.w3.to_checksum_address(spender), amount).build_transaction(txn)
            approve = self.w3.eth.account.sign_transaction(approve, self.key)
            self.w3.eth.send_raw_transaction(approve.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(approve.hash)['status'] == 0:
                    log.error(f'approve transaction {approve.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return approve

    # transfer(recipient (address), amount (uint256))
    def transfer(self, recipient, amount, nonce=None, gas=3000000, gas_price=None):
        """transfers the amount of the erc20 token to the recipient

        :param recipient: address of the recipient
        :type recipient: str
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the transfer transaction
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
            transfer = self.contract.functions.transfer(recipient, amount).build_transaction(txn)
            transfer = self.w3.eth.account.sign_transaction(transfer, self.key)
            self.w3.eth.send_raw_transaction(transfer.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(transfer.hash)['status'] == 0:
                    log.error(f'transfer transaction {transfer.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            transfer = self.contract.functions.transfer(self.w3.to_checksum_address(recipient), amount).build_transaction(txn)
            transfer = self.w3.eth.account.sign_transaction(transfer, self.key)
            self.w3.eth.send_raw_transaction(transfer.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(transfer.hash)['status'] == 0:
                    log.error(f'transfer transaction {transfer.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None
        
        return transfer

    # transferFrom(sender (address), recipient (address), amount (uint256))
    def transfer_from(self, sender, recipient, amount, nonce=None, gas=3000000, gas_price=None):
        """transfers the amount of the erc20 token from the sender to the recipient

        :param sender: address of the sender
        :type sender: str
        :param recipient: address of the recipient
        :type recipient: str
        :param amount: amount of the erc20 token to transfer
        :type amount: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the transferFrom transaction
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
            transfer_from = self.contract.functions.transferFrom(sender, recipient, amount).build_transaction(txn)
            transfer_from = self.w3.eth.account.sign_transaction(transfer_from, self.key)
            self.w3.eth.send_raw_transaction(transfer_from.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(transfer_from.hash)['status'] == 0:
                    log.error(f'transfer_from transaction {transfer_from.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            transfer_from = self.contract.functions.transferFrom(self.w3.to_checksum_address(sender), self.w3.to_checksum_address(recipient), amount).build_transaction(txn)
            transfer_from = self.w3.eth.account.sign_transaction(transfer_from, self.key)
            self.w3.eth.send_raw_transaction(transfer_from.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(transfer_from.hash)['status'] == 0:
                    log.error(f'transfer_from transaction {transfer_from.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return transfer_from
        

    # increaseAllowance(spender (address), addedValue (uint256))
    def increase_allowance(self, spender, added_value, nonce=None, gas=3000000, gas_price=None):
        """increases the allowance of the spender by the added_value

        :param spender: address of the spender
        :type spender: str
        :param added_value: amount to increase the allowance by, in the integer representation of the erc20 token
        :type added_value: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the increaseAllowance transaction
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
            increase_allowance = self.contract.functions.increaseAllowance(spender, added_value).build_transaction(txn)
            increase_allowance = self.w3.eth.account.sign_transaction(increase_allowance, self.key)
            self.w3.eth.send_raw_transaction(increase_allowance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(increase_allowance.hash)['status'] == 0:
                    log.error(f'increase_allowance transaction {increase_allowance.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            increase_allowance = self.contract.functions.increaseAllowance(self.w3.to_checksum_address(spender), added_value).build_transaction(txn)
            increase_allowance = self.w3.eth.account.sign_transaction(increase_allowance, self.key)
            self.w3.eth.send_raw_transaction(increase_allowance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(increase_allowance.hash)['status'] == 0:
                    log.error(f'increase_allowance transaction {increase_allowance.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return increase_allowance

    # decreaseAllowance(spender (address), subtractedValue (uint256))
    def decrease_allowance(self, spender, subtracted_value, nonce=None, gas=3000000, gas_price=None):
        """decreases the allowance of the spender by the subtracted_value

        :param spender: address of the spender
        :type spender: str
        :param subtracted_value: amount to decrease the allowance by, in the integer representation of the erc20 token
        :type subtracted_value: int
        :param nonce: nonce of the transaction, defaults to calling the chain state to get the nonce
        :type nonce: int, optional
        :param gas: gas limit of the transaction, defaults to a value of 3000000
        :type gas: int, optional
        :param gas_price: gas price of the transaction, defaults to the gas price of the chain
        :type gas_price: int, optional
        :return: the transaction object of the decreaseAllowance transaction
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
            decrease_allowance = self.contract.functions.decreaseAllowance(spender, subtracted_value).build_transaction(txn)
            decrease_allowance = self.w3.eth.account.sign_transaction(decrease_allowance, self.key)
            self.w3.eth.send_raw_transaction(decrease_allowance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(decrease_allowance.hash)['status'] == 0:
                    log.error(f'decrease_allowance transaction {decrease_allowance.hash.hex()} failed')
                    raise SystemExit()

        except ValueError:
            log.warning('most likely a checksum error... retrying with checksummed addresses')
            decrease_allowance = self.contract.functions.decreaseAllowance(self.w3.to_checksum_address(spender), subtracted_value).build_transaction(txn)
            decrease_allowance = self.w3.eth.account.sign_transaction(decrease_allowance, self.key)
            self.w3.eth.send_raw_transaction(decrease_allowance.rawTransaction)

            # if a user is not providing a nonce, wait for the transaction to either be confirmed or rejected before continuing
            if nonce is None:
                if self.w3.eth.wait_for_transaction_receipt(decrease_allowance.hash)['status'] == 0:
                    log.error(f'decrease_allowance transaction {decrease_allowance.hash.hex()} failed')
                    raise SystemExit()

        except Exception as e:
            log.error(e, exc_info=True)
            return None

        return decrease_allowance

    ######################################################################
    # 
    ###################################################################### 