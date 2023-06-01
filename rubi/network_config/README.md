# network_config

This is the default location of all network config in the repo. Config here is used to construct a `Network` instance
found in [network.py](../rubi/network/network.py). This can then be used to instantiate contracts in the
[contracts_v2](../rubi/contracts_v2) folder using the `from_network` constructor.

To understand how this is all mapped into the `Network` instance please see: [network.py](../rubi/network/network.py).

### Directory Structure

```
├── network_config
│   ├── {network name}
│   │   ├── abis <- the abis of all the rubicon contracts deployed on chain.
│   │   │   ├── market.json
│   │   │   ├── ...
│   │   ├── network.yaml <- the configuration for the network.
│   ├── ...
│   ├── ERC20.json <- standard abi for the openzepplin ERC20 contract.
│   ├── README.md
└──...
```

Note: the {network name} folder must map to the `NetworkId` enum found in [network.py](../rubi/network/network.py).

### network.yaml

```yaml
name: "Optimism Goerli" # <- the plaintext name of the network
chain_id: 420 # <- the network id
currency: "ETH" # <- the currency of the network
rpc_url: "https://goerli.optimism.io" # <- the rpc url of the network
explorer_url: "https://goerli-explorer.optimism.io/" # <- the url of the network explorer

rubicon:
  market:
    address: "0x9d0D6c259566d8161a1b2c513af0463992db38bc" # <- the address of the RubiconMarket.sol contract on this network
  router:
    address: "0x7a1B7720E691E74ee523E4ecBD6C77A094222757" # <- the address of the RubiconRouter.sol contract on this network

token_addresses: # <- the addresses of tokens of interest on this network
  ETH: "0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000"
  WETH: "0x4200000000000000000000000000000000000006"
  OP: "0xCeE7148028Ff1B08163343794E85883174a61393"
  USDC: "0xe432f229521eE954f80C83257485405E3d848d17"
```