import os
import logging
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Optional, Dict, Union

import yaml
from eth_typing import ChecksumAddress
from web3 import Web3

from rubi.contracts import ERC20, RubiconMarket, RubiconRouter, TransactionHandler

# from rubi.data import MarketData

logger = logging.getLogger(__name__)


class NetworkId(Enum):
    # MAINNET
    OPTIMISM = 10
    ARBITRUM_ONE = 42161
    BASE = 8453

    # TESTNET
    OPTIMISM_GOERLI = 420
    ARBITRUM_GOERLI = 421613
    POLYGON_MUMBAI = 80001


class Network:
    """This class represents a network and can be used to instantiate contracts using the `from_network` method. It
    provides and easy way to configure a client or contracts.
    """

    def __init__(
        self,
        w3: Web3,
        # The below all come from network_config/{network_name}/network.yaml
        name: str,
        chain_id: int,
        currency: str,
        rpc_url: str,
        explorer_url: str,
        market_data_url: str,
        market_data_fallback_url: str,
        rubicon: Dict,
        token_addresses: Dict,
        # optional custom token config file from the user
        custom_token_addresses_file: Optional[str] = None,
    ):
        """Initializes a Network instance.

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
        :param market_data_url: the URL of the market data subgraph (RubiconV2)
        :param rubicon: Dictionary containing Rubicon contract parameters.
        :type rubicon: dict
        :param token_addresses: Dictionary containing token addresses on the network.
        :type token_addresses: dict
        :param custom_token_addresses_file: The name of a yaml file (relative to the current working directory) with
            custom token addresses. Overwrites the token config found in network_config/{chain}/network.yaml.
            (optional, default is None).
        :type custom_token_addresses_file: Optional[str]
        """
        # General config
        self.name = name
        self.w3 = w3
        self.chain_id = chain_id
        self.currency = currency
        self.rpc_url = rpc_url
        self.explorer_url = explorer_url

        # Rubicon contracts
        self.rubicon_market = RubiconMarket.from_address(
            w3=self.w3, address=rubicon["market"]
        )
        self.rubicon_router = RubiconRouter.from_address(
            w3=self.w3, address=rubicon["router"]
        )

        # Tokens
        custom_token_addresses = self._custom_token_addresses(
            custom_token_addresses_file=custom_token_addresses_file
        )
        token_addresses.update(custom_token_addresses)

        checksummed_token_addresses = self._checksum_token_addresses(
            token_addresses=token_addresses
        )

        futures = {}
        with ThreadPoolExecutor() as executor:
            for name, address in checksummed_token_addresses.items():
                future = executor.submit(ERC20.from_address, self.w3, address)
                futures[name] = future

        self.tokens: Dict[Union[ChecksumAddress, str], ERC20] = {}
        for name, future in futures.items():
            erc20 = future.result()

            self.tokens[name] = erc20
            self.tokens[erc20.address] = erc20

        # Transaction Handler
        self.transaction_handler = TransactionHandler(
            w3=self.w3,
            contracts=[
                self.rubicon_market.contract,
                self.rubicon_router.contract,
                # We only need one ERC20 contract in order to decode ERC20 events
                list(self.tokens.values())[0].contract,
            ],
        )

        # Subgraph urls
        # TODO: currently we are utilizing just a single url, we should switch to a dictionary as the number of
        #  subgraphs we support grows
        self.market_data_url = market_data_url
        self.market_data_fallback_url = market_data_fallback_url

    @classmethod
    def from_http_node_url(
        cls,
        http_node_url: str,
        custom_token_addresses_file: Optional[str] = None,
    ) -> "Network":
        """Create a Network instance based on the node url provided. A call is then made to this node to get the
        chain_id which links to network_config/{network_name}/ using the NetworkId Enum.

        :param http_node_url: The URL of the HTTP node for the network.
        :type http_node_url: str
        :param custom_token_addresses_file: The name of a yaml file (relative to the current working directory) with
            custom token addresses. Overwrites the token config found in network_config/{chain}/network.yaml.
            (optional, default is None).
        :type custom_token_addresses_file: Optional[str]
        :return: A Network instance based on the network configuration.
        :rtype: Network
        :raises Exception: If no network configuration file is found for the specified network name.
        """
        w3 = Web3(Web3.HTTPProvider(http_node_url))

        network_name = NetworkId(w3.eth.chain_id).name.lower()

        try:
            path = f"{os.path.dirname(os.path.abspath(__file__))}/../../network_config/{network_name}"

            with open(f"{path}/network.yaml") as f:
                network_data = yaml.safe_load(f)
                return cls(
                    w3=w3,
                    custom_token_addresses_file=custom_token_addresses_file,
                    **network_data,
                )
        except FileNotFoundError:
            raise Exception(
                f"No network config found for {network_name}. There should be a corresponding folder in "
                f"the network_config directory."
            )

    @staticmethod
    def _custom_token_addresses(custom_token_addresses_file: str) -> Dict[str, str]:
        if not custom_token_addresses_file:
            return {}
        if not (
            custom_token_addresses_file.endswith(".yaml")
            or custom_token_addresses_file.endswith(".yml")
        ):
            raise Exception(
                f"token_config_file: {custom_token_addresses_file} must be a yaml file."
            )

        working_directory = os.getcwd()
        try:
            with open(f"{working_directory}/{custom_token_addresses_file}") as f:
                custom_token_addresses = yaml.safe_load(f)

                return custom_token_addresses
        except FileNotFoundError:
            raise Exception(
                f"could not find token_config_file, expected it to be a yaml file here: "
                f"{working_directory}/{custom_token_addresses_file}."
            )
        except AttributeError:
            raise Exception(
                f"{custom_token_addresses_file} cannot be empty, should be in the format: "
                f"token_symbol: address, e.g. WETH: chain_specific_weth_address"
            )

    def _checksum_token_addresses(
        self, token_addresses: Dict[str, str]
    ) -> Dict[str, ChecksumAddress]:
        checksummed_token_addresses: dict[str, ChecksumAddress] = {}
        for k, v in token_addresses.items():
            checksummed_token_addresses[k] = self.w3.to_checksum_address(v)

        return checksummed_token_addresses

    def token_from_address(self, address: Union[ChecksumAddress, str]):
        try:
            address = self.w3.to_checksum_address(address)
        except:
            logger.error(f"Could not checksum address {address}")
            return

        try:
            erc20 = ERC20.from_address(self.w3, address)
        except:
            logger.error(f"Could not find token with address {address}")
            return

        self.tokens[erc20.symbol] = erc20
        self.tokens[erc20.address] = erc20
