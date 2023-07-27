Quickstart
==========

.. contents::
   :depth: 2
   :local:

.. _installation:

Installation
------------

To use the rubi sdk, first install it using ``pip`` or ``poetry``:

.. code-block:: console

   (.venv) $ pip install rubi

.. code-block:: console

   (.venv) $ poetry add rubi

Using rubi
----------

This quickstart guide aims highlight the most common use case of rubi, connecting to and trading on the Rubicon Protocol.

This sdk depends on a connection to an Ethereum node by relying on the `web3.py <https://github.com/ethereum/web3.py>`_
library. Please refer to their `documentation <https://web3py.readthedocs.io/en/latest/index.html>`_ if you want to
understand what is going on behind the scenes.

rubi client
^^^^^^^^^^^

The main entrypoint of this library is the :ref:`rubi client <client>`. In order to instantiate a client we will need to
provide it with some environment variables, namely a ``HTTP_NODE_URL``, ``WALLET`` and ``KEY``. While not strictly
necessary it is best practice to provide this from a ``.env`` file.

.. note:: If you are working in a git repository make sure you add a ``.gitignore`` and ignore ``.env`` files to ensure you never commit sensitive information.

Create a ``.env`` file with the following format:

.. code-block:: text

    HTTP_NODE_URL = <an optimism http node url>
    WALLET = <the wallet that is being used to sign transactions and pay gas for said transactions>
    KEY = <the private key of the wallet being used to sign transactions>

.. note:: The easiest way to connect to a node is to use a node provider like `alchemy <https://www.alchemy.com/>`_ or `infura <https://www.infura.io/>`_.

Following this you will need to read in these environment variables. The easiest way to do this is using the python
``dotenv`` library.

.. code-block:: console

   (.venv) $ pip install python-dotenv

.. code-block:: console

   (.venv) $ poetry add python-dotenv

This will allow you to read in your environment variables as follows:

.. code-block:: python

    import logging as log
    import os

    from dotenv import load_dotenv

    # load from env file
    load_dotenv(".env")

    # set the env variables
    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("WALLET")
    key = os.getenv("KEY")

Finally we are ready to instantiate a client

.. code-block:: python

    # rubi imports
    from rubi import Client, NetworkName, Transaction, NewLimitOrder, OrderSide

    # instantiate the client
    client = Client.from_http_node_url(
        http_node_url=http_node_url,
        wallet=wallet,
        key=key
    )

.. note:: In the above example we are creating a client using the ``from_http_node_url`` function. This fetches the chain id from the node and then maps this to default network config that is managed by the Rubicon team. This config can be seen `here <https://github.com/RubiconDeFi/rubi-py/tree/master/rubi/network_config>`_. If you prefer you can instantiate your own ``Network`` instance and use that to instantiate the client.

.. note:: In the above example we are connecting to the optimism goerli testnet. Make sure the node you are using is an optimism goerli node.

Having instantiated a client you are now ready to start interacting with the Rubicon protocol. In order to use the
client to read or trade against a specific pair you will need to first add the pair to the client.

.. code-block:: python

    # add the WETH/USDC pair to the client
    # the base asset is WETH and the quote asset is USDC
    client.add_pair(
        pair_name="WETH/USDC",
        base_asset_allowance=Decimal("1"),
        quote_asset_allowance=Decimal("10000")
    )

.. note:: The allowances in the code above approve the ``RubiconMarket`` contract to transact up to that amount on your wallets behalf. This is necessary in order to create offers on the protocol.

Now with a pair created you can place your first limit order on Rubicon the decentralized world orderbook!

.. code-block:: python

    limit_order = NewLimitOrder(
        pair_name="WETH/USDC",
        order_side=OrderSide.BUY,
        size=Decimal("1"),
        price=Decimal("1914.13")
    )

    client.place_limit_order(
        transaction=Transaction(
            orders=[limit_order]
        )
    )

That brings us to the end of the quickstart. Next see the :doc:`overview` of the client's current functionality.

READ ONLY rubi client
^^^^^^^^^^^^^^^^^^^^^^

To create a read only :ref:`rubi client <client>` follow the steps above except when creating your ``.env`` file DO NOT
add a ``WALLET`` or ``KEY``. Instead your ``.env`` file should only contain the following

.. code-block:: text

    HTTP_NODE_URL = <an optimism http node url>

The :ref:`rubi client <client>` will then be instantiated without signing rights. You will still have read access to all
the Rubicon contracts.

That brings us to the end of the quickstart. Next see the :doc:`overview` of the client's current functionality.

rubi client pairs and tokens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :ref:`rubi client <client>` uses the notion of a ``pair`` to effectively translate from offers on the Rubicon
protocol to the more understandable notions of bids and asks.


Whenever you want to trade a specific set of tokens you will first need to add this pair to the client

.. code-block:: python

    # add the WETH/USDC pair to the client
    # the base asset is WETH and the quote asset is USDC
    client.add_pair(
        pair_name="WETH/USDC",
        base_asset_allowance=Decimal("1"),
        quote_asset_allowance=Decimal("10000")
    )

If you add the ``WETH/USDC`` pair as in the above example then you are saying you want to think of trading ``WETH`` in
terms of ``USDC``. In other words, all orders and the client orderbook will price ``WETH`` in terms of ``USDC``, so for
example, if you wanted to create a new limit order you would say I want to sell ``1 WETH`` for ``2000 USDC``. It should
be noted that there is no need to price assets in stable coin terms. In fact, being in defi it probably makes more sense
to price things in terms of ``WETH`` ;).

.. code-block:: python

    client.add_pair(
        pair_name="USDC/WETH",
        base_asset_allowance=Decimal("1"),
        quote_asset_allowance=Decimal("10000")
    )

By default when you instantiate a :ref:`rubi client <client>` you will only be able to create pairs from the tokens
found in the ``token_addresses`` section of the ``network.yaml`` config for the chain you are connected to. This set of
token addresses is vetted by the Rubicon team and intended to ensure that in interacting with the protocol users do not
fall victim to scam coins. However, when instantiating the client you can provide an additional
``custom_token_addresses_file`` parameter

.. code-block:: python

    client = Client.from_http_node_url(
        http_node_url=http_node_url,
        custom_token_addresses_file="custom_token_addresses.yaml",
        wallet=wallet,
        key=key
    )


This points to a yaml file (which is relative to the current working directory) containing token addresses in the
following format

.. code-block:: yaml

    # Forrest coin and USDT on Optimism Goerli
    F: 0x45fa7d7b6c954d17141586e1bd63d2e35d3e26de
    USDT:  0xd70734ba8101ec28b38ab15e30dc9b60e3c6f433

These additional tokens will then be appended to the valid tokens found in the ``network.yaml``.

Additionally, it should be noted that you can override the addresses found in ``token_addresses`` section of the
``network.yaml`` by adding the same key to the ``custom_token_addresses_file``.

.. warning:: THIS IS SUPER RISKY. I HOPE YOU KNOW WHAT YOU'RE DOING IF YOU CHOOSE TO DO THIS.

.. code-block:: yaml

    USDC: 0xFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfake

This will result in the client being instantiated with the address of
``USDC`` as ``0xFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfake``.

rubi data methods
-----------------

In this section, we will go through some methods in the ``Client`` and ``MarketData`` classes of the Rubicon package, specifically the ``get_offers`` and ``get_trades`` methods. We'll also illustrate how to use these methods with a basic example at the end.

The `get_offers` Method
^^^^^^^^^^^^^^^^^^^^^^^

This method is used to retrieve offers placed on the market contract. Users can filter the offers based on various parameters including the maker's address, transaction origin address, tokens involved in the transaction, etc.

Here's the signature of the method:

.. code-block:: python

    def get_offers(
        self,
        first: int = 10000000,
        order_by: str = "timestamp",
        order_direction: str = "desc",
        formatted: bool = True,
        book_side: OrderSide = OrderSide.NEUTRAL,
        maker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        pair_name: Optional[str] = None,
        pay_gem: Optional[Union[ChecksumAddress, str]] = None,
        buy_gem: Optional[Union[ChecksumAddress, str]] = None,
        open: Optional[bool] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:

The method accepts the following parameters:

.. list-table:: 
   :header-rows: 1

   * - Parameter
     - Description
   * - `first`
     - Number of offers to return
   * - `order_by`
     - Field to order the offers by. Default is "timestamp"
   * - `order_direction`
     - Direction to order the offers by. Default is "desc"
   * - `formatted`
     - Whether or not to return the dataframe with formatted fields (requires node connection)
   * - `book_side`
     - Specifies which side of the order book to consider
   * - `maker`
     - The address of the maker of the offer
   * - `from_address`
     - The address that originated the transaction that created the offer
   * - `pair_name`
     - Token pair in the format "WETH/USDC" following the pattern <ASSET/QUOTE>
   * - `pay_gem`
     - The address of the token that the maker is offering. Optional, overrides the `pair_name` if provided
   * - `buy_gem`
     - The address of the token that the maker is requesting. Optional, overrides the `pair_name` if provided
   * - `open`
     - Whether or not the offer is still active
   * - `start_time`
     - The unix timestamp of the earliest offer to return
   * - `end_time`
     - The unix timestamp of the latest offer to return

The `get_trades` Method
^^^^^^^^^^^^^^^^^^^^^^^

This method is used to retrieve trades that have occurred on the market contract. Similar to `get_offers`, users can filter the trades based on various parameters including the taker's address, transaction origin address, tokens involved in the transaction, etc.

Here's the signature of the method:

.. code-block:: python

    def get_trades(
        self,
        first: int = 10000000,
        order_by: str = "timestamp",
        order_direction: str = "desc",
        formatted: bool = True,
        book_side: OrderSide = OrderSide.NEUTRAL,
        taker: Optional[Union[ChecksumAddress, str]] = None,
        from_address: Optional[Union[ChecksumAddress, str]] = None,
        pair_name: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> pd.DataFrame:

The method accepts the following parameters:

.. list-table:: 
   :header-rows: 1

   * - Parameter
     - Description
   * - `first`
     - Number of trades to return
   * - `order_by`
     - Field to order the trades by. Default is "timestamp"
   * - `order_direction`
     - Direction to order the trades by. Default is "desc"
   * - `formatted`
     - Whether or not to return the dataframe with formatted fields (requires node connection)
   * - `book_side`
     - Specifies which side of the order book to consider
   * - `taker`
     - The address of the taker of the trade
   * - `from_address`
     - The address that originated the transaction that created the trade (helpful when transactions go through the router)
   * - `pair_name`
     - Token pair in the format "WETH/USDC" following the pattern <ASSET/QUOTE>
   * - `start_time`
     - The unix timestamp of the earliest trade to return
   * - `end_time`
     - The unix timestamp of the latest trade to return

Retrieving Offer Data
^^^^^^^^^^^^^^^^^^^^^

In the example below, we will retrieve WETH/USDC offer data for a given time range on the network of the node connection.

.. code-block:: python

    weth_usdc_offers = client.get_offers(
        pair_name="WETH/USDC",
        book_side=OrderSide.NEUTRAL, # options are NEUTRAL, BUY, SELL
        formatted=True, # by default is set to True, if set to False, raw data will be returned (with greater detail)
        start_time=1688187600,
        end_time=1690606800,
    )

Retrieving Trade Data
^^^^^^^^^^^^^^^^^^^^^

In the example below, we will access WETH/USDC trade data for a given time range on the network of the node connection.

.. code-block:: python

    weth_usdc_trades = client.get_trades(
        pair_name="WETH/USDC",
        book_side=OrderSide.NEUTRAL, # options are NEUTRAL, BUY, SELL
        formatted=True, # by default is set to True, if set to False, raw data will be returned (with greater detail)
        start_time=1688187600,
        end_time=1690606800,
    )
