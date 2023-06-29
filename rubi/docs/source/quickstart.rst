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
