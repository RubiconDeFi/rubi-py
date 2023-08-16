import os
from _decimal import Decimal
from typing import Dict

import yaml
from pytest import mark
from web3 import Web3
from web3.contract import Contract

from contracts.contract_types.transaction_reciept import TransactionStatus
from rubi import (
    Network,
    Client,
    RubiconMarket,
    RubiconRouter,
    ERC20,
    NewMarketOrder,
    OrderSide,
    Transaction,
    NewLimitOrder,
    EmitOfferEvent,
    OrderEvent,
    OrderType,
    NewCancelOrder,
    EmitCancelEvent,
    EmitTakeEvent,
    EmitDeleteEvent,
    EmitFeeEvent,
    OrderBook,
    FeeEvent,
    UpdateLimitOrder,
)


class TestNetwork:
    def test_init_from_yaml(self, test_network_1: Network, web3: Web3):
        path = f"{os.path.dirname(os.path.abspath(__file__))}/test_network_config"
        with open(f"{path}/test_config.yaml", "r") as file:
            network_config = yaml.safe_load(file)

        network = Network(w3=web3, **network_config)

        assert network.name == test_network_1.name
        assert network.chain_id == test_network_1.chain_id
        assert network.rpc_url == test_network_1.rpc_url
        assert network.explorer_url == test_network_1.explorer_url
        assert network.currency == test_network_1.currency

        # contracts
        assert network.rubicon_market.address == network_config["rubicon"]["market"]
        assert network.rubicon_router.address == network_config["rubicon"]["router"]

        # tokens
        assert network.tokens["COW"].symbol == "COW"
        assert network.tokens["COW"].decimals == 18

        assert network.tokens["ETH"].symbol == "ETH"
        assert network.tokens["ETH"].decimals == 18

        assert network.tokens["BLZ"].symbol == "BLZ"
        assert network.tokens["BLZ"].decimals == 18


class TestClient:
    def test_init(self, account_1: Dict, test_network_1: Network):
        client = Client(
            network=test_network_1, wallet=account_1["address"], key=account_1["key"]
        )
        # Test client creation
        assert isinstance(client, Client)
        # Test if the wallet attribute is set correctly when a valid wallet address is provided.
        assert client.wallet == account_1["address"]
        # Test if the key attribute is set correctly when a key is provided.
        assert client.key == account_1["key"]
        # Test if the market/router have correct types and are init
        assert isinstance(client.market, RubiconMarket)
        assert isinstance(client.router, RubiconRouter)
        # Test if the _pairs attribute is initialized as an empty dictionary.
        assert len(client._pairs.keys()) == 0
        # Test if the message_queue attribute is set to None when no queue is provided.
        assert client.message_queue is None

    def test_fail_to_instantiate_different_clients(
        self, test_network_1: Network, account_1: Dict, account_2: Dict
    ):
        client_1 = Client(
            network=test_network_1, wallet=account_1["address"], key=account_1["key"]
        )

        try:
            client_2 = Client(
                network=test_network_1,
                wallet=account_2["address"],
                key=account_2["key"],
            )
        except Exception as e:
            assert (
                e.args[0]
                == "Network has already been configured to use another wallet."
            )

    ######################################################################
    # pair tests
    ######################################################################

    def test_add_pair(self, test_client: Client, cow: Contract, eth: Contract):
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
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        initial_cow_allowance = cow_erc20_for_account_1.allowance(
            owner=cow_erc20_for_account_1.wallet, spender=rubicon_market.address
        )
        initial_eth_allowance = eth_erc20_for_account_1.allowance(
            owner=eth_erc20_for_account_1.wallet, spender=rubicon_market.address
        )

        # in fixtures these are initialized with the max approval value
        max_approval = 2**256 - 1

        assert initial_cow_allowance == max_approval
        assert initial_eth_allowance == max_approval

        test_client_for_account_1.update_pair_allowance(
            pair_name=pair_name,
            new_base_asset_allowance=Decimal("12"),
            new_quote_asset_allowance=Decimal("100"),
        )

        new_cow_allowance = cow_erc20_for_account_1.allowance(
            owner=cow_erc20_for_account_1.wallet, spender=rubicon_market.address
        )
        new_eth_allowance = eth_erc20_for_account_1.allowance(
            owner=eth_erc20_for_account_1.wallet, spender=rubicon_market.address
        )

        assert new_cow_allowance != initial_cow_allowance
        assert new_cow_allowance == cow_erc20_for_account_1.to_integer(Decimal("12"))

        assert new_eth_allowance != initial_eth_allowance
        assert new_eth_allowance == eth_erc20_for_account_1.to_integer(Decimal("100"))

    def test_delete_pair(
        self, test_client_for_account_1: Client, cow: Contract, eth: Contract
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
    def test_get_orderbook(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        # Check that the account 2 offers are in the book
        assert len(orderbook.bids.levels) == 1
        assert len(orderbook.asks.levels) == 2

        bid = orderbook.bids.levels[0]
        ask = orderbook.asks.levels[0]

        assert bid.price == Decimal("1")
        assert bid.size == Decimal("1")
        assert ask.price == Decimal("2")
        assert ask.size == Decimal("1")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_orderbook_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_orderbook_poller(pair_name=pair_name)

        message_queue = test_client_for_account_1.message_queue

        message = message_queue.get(block=True)

        # Check that the account 2 offers are in the book
        assert isinstance(message, OrderBook)
        assert len(message.bids.levels) == 1
        assert len(message.asks.levels) == 2

        bid = message.bids.levels[0]
        ask = message.asks.levels[0]

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
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_1.place_market_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == market_order.pair_name
        assert event.order_side == market_order.order_side
        assert event.order_type == OrderType.MARKET
        assert event.size == market_order.size
        assert event.price == Decimal("2")
        assert event.market_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # Check that account 1 had paid and received assets accounting for fees
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(
                cow_amount_after_order - cow_amount_before_order
            ),
            3,
        ) == Decimal("1")
        # paid 2 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(
                eth_amount_after_order - eth_amount_before_order
            ),
            3,
        ) == Decimal("-2")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        # There were 2 asks prior to the market order in the fixture
        assert len(orderbook.asks.levels) == 1
        assert orderbook.asks.levels[0].price == Decimal("3")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_market_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.SELL,
            size=Decimal("1"),
            worst_execution_price=Decimal("1"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_1.place_market_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == market_order.pair_name
        assert event.order_side == market_order.order_side
        assert event.order_type == OrderType.MARKET
        assert event.size == market_order.size
        assert event.price == Decimal("1")
        assert event.market_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # Check that account 1 had paid and received assets accounting for fees
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(
                cow_amount_after_order - cow_amount_before_order
            ),
            3,
        ) == Decimal("-1")
        # paid 1 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(
                eth_amount_after_order - eth_amount_before_order
            ),
            3,
        ) == Decimal("1")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert len(orderbook.bids.levels) == 0

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_buy_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == limit_order.pair_name
        assert event.order_side == limit_order.order_side
        assert event.order_type == OrderType.LIMIT
        assert event.size == limit_order.size
        assert event.price == limit_order.price
        assert event.limit_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # no cow should have changed hands yet
        assert cow_amount_before_order == cow_amount_after_order
        # 0.75 ETH being held in escrow for the Limit Order
        assert round(
            eth_erc20_for_account_1.to_decimal(
                eth_amount_after_order - eth_amount_before_order
            ),
            4,
        ) == Decimal("-0.75")

        # Check that offer has been placed in the market and that the client is tracking the limit order
        assert len(test_client_for_account_1.active_limit_orders) == 1

        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)
        active_limit_order = list(
            test_client_for_account_1.active_limit_orders.values()
        )[0]

        assert (
            orderbook.bids.levels[0].size == active_limit_order.size == Decimal("0.5")
        )
        assert (
            orderbook.bids.levels[0].price == active_limit_order.price == Decimal("1.5")
        )
        assert active_limit_order.filled_size == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_limit_order(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("0.5"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == limit_order.pair_name
        assert event.order_side == limit_order.order_side
        assert event.order_type == OrderType.LIMIT
        assert event.size == limit_order.size
        assert event.price == limit_order.price
        assert event.limit_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # 0.5 COW being held in escrow for the Limit Order
        assert round(
            cow_erc20_for_account_1.to_decimal(
                cow_amount_after_order - cow_amount_before_order
            ),
            4,
        ) == Decimal("-0.5")
        # no ETH has changed hands yet
        assert eth_amount_after_order == eth_amount_before_order

        # Check that offer has been placed in the market and that the client is tracking the limit order
        assert len(test_client_for_account_1.active_limit_orders) == 1

        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)
        active_limit_order = list(
            test_client_for_account_1.active_limit_orders.values()
        )[0]

        assert (
            orderbook.asks.levels[0].size == active_limit_order.size == Decimal("0.5")
        )
        assert (
            orderbook.asks.levels[0].price == active_limit_order.price == Decimal("1.5")
        )
        assert active_limit_order.filled_size == Decimal("0")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_buy_limit_order_that_crosses_the_spread(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # There is a SELL limit order already in the book with a size of 1 and price of 2 so this should match with that
        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            price=Decimal("1000"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == limit_order.pair_name
        assert event.order_side == limit_order.order_side
        assert event.order_type == OrderType.MARKET
        assert event.size == limit_order.size
        assert event.price == Decimal("2")
        assert event.market_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # Check that account 1 had paid and received assets accounting for fees
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(
                cow_amount_after_order - cow_amount_before_order
            ),
            3,
        ) == Decimal("1")
        # paid 2 ETH even though we were willing to pay 1000 eth
        assert round(
            eth_erc20_for_account_1.to_decimal(
                eth_amount_after_order - eth_amount_before_order
            ),
            3,
        ) == Decimal("-2")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        # There were 2 asks prior to the market order in the fixture
        assert len(orderbook.asks.levels) == 1
        assert orderbook.asks.levels[0].price == Decimal("3")

        # Check that the limit order is not being tracked
        assert len(test_client_for_account_1.active_limit_orders) == 0

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_place_sell_limit_order_that_crosses_the_spread(
        self,
        test_client_for_account_1: Client,
        cow_erc20_for_account_1: ERC20,
        eth_erc20_for_account_1: ERC20,
    ):
        pair_name = "COW/ETH"

        cow_amount_before_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_before_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # There is a BUY limit order already in the book with a size of 1 and price of 1 so this should match with that
        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("1"),
            price=Decimal("1"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 1

        event: OrderEvent = result.events[0]

        assert event.pair_name == limit_order.pair_name
        assert event.order_side == limit_order.order_side
        assert event.order_type == OrderType.MARKET
        assert event.size == limit_order.size
        assert event.price == Decimal("1")
        assert event.market_order_owner == test_client_for_account_1.wallet

        cow_amount_after_order = cow_erc20_for_account_1.balance_of(
            cow_erc20_for_account_1.wallet
        )
        eth_amount_after_order = eth_erc20_for_account_1.balance_of(
            eth_erc20_for_account_1.wallet
        )

        # Check that account 1 had paid and received assets accounting for fees
        # received 1 COW
        assert round(
            cow_erc20_for_account_1.to_decimal(
                cow_amount_after_order - cow_amount_before_order
            ),
            3,
        ) == Decimal("-1")
        # paid 1 ETH
        assert round(
            eth_erc20_for_account_1.to_decimal(
                eth_amount_after_order - eth_amount_before_order
            ),
            3,
        ) == Decimal("1")

        # Check that offer is effectively no longer in rubicon market
        orderbook = test_client_for_account_1.get_orderbook(pair_name=pair_name)

        assert len(orderbook.bids.levels) == 0

        # Check that the limit order is not being tracked
        assert len(test_client_for_account_1.active_limit_orders) == 0

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_cancel_limit_order(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitOfferEvent
        )
        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1

        # Get limit order ID from message queue
        limit_order_id = message_queue.get(block=True).limit_order_id

        # ID should be 4 as it's the 4th order in the market
        assert isinstance(limit_order_id, int)
        assert limit_order_id == 4

        orderbook_before_cancel = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )
        active_limit_order = test_client_for_account_1.active_limit_orders[4]

        # Check that the order is in the orderbook
        assert len(orderbook_before_cancel.bids.levels) == 2
        assert (
            orderbook_before_cancel.bids.levels[0].price
            == active_limit_order.price
            == Decimal("1.5")
        )
        assert (
            orderbook_before_cancel.bids.levels[0].size
            == active_limit_order.size
            == Decimal("1")
        )

        # Cancel the limit order
        cancel_limit_order = NewCancelOrder(
            pair_name=pair_name, order_id=limit_order_id
        )

        cancel_transaction = Transaction(orders=[cancel_limit_order])

        cancel_result = test_client_for_account_1.cancel_limit_order(
            transaction=cancel_transaction
        )

        # Check that cancel txn was a success
        assert cancel_result.status == 1
        assert cancel_result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(cancel_result.events) == 1

        event: OrderEvent = cancel_result.events[0]

        assert event.pair_name == cancel_limit_order.pair_name
        assert event.order_type == OrderType.CANCEL
        assert event.order_side == limit_order.order_side
        assert event.price == limit_order.price
        assert event.size == limit_order.size
        assert event.limit_order_owner == test_client_for_account_1.wallet

        orderbook_after_cancel = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )

        # Check that the order is no longer in the orderbook
        assert len(orderbook_after_cancel.bids.levels) == 1
        assert orderbook_after_cancel.bids.levels[0].price != Decimal("1.5")

        assert len(test_client_for_account_1.active_limit_orders) == 0

    ######################################################################
    # batch order tests
    ######################################################################

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_batch_place_limit_orders(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        orderbook_before_transaction = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )

        limit_order_1 = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            price=Decimal("1.5"),
        )

        limit_order_2 = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            price=Decimal("0.5"),
        )

        batch_transaction = Transaction(orders=[limit_order_1, limit_order_2])

        result = test_client_for_account_1.batch_place_limit_orders(
            transaction=batch_transaction
        )

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 2

        for i, limit_order in enumerate([limit_order_1, limit_order_2]):
            event: OrderEvent = result.events[i]

            assert event.pair_name == limit_order.pair_name
            assert event.order_type == OrderType.LIMIT
            assert event.order_side == limit_order.order_side
            assert event.price == limit_order.price
            assert event.size == limit_order.size
            assert event.limit_order_owner == test_client_for_account_1.wallet

        # Check that offers has been placed in the market
        orderbook_after_transaction = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )

        assert (
            len(orderbook_after_transaction.bids.levels)
            == len(orderbook_before_transaction.bids.levels) + 2
        )

        assert orderbook_after_transaction.bids.levels[0].price == Decimal("1.5")
        assert orderbook_after_transaction.bids.levels[0].size == Decimal("1")

        # Check that the limit orders are being tracked
        assert len(test_client_for_account_1.active_limit_orders) == 2

        assert test_client_for_account_1.active_limit_orders[4].price == Decimal("1.5")
        assert test_client_for_account_1.active_limit_orders[5].price == Decimal("0.5")

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_batch_update_limit_orders(self, test_client_for_account_2: Client):
        pair_name = "COW/ETH"

        orderbook_before_update = test_client_for_account_2.get_orderbook(
            pair_name=pair_name
        )

        limit_order_1 = UpdateLimitOrder(
            order_id=2,
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("2"),
            price=Decimal("1.5"),
        )

        limit_order_2 = UpdateLimitOrder(
            order_id=3,
            pair_name="COW/ETH",
            order_side=OrderSide.SELL,
            size=Decimal("2"),
            price=Decimal("2.5"),
        )

        batch_transaction = Transaction(orders=[limit_order_1, limit_order_2])

        result = test_client_for_account_2.batch_update_limit_orders(
            transaction=batch_transaction
        )

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 4

        for i, limit_order in enumerate([limit_order_1, limit_order_2]):
            event: OrderEvent = result.events[i]

            assert event.pair_name == limit_order.pair_name
            assert event.order_type == OrderType.LIMIT
            assert event.order_side == limit_order.order_side
            assert event.price == limit_order.price
            assert event.size == limit_order.size
            assert event.limit_order_owner == test_client_for_account_2.wallet

        for i in range(2, 4):
            event: OrderEvent = result.events[i]

            assert event.pair_name == limit_order_1.pair_name
            assert event.order_type == OrderType.CANCEL
            assert event.limit_order_owner == test_client_for_account_2.wallet

        # Check that offers has been placed in the market
        orderbook_after_update = test_client_for_account_2.get_orderbook(
            pair_name=pair_name
        )

        assert len(orderbook_after_update.asks.levels) == len(
            orderbook_before_update.asks.levels
        )

        assert orderbook_after_update.asks.levels[0].price == Decimal("1.5")
        assert orderbook_after_update.asks.levels[0].size == Decimal("2")

        assert orderbook_after_update.asks.levels[1].price == Decimal("2.5")
        assert orderbook_after_update.asks.levels[1].size == Decimal("2")

        # Check that the new limit orders are being tracked

        assert test_client_for_account_2.active_limit_orders.get(4)
        assert test_client_for_account_2.active_limit_orders.get(5)

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_batch_cancel_limit_orders(self, test_client_for_account_2: Client):
        pair_name = "COW/ETH"

        orderbook_before_transaction = test_client_for_account_2.get_orderbook(
            pair_name=pair_name
        )

        cancel_order_1 = NewCancelOrder(pair_name="COW/ETH", order_id=2)

        cancel_order_2 = NewCancelOrder(pair_name="COW/ETH", order_id=3)

        batch_transaction = Transaction(orders=[cancel_order_1, cancel_order_2])

        result = test_client_for_account_2.batch_cancel_limit_orders(
            transaction=batch_transaction
        )

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that we received the event we expected
        assert len(result.events) == 2

        for i, cancel_order in enumerate([cancel_order_1, cancel_order_2]):
            event: OrderEvent = result.events[i]

            assert event.pair_name == cancel_order.pair_name
            assert event.order_type == OrderType.CANCEL
            assert event.limit_order_owner == test_client_for_account_2.wallet

        # Check that offers has been placed in the market
        orderbook_after_transaction = test_client_for_account_2.get_orderbook(
            pair_name=pair_name
        )

        assert (
            len(orderbook_after_transaction.asks.levels)
            == len(orderbook_before_transaction.asks.levels) - 2
        )

        assert len(test_client_for_account_2.active_limit_orders) == 0

    ######################################################################
    # event poller tests
    ######################################################################

    def test_emit_offer_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitOfferEvent
        )

        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

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

        assert len(test_client_for_account_1.active_limit_orders) == 1

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_emit_take_event_poller(self, test_client_for_account_1: Client):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitTakeEvent
        )

        message_queue = test_client_for_account_1.message_queue

        # Create a market order that fills the fixture order
        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_1.place_market_order(transaction=transaction)

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

        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitOfferEvent
        )
        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("0.5"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1

        # Get limit order ID from message queue
        limit_order_id = message_queue.get(block=True).limit_order_id

        # ID should be 4 as it's the 4th order in the market
        assert isinstance(limit_order_id, int)
        assert limit_order_id == 4

        # Start cancel order polling
        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitCancelEvent
        )

        # Cancel the buy limit order
        cancel_limit_order = NewCancelOrder(
            pair_name=pair_name, order_id=limit_order_id
        )

        cancel_transaction = Transaction(orders=[cancel_limit_order])

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
    def test_emit_delete_event_poller(
        self, test_client_for_account_1: Client, test_client_for_account_2: Client
    ):
        pair_name = "COW/ETH"

        test_client_for_account_2.start_event_poller(
            pair_name=pair_name, event_type=EmitDeleteEvent
        )

        message_queue = test_client_for_account_2.message_queue

        # Confirm there are two asks in the market
        orderbook_before_order = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )

        assert len(orderbook_before_order.asks.levels) == 2

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1.5"),
            worst_execution_price=Decimal("4"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_1.place_market_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1

        # Check that 1 ask was filled and the other is partially remaining
        orderbook_after_order = test_client_for_account_1.get_orderbook(
            pair_name=pair_name
        )

        assert len(orderbook_after_order.asks.levels) == 1

        # Get message from message queue put there by event poller (Delete event)
        message = message_queue.get(block=True)

        # Check that the message is for the deleted limit order
        assert isinstance(message, OrderEvent)
        assert message.order_type == OrderType.LIMIT_DELETED

    @mark.usefixtures("add_account_2_offers_to_cow_eth_market")
    def test_emit_fee_event_poller(
        self, test_client_for_account_1: Client, test_client_for_account_2: Client
    ):
        pair_name = "COW/ETH"

        test_client_for_account_2.start_event_poller(
            pair_name=pair_name, event_type=EmitFeeEvent
        )
        message_queue = test_client_for_account_2.message_queue

        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.BUY,
            size=Decimal("1"),
            worst_execution_price=Decimal("2"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_1.place_market_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1

        # Get message from message queue put there by event poller (Fee event)
        message = message_queue.get(block=True)

        # Check that fee was paid to account 2
        assert isinstance(message, FeeEvent)
        assert message.fee_to == test_client_for_account_2.wallet
        assert message.fee_asset == "ETH"

        # taker pay maker is 1 bip and price is 2 ETH
        assert round(message.fee, 4) == Decimal("2") * Decimal("0.0001")

    ######################################################################
    # active limit order tests
    ######################################################################

    def test_limit_order_partially_taken(
        self, test_client_for_account_1: Client, test_client_for_account_2: Client
    ):
        pair_name = "COW/ETH"

        test_client_for_account_1.start_event_poller(
            pair_name=pair_name, event_type=EmitTakeEvent
        )

        message_queue = test_client_for_account_1.message_queue

        limit_order = NewLimitOrder(
            pair_name="COW/ETH",
            order_side=OrderSide.BUY,
            size=Decimal("2"),
            price=Decimal("1.5"),
        )

        transaction = Transaction(orders=[limit_order])

        result = test_client_for_account_1.place_limit_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        assert len(test_client_for_account_1.active_limit_orders) == 1

        active_limit_order = test_client_for_account_1.active_limit_orders[1]
        assert active_limit_order.filled_size == Decimal("0")

        # Place market order with account_2
        market_order = NewMarketOrder(
            pair_name=pair_name,
            order_side=OrderSide.SELL,
            size=Decimal("1"),
            worst_execution_price=Decimal("1"),
        )

        transaction = Transaction(orders=[market_order])

        result = test_client_for_account_2.place_market_order(transaction=transaction)

        # Check that transaction was a success
        assert result.status == 1
        assert result.transaction_status == TransactionStatus.SUCCESS

        # Check that message was received but account_1 client
        message = message_queue.get(block=True)

        assert isinstance(message, OrderEvent)

        # Check that the active limit order has been updated correctly
        assert len(test_client_for_account_1.active_limit_orders) == 1

        active_limit_order = test_client_for_account_1.active_limit_orders[1]
        assert active_limit_order.filled_size == Decimal("1")
        assert active_limit_order.remaining_size == Decimal("1")
