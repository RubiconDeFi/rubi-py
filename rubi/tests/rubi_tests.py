import os
from typing import Dict

import yaml
from web3 import Web3
from web3.contract import Contract

from rubi import Network, Client, RubiconMarket, RubiconRouter


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

    def test_add_pair(self, test_client: Client, cow: Contract, eth: Contract):
        pair_name = "COW/ETH"

        test_client.add_pair(pair_name=pair_name)

        assert len(test_client._pairs.keys()) == 1

        pair = test_client.get_pair(pair_name=pair_name)
        assert pair.base_asset.address == cow.address
        assert pair.quote_asset.address == eth.address
