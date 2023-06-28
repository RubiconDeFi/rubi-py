# bots

The purpose of `bots` is to provide example bots utilizing the `rubi` client.

Note: This is currently work in progress and aims to serve only as an example of how to develop trading strategies on
the Rubicon Protocol. 

Please refer to [this](https://docs.rubicon.finance/protocol/risks) for information on the risks associated to the
Rubicon Protocol.

## Structure

Currently, `bots` consists of a base implementation of an event trading framework using the `rubi` client and an 
implementation of a Grid bot that allows a user to provide liquidity on Rubicon mirroring if they were to LP in a 
Uniswap v3 like pool.

### Directory Structure

```
├── event_trading_framework
│   ├── helpers
│   │   ├── event_queues.py
│   │   ├── transaction_manager.py
│   ├── base_event_trading_framework.py
├── example_bots
│   ├── gridbot.py
│   ├── helpers
│   │   ├── ...
├── poetry.lock
├── pyproject.toml
├── main.py
├── local.env
├── bot_config.yaml
└──...
```

## Event trading framework

An event-driven system is a framework in which the flow and behavior of the system is driven by events. In this 
approach, the system responds to external events by triggering corresponding actions or processes.

The `BaseEventTradingFramework` found in [base_event_trading_framework.py](event_trading_framework/base_event_trading_framework.py)
is a base class that can be extended to implement any event driven strategy conceivable. 

Specific details on the event trading framework can be found [here](event_trading_framework/README.md).

## Example bots

Currently, the only example bot implemented is a grid bot.

### Grid bot

Specific details on the grid bot can be found [here](example_bots/gridbot.py).