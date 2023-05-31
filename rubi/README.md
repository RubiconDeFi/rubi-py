# rubi

rubi is a python SDK for the Rubicon Protocol and has a variety of functionality for interacting with the protocol.
Documentation related to rubi and its functionality can be found [here](https://rubi.readthedocs.io/en/latest/#).

### Design Goals

The underlying goal of the design of rubi is to provide developers with a seamless integration experience when
interacting with the Rubicon. The SDK is built with the goal of enabling efficient and reliable communication with
Rubicon's smart contracts, empowering developers to effortlessly access and utilize Rubicon's features in their Python
applications.

### Examples

Examples of using the rubi sdk can be found [here](docs/examples).

### Directory Structure

```
├── docs
│   ├── examples
│   │   ├── example.py
│   ├── ...
├── network_config
│   ├── optimism
│   │   ├── abis
│   │   ├── network.yaml
│   ├── ...
│   ├── ERC20.json
│   ├── README.md
├── rubi
│   ├── contracts
│   ├── data
│   ├── network
│   ├── types
│   ├── client.py
├── tests
│   ├── ...
├── poetry.lock
├── pyproject.toml
└──...
```

The codebase follows the structure detailed above with:

- docs: all the sources for documentation along with some [examples](docs/examples/example.py).
- network_config: configuration and abis for the different networks. For more details see
  the [README.md](network_config/README.md).
- rubi: the python sources root. The main entrypoint for most users will be the [client.py](rubi/client.py).
- tests: test coverage of the repository.

### Decisions and Considerations

#### - Writing to the chain

Throughout the codebase we offer the user the option to pass in a nonce argument or derive it from chain state if none
is provided (via the `get_transaction_count` function). Aspirationally, we want to support a python based nonce manager
that can be used to manage nonces for the user. Until then, this optional parameter is meant to enable the user to
manage nonces themselves. When a user does not provide a nonce, we derive it from chain state accordingly. In this case,
we also wait for the transaction to be confirmed before continuing. If the transaction fails, an exception is raised and
the program is exited. The user can override this behavior by managing nonces themselves.

### SDK Disclaimer

This codebase is in Alpha and could contain bugs or change significantly between versions. Contributing through Issues
or Pull Requests is welcome!

### Protocol Disclaimer

Please refer to [this](https://docs.rubicon.finance/protocol/risks) for information on the risks associated to the
Rubicon Protocol.