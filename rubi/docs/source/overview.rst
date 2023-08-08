Overview
========

.. contents::
   :depth: 2
   :local:

The main entrypoint of the **rubi** sdk is the :ref:`client <client>` which aims to serve as the unified api for
the rubi sdk.

The client
----------

The underlying goal of the design of the :ref:`client <client>` is to provide developers with a seamless integration
experience when interacting with the Rubicon. The sdk is built with the goal of enabling efficient and reliable
communication with Rubicon's smart contracts, empowering developers to effortlessly access and utilize Rubicon's
features in their Python applications.

All of the methods on the client can be seen :ref:`here <client>`. Fundamentally, these methods aim to abstract away the
complexity of interacting with the protocol directly. For example you can use the client to place ``bid limit orders``.

.. code-block:: python

    limit_order = NewLimitOrder(
        pair_name="WETH/USDC",
        order_side=OrderSide.BUY,
        size=Decimal("1"),
        price=Decimal("1914.13")
    )

    client.place_limit_order(limit_order=limit_order)

However the :ref:`client <client>` also enables access to the underlying smart contracts that power the Rubicon
protocol.

Rubicon contracts
-----------------

The :ref:`client <client>` currently exposes the :ref:`RubiconMarket <RubiconMarket>` and
:ref:`RubiconRouter <RubiconRouter>` contracts.

From an instantiated :ref:`client <client>` any methods on these contracts can easily be called using the contract
objects on the :ref:`client <client>`.


.. code-block:: python

    client.network.market  # RubiconMarket
    client.network.router  # RubiconRouter

.. _RubiconMarket:

RubiconMarket contract
^^^^^^^^^^^^^^^^^^^^^^

**RubiconMarket** implements order books and a matching engine for peer-to-peer trading of ERC-20 tokens.

The contract uses an escrow model for liquidity; when ``offer()`` is called, tokens are sent to the contract. If/when an
order is filled, the contract matches the traders directly and the tokens are sent to each party. When ``cancel()`` is
called, the contract removes the target ``offer()`` and returns the tokens to the owner.

An overview of the contract can be found `here <https://docs.rubicon.finance/protocol/rubicon-market/contract-overview>`__.

Additionally, details of the python implementation can be seen in the :ref:`contracts module <rubi_contracts>`.

.. _RubiconRouter:

RubiconRouter contract
^^^^^^^^^^^^^^^^^^^^^^

**RubiconRouter** is a high-level contract that adds convenient functionality for interacting with low-level Rubicon
smart contracts.

It primarily serves as a router for ERC-20/ERC-20 token swaps on the RubiconMarket contract, and enables multi-hop swaps
if two tokens do not have an underlying order book.

An overview of the contract can be found `here <https://docs.rubicon.finance/protocol/rubicon-router/rubicon-router>`__.

Additionally, details of the python implementation can be seen in the :ref:`contracts module <rubi_contracts>`.