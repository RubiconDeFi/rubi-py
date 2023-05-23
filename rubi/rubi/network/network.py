import json
import os
from enum import Enum

import yaml
from eth_typing import ChecksumAddress
from web3 import Web3


class NetworkName(Enum):
    # MAINNET
    OPTIMISM = "optimism"
    ARBITRUM = "abritrum"

    # TESTNET
    OPTIMISM_GOERLI = "optimism_goerli"
    ARBITRUM_GOERLI = "abritrum_goerli"


class Network:
    def __init__(
        self,
        # TODO: I think there should be a better way than having to pass this to the init
        # this whole init should be rethought along what I have done in contracts as currently this may be confusing
        path: str,
        node_url: str,
        name: str,
        chain_id: int,
        currency: str,
        rpc_url: str,
        explorer_url: str,
        rubicon: dict,
        token_addresses: dict
    ) -> None:
        self.name = name
        self.chain_id = chain_id
        self.w3 = Web3(Web3.HTTPProvider(node_url))

        self.currency = currency
        self.rpc_url = rpc_url
        self.explorer_url = explorer_url
        self.rubicon = RubiconContracts(path=path, w3=self.w3, **rubicon)

        checksummed_token_addresses: dict[str, ChecksumAddress] = {}
        for k, v in token_addresses.items():
            checksummed_token_addresses[k] = self.w3.to_checksum_address(v)

        self.token_addresses = checksummed_token_addresses

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))

    @classmethod
    def build(cls, name: NetworkName, node_url: str) -> "Network":
        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/{name.value}"

            with open(f"{path}/network.yaml") as f:
                network_data = yaml.safe_load(f)
                return cls(path=path, node_url=node_url, **network_data)
        except FileNotFoundError:
            raise Exception(f"no network config found for {name.value}, there should be a corresponding folder in "
                            f"the network_config directory")


class RubiconContracts:
    def __init__(self, path: str, w3: Web3, market: dict, router: dict) -> None:
        self.market = ContractRepr(path=path, w3=w3, name="market", **market)
        self.router = ContractRepr(path=path, w3=w3, name="router", **router)

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class ContractRepr:
    def __init__(self, path: str, w3: Web3, name: str, address: str) -> None:
        self.address = w3.to_checksum_address(address)

        try:
            with open(f"{path}/abis/{name}.json") as f:
                self.abi = json.load(f)
        except FileNotFoundError:
            self.abi = None

    def __repr__(self):
        return f"{type(self).__name__}(address='{self.address}', abi='{'Loaded' if self.abi is not None else 'None'}')"
