basic example of market aid functionality 
==========================================================
this is a basic example of the market aid functionality in the rubi sdk. more information about the market aid contract can be found `in the protocol docs <https://docs.rubicon.finance/docs/protocol/rubicon-market/market-aid)>`_. 
in short, the market aid contract allows a user to allocate funds to a smart contract that can then be used to interact with the RubiconMarket.sol contract on the user's behalf.
the market aid contract includes a variety of useful higher level functions, such as placing and updating multiple market orders at once, and can be used to approve other EOA's on behalf of the user, track portfolio balances, and emit event data to be indexed. 

setup and installation
-----------------------

utilizing either `pip <https://pip.pypa.io/en/stable/>`_ or `poetry <https://python-poetry.org/docs/basic-usage/>`_ , install the `rubi`, `web3`, and `python-dotenv` packages with the following command(s)

.. code-block:: bash

    (venv) pip install rubi
    (venv) pip install web3
    (venv) pip install python-dotenv

.. code-block:: bash

    (rubi-py3.10) poetry add rubi                   
    (rubi-py3.10) poetry add web3
    (rubi-py3.10) poetry add python-dotenv

in order to utilize the `rubi` package you will need to first create a `web3 object <https://web3py.readthedocs.io/en/v5/>`_. you will need an optimism node enpoint to do so. you can find more information regarding optimism rpc endpoints `in the optimism docs <https://community.optimism.io/docs/useful-tools/networks/>`_.
in order to sign transactions the user will need a wallet and private key. more information on wallets can be found `in the ethereum docs <https://ethereum.org/en/wallets/>`_.
you will need to set up a `.env file <https://improveandrepeat.com/2022/01/python-friday-107-working-with-env-files-in-python/#:~:text=env%20file%20is%20a%20great,your%20Python%20code%20as%20well.>`_ in the root directory of the project. this file will contain the private key of the account you wish to use to interact with the market aid contract. the .env file should look like this

.. code-block:: text

    OP_MAINNET_NODE = <an optimism mainnet node endpoint>
    OP_GOERLI_NODE = <only for testing purposes, an optimism goerli node endpoint>
    DEV_KEYS = <the private key of the EOA being used to sign tranactions>
    DEV_EOA = <the EOA that is being used to sign transactions and pay gas for said transactions>

deploying a market aid contract and placing your first trades
-------------------------------------------------------------

now that we have our environment variables and packages installed, lets actually deploy a market aid contract and place our first trades. in order to do so, we will need to import the `rubi` package, the `web3` package, and the `dotenv` package. we will also need to import the `os` package in order to access our environment variables.

.. code-block:: python

    import os
    import rubi as Rubi
    from web3 import Web3
    from dotenv import load_dotenv

    load_dotenv()

    # set the env variables
    OP_MAINNET_NODE = os.getenv("OP_MAINNET_NODE")
    OP_GOERLI_NODE = os.getenv("OP_GOERLI_NODE")
    DEV_EOA = os.getenv("DEV_EOA")
    DEV_KEYS = os.getenv("DEV_KEYS")

    # ensure the env variables are set
    if None in [OP_MAINNET_NODE, OP_GOERLI_NODE, DEV_EOA, DEV_KEYS]:
        raise ValueError("Please set the environment variables, either update or create a .env file")

in order to interact with the `rubi` package, we will need to create a `web3` object. the `web3` object will be used to interact with the optimism node endpoint, and will be used to sign transactions. `rubi` is mostly a wrapper around the `web3` package, and over time will be expanded to include more functionality. 

.. code-block:: python 

    # create a web3 instance
    w3 = Web3(Web3.HTTPProvider(OP_MAINNET_NODE))

    # create a rubicon instance
    rubi = Rubi.Rubicon(w3, wallet=DEV_EOA, key=DEV_KEYS)
    
    # get the current nonce of the dev account
    nonce = rubi.w3.eth.get_transaction_count(rubi.wallet)

now, we will see if the current wallet has any associated market aid contracts. if the wallet is associated with a market aid instance, we will connect to the first one it finds for the purpose of this example. if it does not, we will deploy a market aid contract that we will then connect to.

.. code-block:: python 

    # check that the user does not currently have any market aid contracts deployed 
    aids = rubi.factory.get_user_market_aids(rubi.wallet)

    if aids:
        print("\nyou already have a market aid contract deployed, lets connect to it!\n")
        aid_address = aids[0]
        aid = rubi.aid(aid_address)
    else:
        print("\nyou do not have a market aid contract deployed, lets deploy one!\n")
        rubi.factory.create_market_aid_instance(nonce = nonce)
        nonce += 1

        aids = rubi.factory.get_user_market_aids(rubi.wallet)
        aid_address = aids[0]
        aid = rubi.aid(aid_address)

        # check that the aid was deployed and connect to it 
        if aid.address:
            print("market aid deployed!")
            aid = rubi.aid(aid.address)

    # check that the aid is connected to the correct market and print out the aid address
    assert aid.rubicon_market_address() == rubi.market.address
    print("market aid address: ", aid.address, "\n")

the user is now connected to a market aid contract that it has created from the MarketAidFactory.sol contract. this market aid contract will hold the user's funds and place manage the funds on behalf of the user's EOA. 
to get started, we will need to first transfer some funds to the market aid contract. one of the benefits of this contract is that it allows the user to transfer funds to the contract without having to first approve the contract to spend the funds. this protects the user's funds from removing the need to allow a contract to spend its funds. 
we will utilize the `rolodex` class within the `rubi` package to access the `WETH` and `USDC` addresses on Optimism Mainnet. several other useful addresses are stored within this class, check it out `in the rubi repo <https://github.com/RubiconDeFi/rubi-py/blob/master/rubi/rubi/contracts/helper/erc20.py>`_!
each function can be utilized without passing in a `nonce <https://ethereum.stackexchange.com/questions/27432/what-is-nonce-in-ethereum-how-does-it-prevent-double-spending>`_, but to allow the transactions to execute in rapid succession we must manually set the nonce in this example. 
we hope to soon add a `nonce manager <https://github.com/RubiconDeFi/rubi-py/issues/14>`_ to the `rubi` package to allow for more seamless transactions.

.. code-block:: python 

    # access the rolodex of helpful addresses based upon the chain id of the node that is being used
    chain = rubi.chain
    rolodex = Rubi.contracts.helper.networks[chain]()

    # get the weth and usdc addresses
    weth = rolodex.weth
    usdc = rolodex.usdc

    # connect to the weth and usdc contracts
    weth = rubi.token(weth)
    usdc = rubi.token(usdc)

    # transfer some 0.01 weth and 10 usdc to the aid contract
    weth.transfer(aid.address, 1000000000000000, nonce=nonce)
    nonce += 1
    usdc.transfer(aid.address, 10000000, nonce=nonce)
    nonce += 1

the market aid contract has a function called `get_strategist_total_liquidity` that can be used to get the total liquidity of a set assset / quote pair, including any current offers on the book, and indicate if any offers are outstanding. 
lets now check the market aid contract for any outstanding offers and wipe any we may find. 

.. code-block:: python 

    # check the current balance of the aid contract
    balances = aid.get_strategist_total_liquidity(weth.address, usdc.address, rubi.wallet)

    # important to notice that the balances are returned in the order of [weth, usdc, outstanding trades], opposite of the order of the arguments
    weth_balance = balances[1]
    usdc_balance = balances[0]
    oustanding_trades = balances[2]

    # print out the current balance of the aid contract
    print("current balance of aid contract -> ", weth.symbol(), weth_balance / (10 ** weth.decimal), usdc.symbol(), usdc_balance / (10 ** usdc.decimal), "\n")
    print("does the contract have outstanding trades? [T/F] -> ", oustanding_trades, "\n")

    if oustanding_trades:
        
        # get the oustanding trades of the aid contract
        trades = aid.get_outstanding_strategist_trades(weth.address, usdc.address, rubi.wallet)

        # print out the oustanding trades of the aid contract
        print("oustanding trades -> ", trades, "\n")

        # if there are any oustanding trades, lets cancel them
        aid.scrub_strategist_trades(trades, gas=3000000, nonce=nonce)
        nonce += 1


finally, we will cover some of the higher level functionality of the market aid contract. this example includes the `batch_market_making_trades`, `batch_requote_all_offers`, and the `scrub_strategist_trades` functions. however, there are many other functions that can be utilized to manage the funds of the market aid contract, check them out `in the repo here <https://rubi.readthedocs.io/en/latest/rubi.html#rubi.contracts.MarketAidSigner>`_! 
we will first place a batch of offers that includes an offer to sell 0.01 ETH for 1000 USDC or an offer to buy 0.01 ETH for 1 USDC
we will then remove all offers for the set asset / quote pair from the book and replace them with a new batch of offers that includes an offer to sell 0.01 ETH for 10000 USDC or an offer to buy 0.01 ETH for .1 USDC
then, we will wipe all outstanding offers for the set asset / quote pair from the book before ending the tutorial. 

.. code-block:: python 

    # place a batch market making trade through the aid contract
    # this trade will create two new market offers, one selling the asset and one buying the asset 
    # this is an offer to sell 0.01 ETH for 1000 USDC or an offer to buy 0.01 ETH for 1 USDC
    aid.batch_market_making_trades([weth.address, usdc.address], [10000000000000000], [1000000000], [1000000], [10000000000000000], nonce = nonce)
    nonce += 1

    # now requote all of the outstanding trades
    # this is an offer to sell 0.01 ETH for 10000 USDC or an offer to buy 0.01 ETH for .1 USDC
    batch_requote = aid.batch_requote_all_offers([weth.address, usdc.address], [10000000000000000], [10000000000], [100000], [10000000000000000], nonce = nonce)
    nonce += 1

    # wait for the transaction to be mined
    hash = rubi.w3.eth.wait_for_transaction_receipt(batch_requote['hash'])

    # now cancel all of the outstanding trades
    if hash: 

        # get the oustanding trades of the aid contract
        trades = aid.get_outstanding_strategist_trades(weth.address, usdc.address, rubi.wallet)

        # if there are any oustanding trades, lets cancel them
        scrub = aid.scrub_strategist_trades(trades, gas=3000000, nonce=nonce)
        nonce += 1

        # wait for the transaction and check that the trades were cancelled
        hash = rubi.w3.eth.wait_for_transaction_receipt(scrub['hash'])
        if hash:
            print("all trades for the strategists assset / quote pair were cancelled!")