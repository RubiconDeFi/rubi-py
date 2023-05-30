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
    POLYGON_MUMBAI = "polygon_mumbai"


class Network:
    """This class represents a network and can be used to instantiate contracts using the `from_network` method. It
    provides and easy way to configure a client or contracts.
    """

    def __init__(
        self,
        path: str,
        w3: Web3,
        # The below all come from network_config/{network_name}/network.yaml
        name: str,
        chain_id: int,
        currency: str,
        rpc_url: str,
        explorer_url: str,
        rubicon: dict,
        token_addresses: dict
    ) -> None:
        """Initializes a Network instance.

        :param path: The path to the network configuration.
        :type path: str
        :param w3: The Web3 instance connected to the network.
        :type w3: Web3
        :param name: The name of the network.
        :type name: str
        :param chain_id: The chain ID of the network.
        :type chain_id: int
        :param currency: The base currency of the network.
        :type currency: str
        :param rpc_url: The RPC URL of the network.
        :type rpc_url: str
        :param explorer_url: The URL of the network explorer.
        :type explorer_url: str
        :param rubicon: Dictionary containing Rubicon contract parameters.
        :type rubicon: dict
        :param token_addresses: Dictionary containing token addresses on the network.
        :type token_addresses: dict
        """
        self.name = name
        self.chain_id = chain_id
        self.w3 = w3

        self.currency = currency
        self.rpc_url = rpc_url
        self.explorer_url = explorer_url
        self.rubicon = RubiconContracts(path=path, w3=self.w3, **rubicon)

        checksummed_token_addresses: dict[str, ChecksumAddress] = {}
        for k, v in token_addresses.items():
            checksummed_token_addresses[k] = self.w3.to_checksum_address(v)

        self.token_addresses = checksummed_token_addresses

    @classmethod
    def from_config(cls, name: NetworkName, http_node_url: str) -> "Network":
        """Create a Network instance based on the network name provided which links to network_config/{network_name}/.

        :param name: The name of the network.
        :type name: NetworkName
        :param http_node_url: The URL of the HTTP node for the network.
        :type http_node_url: str
        :return: A Network instance based on the network configuration.
        :rtype: Network
        :raises Exception: If no network configuration file is found for the specified network name.
        """
        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/{name.value}"
            w3 = Web3(Web3.HTTPProvider(http_node_url))

            with open(f"{path}/network.yaml") as f:
                network_data = yaml.safe_load(f)
                return cls(path=path, w3=w3, **network_data)
        except FileNotFoundError:
            raise Exception(f"no network config found for {name.value}, there should be a corresponding folder in "
                            f"the network_config directory")

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class RubiconContracts:
    """This class is a simple wrapper for all the Rubicon contracts on a network. Right now it only contains the market
    and router contracts.
    """

    def __init__(self, path: str, w3: Web3, market: dict, router: dict) -> None:
        """Initialize a RubiconContracts instance.

        :param path: The path to the network configuration.
        :type path: str
        :param w3: The Web3 instance connected to the network.
        :type w3: Web3
        :param market: Dictionary containing market contract information.
        :type market: dict
        :param router: Dictionary containing router contract information.
        :type router: dict
        """
        self.market = ContractRepr(path=path, w3=w3, name="market", **market)
        self.router = ContractRepr(path=path, w3=w3, name="router", **router)

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class ContractRepr:
    """This class represents a contract on a specific network.
    """

    def __init__(self, path: str, w3: Web3, name: str, address: str) -> None:
        """Initialize a ContractRepr instance which is a representation of a contract containing the contract address
        and abi.

        :param path: The path to the network configuration.
        :type path: str
        :param w3: The Web3 instance connected to the network.
        :type w3: Web3
        :param name: The name of the contract.
        :type name: str
        :param address: The address of the contract.
        :type address: str
        """
        self.address = w3.to_checksum_address(address)

        try:
            with open(f"{path}/abis/{name}.json") as f:
                self.abi = json.load(f)
        except FileNotFoundError:
            self.abi = None

    def __repr__(self):
        return f"{type(self).__name__}(address='{self.address}', abi='{'Loaded' if self.abi is not None else 'None'}')"
