# rubi
rubi is a python SDK for the Rubicon Protocol and has a variety of functionality for interacting with the protocol. documentation related to rubi and its functionality can be found [here](https://rubi.readthedocs.io/en/latest/#). 

### Design Goals
the underlying goal of the design of rubi is to decrease user friction when interacting with the protocol, and when interacting with the sdk. we want to enable the user
as much access as possible without requiring any input from the user. for example, by breaking up the contract functionality into read and write classes, we enable the user to
use the sdk to read from the protocol without passing in any keys. within the data classes, we aim to provide as much information as possible to the user without requiring any 
additional input such as api keys. when it is clearly useful, we will add higher level classes that provide additional functionality to the user by requiring additional input. 

### SDK Disclaimer

this codebase is in Alpha and could contain bugs or change significantly between versions. contributing through Issues or Pull Requests is welcome!

### Protocol Disclaimer

please refer to [this](https://docs.rubicon.finance/protocol/risks) for information on the risks associated to the Rubicon Protocol.