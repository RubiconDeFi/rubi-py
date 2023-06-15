import os
from _decimal import Decimal
from typing import Dict

import yaml
from pytest import mark
from web3 import Web3
from web3.contract import Contract

from rubi import (
    Network, Client, RubiconMarket, RubiconRouter, ERC20, NewMarketOrder, OrderSide, Transaction, NewLimitOrder,
    EmitOfferEvent, OrderEvent, OrderType, NewCancelOrder, EmitCancelEvent, EmitTakeEvent, EmitDeleteEvent, EmitFeeEvent
)


class TestNetwork:
    def test_init_from_yaml(self, test_network: Network, web3: Web3):
        path = f"{os.path.dirname(os.path.abspath(__file__))}/test_network_config"
        with open(f"{path}/test_config.yaml", 'r') as file:
            network_config = yaml.safe_load(file)

        network = Network(
            path=path,
            w3=web3,
            **network_config
        )

        assert network.name == test_network.name
        assert network.chain_id == test_network.chain_id
        assert network.rpc_url == test_network.rpc_url
        assert network.explorer_url == test_network.explorer_url
        assert network.currency == test_network.currency


class TestClient:
    def test_init(self, account_1: Dict, test_network: Network):
        client = Client(
            network=test_network,
            wallet=account_1['address'],
            key=account_1['key']
        )
        # Test client creation
        assert isinstance(client, Client)
        # Test if the wallet attribute is set correctly when a valid wallet address is provided.
        assert client.wallet == account_1["address"]
        # Test if the key attribute is set correctly when a key is provided.
        assert client.key == account_1['key']
        # Test if the market/router have correct types and are init
        assert isinstance(client.market, RubiconMarket)
        assert isinstance(client.router, RubiconRouter)
        # Test if the _pairs attribute is initialized as an empty dictionary.
        assert len(client._pairs.keys()) == 0
        # Test if the message_queue attribute is set to None when no queue is provided.
        assert client.message_queue is None

    ######################################################################
    # pair tests
    ######################################################################

    def test_add_pair(
        self, 
        test_client: Client, 
        cow: Contract, 
        eth: Contract
    ):
        pair_name = "COW/ETH"

        test_client.add_pair(pair_name=pair_name)

        assert len(test_client.get_pairs_list()) == 1
        assert test_client.get_pairs_list()[0] == pair_name

        pair = test_client.get_pair(pair_name=pair_name)
        assert pair.base_asset.address == cow.address
        assert pair.quote_asset.address == eth.address

    def test_update_pair_allowance(
        self,
        rubicon_market: Contract,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        initial_cow_allowance = cow_erc20_for_account_1.allowance(
            owner=cow_erc20_for_account_1.wallet,
            spender=rubicon_market.address
        )
        initial_eth_allowance = eth_erc20_for_account_1.allowance(
            owner=eth_erc20_for_account_1.wallet,
            spender=rubicon_market.address
        )

        # in fixtures these are initialized with the max approval value
        max_approval = 2 ** 256 - 1

        assert initial_cow_allowance == max_approval
        assert initial_eth_allowance == max_approval

        test_client_for_account_1.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=Decimal("12"),
            new_quote_asset_allowance=Decimal("100"),
        )

        new_cow_allowance = cow_erc20_for_account_1.allowance(
            owner=cow_erc20_for_account_1.wallet,
            spender=rubicon_market.address
        )
        new_eth_allowance = eth_erc20_for_account_1.allowance(
            owner=eth_erc20_for_account_1.wallet,
            spender=rubicon_market.address
        )

        assert new_cow_allowance != initial_cow_allowance
        assert new_cow_allowance == cow_erc20_for_account_1.to_integer(Decimal("12"))

        assert new_eth_allowance != initial_eth_allowance
        assert new_eth_allowance == eth_erc20_for_account_1.to_integer(Decimal("100"))

    def test_delete_pair(
        self, 
        test_client_for_account_1: Client, 
        cow: Contract, 
        eth: Contract
    ):
        pair_name = "COW/ETH"

        assert len(test_client_for_account_1.get_pairs_list()) == 1
        assert test_client_for_account_1.get_pairs_list()[0] == pair_name

        pair = test_client_for_account_1.get_pair(pair_name)
        assert pair.base_asset.address == cow.address
        assert pair.quote_asset.address == eth.address

        test_client_for_account_1.remove_pair(pair_name)

        assert len(test_client_for_account_1.get_pairs_list()) == 0

    ######################################################################
    # orderbook tests
    ######################################################################

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_get_orderbook(
        self, 
        test_client_for_account_1: Client
    ):
        pair_name = "COW/ETH"

        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        # Check that the account 2 offers are in the book
        assert len(orderbook.bids.levels) == 1
        assert len(orderbook.asks.levels) == 1

        bid = orderbook.bids.levels[0]
        ask = orderbook.asks.levels[0]

        assert bid.price == Decimal("1")
        assert bid.size == Decimal("1")
        assert ask.price == Decimal("2")
        assert ask.size == Decimal("1")

    ######################################################################
    # order tests
    ######################################################################

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_buy_market_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2")
        )

        transaction = Transaction(
            orders=[market_order]
        )

        result = test_client_for_account_1.place_market_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # Check that account 1 had paid and received assets accounting for rounding
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(cow_amount_after_order - cow_amount_before_order), 4
        ) == Decimal("1")
        # paid 2 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(eth_amount_after_order - eth_amount_before_order), 4
        ) == Decimal("-2")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert round(orderbook.asks.levels[0].size, 4) == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_market_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.SELL,
            size=Decimal("1"),
            worst_execution_price=Decimal("1")
        )

        transaction = Transaction(
            orders=[market_order]
        )

        result = test_client_for_account_1.place_market_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # Check that account 1 had paid and received assets accounting for rounding
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(cow_amount_after_order - cow_amount_before_order), 4
        ) == Decimal("-1")
        # paid 1 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(eth_amount_after_order - eth_amount_before_order), 4
        ) == Decimal("1")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)
        assert round(orderbook.bids.levels[0].size, 4) == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_buy_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # no cow should have changed hands yet
        assert cow_amount_before_order == cow_amount_after_order
        # 0.75 ETH being held in escrow for the Limit Order
        assert round(
            eth_erc20_for_account_1.to_decimal(eth_amount_after_order - eth_amount_before_order), 4
        ) == Decimal("-0.75")

        # Check that offer has been placed in the market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert orderbook.bids.levels[0].size == Decimal("0.5")
        assert orderbook.bids.levels[0].price == Decimal("1.5")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # 1 COW being held in escrow for the Limit Order
        assert round(
            cow_erc20_for_account_1.to_decimal(cow_amount_after_order - cow_amount_before_order), 4
        ) == Decimal("-0.5")
        # no ETH has changed hands yet
        assert eth_amount_after_order == eth_amount_before_order

        # Check that offer has been placed in the market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert orderbook.asks.levels[0].size == Decimal("0.5")
        assert orderbook.asks.levels[0].price == Decimal("1.5")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_buy_limit_order_that_crosses_the_spread(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # There is a SELL limit order already in the book with a size of 1 and price of 2 so this should match with that
        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            price=Decimal("1000")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # Check that account 1 had paid and received assets accounting for rounding
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(cow_amount_after_order - cow_amount_before_order), 4
        ) == Decimal("1")
        # paid 2 ETH even though we were willing to pay 1000 eth
        assert round(
            eth_erc20_for_account_1.to_decimal(eth_amount_after_order - eth_amount_before_order), 4
        ) == Decimal("-2")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert round(orderbook.asks.levels[0].size, 4) == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_limit_order_that_crosses_the_spread(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # There is a BUY limit order already in the book with a size of 1 and price of 1 so this should match with that
        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("1"),
            price=Decimal("1")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        # Check that account 1 had paid and received assets accounting for rounding
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(cow_amount_after_order - cow_amount_before_order), 4
        ) == Decimal("-1")
        # paid 1 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(eth_amount_after_order - eth_amount_before_order), 4
        ) == Decimal("1")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert round(orderbook.bids.levels[0].size, 4) == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_cancel_buy_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)
        
        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitOfferEvent)
        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Get limit order ID from message queue 
        limit_order_id = message_queue.get(block=True).limit_order_id
        
        # ID should be 3 as it's the 3rd order in the market 
        assert isinstance(limit_order_id, int)
        assert limit_order_id == 3

        # Cancel the buy limit order
        cancel_limit_order = NewCancelOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            order_id=limit_order_id
        )

        cancel_transaction = Transaction(
            orders=[cancel_limit_order]
        )

        cancel_result = test_client_for_account_1.cancel_limit_order(
            transaction=cancel_transaction
        )

        # Check that cancel txn was a success
        assert cancel_result.status == 1

        # Check balances are the same after the cancel removes funds from escrow
        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        assert cow_amount_before_order == cow_amount_after_order
        assert eth_amount_before_order == eth_amount_after_order
    
    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_cancel_sell_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitOfferEvent)
        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Get limit order ID from message queue 
        limit_order_id = message_queue.get(block=True).limit_order_id
        
        # ID should be 3 as it's the 3rd order in the market 
        assert isinstance(limit_order_id, int)
        assert limit_order_id == 3

        # Cancel the buy limit order
        cancel_limit_order = NewCancelOrder(
            pair_name=pair_name,
            order_side=OrderSide.SELL,
            order_id=limit_order_id
        )

        cancel_transaction = Transaction(
            orders=[cancel_limit_order]
        )

        cancel_result = test_client_for_account_1.cancel_limit_order(
            transaction=cancel_transaction
        )

        # Check that cancel txn was a success
        assert cancel_result.status == 1

        # Check balances are the same after the cancel removes funds from escrow
        cow_amount_after_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        assert cow_amount_before_order == cow_amount_after_order
        assert eth_amount_before_order == eth_amount_after_order
    
    ######################################################################
    # batch order tests
    ######################################################################
    
    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    #currently broke
    def test_batch_place_limit_orders(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(cow_erc20_for_account_1.wallet)
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(eth_erc20_for_account_1.wallet)

        print(cow_amount_before_order)
        print(eth_amount_before_order)

        limit_order_1 = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.05"),
            price=Decimal("1000")
        )

        limit_order_2 = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.05"),
            price=Decimal("1000")
        )


        batchtxn = Transaction(
            orders=[limit_order_1,limit_order_2]
        )

        result = test_client_for_account_1.batch_place_limit_orders(
            transaction=batchtxn
        )

        # Check that transaction was a success
        assert result.status == 1

        # Check that offers has been placed in the market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert orderbook.bids.levels[0].size == Decimal("0.5")
        assert orderbook.bids.levels[0].price == Decimal("1.5")
    
    
    ######################################################################
    # event poller tests
    ######################################################################

    def test_emit_offer_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitOfferEvent)

        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Get message from message queue put there by event poller
        message = message_queue.get(block=True)

        # Check that this message is for the limit order we placed
        assert isinstance(message, OrderEvent)
        assert message.order_type == OrderType.LIMIT
        assert message.order_side == OrderSide.BUY
        assert message.size == Decimal("0.5")
        assert message.price == Decimal("1.5")
        assert message.pair_name == pair_name

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_emit_take_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitTakeEvent)

        message_queue = test_client_for_account_1.message_queue

        # Create a market order that fills the fixture ordre
        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2")
        )

        transaction = Transaction(
            orders=[market_order]
        )

        result = test_client_for_account_1.place_market_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Get message from message queue put there by event poller
        message = message_queue.get(block=True)

        # Check that the message is for the filled market order
        assert isinstance(message, OrderEvent)
        assert message.order_type == OrderType.MARKET
        assert message.order_side == OrderSide.BUY
        assert message.price == Decimal("2")
        assert round(message.size, 4) == Decimal("1")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_emit_cancel_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"
        
        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitOfferEvent)
        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5")
        )

        transaction = Transaction(
            orders=[limit_order]
        )

        result = test_client_for_account_1.place_limit_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Get limit order ID from message queue 
        limit_order_id = message_queue.get(block=True).limit_order_id
        
        # ID should be 3 as it's the 3rd order in the market 
        assert isinstance(limit_order_id, int)
        assert limit_order_id == 3

        # Start cancel order polling
        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitCancelEvent)

        # Cancel the buy limit order
        cancel_limit_order = NewCancelOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            order_id=limit_order_id
        )

        cancel_transaction = Transaction(
            orders=[cancel_limit_order]
        )

        cancel_result = test_client_for_account_1.cancel_limit_order(
            transaction=cancel_transaction
        )

        # Check that cancel txn was a success
        assert cancel_result.status == 1

        # Get message from message queue put there by event poller
        message = message_queue.get(block=True)
        
        # Check that the message is a cancel event
        assert isinstance(message, OrderEvent)
        assert message.order_type == OrderType.CANCEL
        assert message.order_side == OrderSide.BUY
        assert message.price == Decimal("1.5")
        assert round(message.size, 4) == Decimal("0.5")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    # broken - hits an error because the order is not completely removed (rounding)
    def test_emit_delete_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(pair_name=pair_name, event_type=EmitDeleteEvent)
        message_queue = test_client_for_account_1.message_queue

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2")
        )

        transaction = Transaction(
            orders=[market_order]
        )

        result = test_client_for_account_1.place_market_order(
            transaction=transaction
        )

        # Check that transaction was a success
        assert result.status == 1

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)
        print(orderbook)

        # Get message from message queue put there by event poller (Delete event)
        message = message_queue.get(block=True)
        print(message)

        # # Check that the message is for the filled market order
        # assert isinstance(message, OrderEvent)
        # assert message.order_type == OrderType.MARKET
        # assert message.order_side == OrderSide.BUY
        # assert message.price == Decimal("2")
        # assert round(message.size, 4) == Decimal("1")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    #broken hits an error for fee
    def test_emit_fee_event_poller(self, test_client_for_account_1: Client):
        assert 1 == 0

    