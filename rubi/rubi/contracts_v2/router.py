from threading import Thread
from typing import Optional, Type

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.contract import Contract

from rubi.contracts_v2.helper import BaseContract
from rubi.contracts_v2.helper.event_types import EmitSwap
from rubi.network import Network


class RubiconRouter(BaseContract):
    """this class represents the RubiconRouter.sol contract and by default has read functionality.
    if a wallet and key are passed in instantiation then this class can also be used to write to the contract instance.

    :param w3: Web3 instance
    :type w3: Web3
    :param contract: Contract instance
    :type contract: Contract
    :param wallet: a wallet address of the signer (optional)
    :type wallet: Optional[ChecksumAddress]
    :param key: the private key of the signer (optional)
    :type key: Optional[str]
    """

    def __init__(
        self,
        w3: Web3,
        contract: Contract,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ) -> None:
        """constructor method"""
        super().__init__(
            w3=w3,
            contract=contract,
            wallet=wallet,
            key=key
        )

    @classmethod
    def from_network(
        cls,
        network: Network,
        wallet: Optional[ChecksumAddress] = None,
        key: Optional[str] = None
    ) -> "RubiconRouter":
        return cls.from_address_and_abi(
            w3=network.w3,
            address=network.rubicon.router.address,
            contract_abi=network.rubicon.router.abi,
            wallet=wallet,
            key=key
        )

    ######################################################################
    # read calls
    ######################################################################

    # TODO
    # getBookFromPair
    # getBookDepth
    # getBestOfferAndInfo
    # getExpectedSwapFill
    # getExpectedMultiswapFill
    # checkClaimAllUserBonusTokens

    ######################################################################
    # event listeners
    ######################################################################

    def start_event_listener(self, event_type: Type[EmitSwap]):
        event_filter = event_type.create_event_filter(self.contract)

        thread = Thread(
            target=self._start_default_listener,
            args=(event_filter, event_type.handler, 10),
            daemon=True
        )
        thread.start()

    ######################################################################
    # write calls
    ######################################################################

    # TODO
    # multiswap
    # swap
    # buyAllAmountWithETH
    # buyAllAmountForETH
    # swapWithETH
    # swapForETH
    # offerWithETH
    # offerForETH
    # cancelForETH
    # depositWithETH
    # withdrawForETH
