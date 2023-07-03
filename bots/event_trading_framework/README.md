# Event trading framework

The base event trading framework provides a base class which can be inherited from to develop any conceivable event
strategy. When implementing your own strategy all you need to do is inherit the `BaseEventTradingFramework` and 
implement the following abstract methods:

* on_startup
* on_shutdown
* on_orderbook
* on_order
* on_transaction_result (this will only receive events if the `ThreadedTransactionManager` is used to place transactions)

This [Grid bot](../example_bots/gridbot.py) is an example of inheriting the `BaseEventTradingFramework` to develop a 
strategy.

## Components

In using the `BaseEventTradingFramework` it is important to understand the following components of the framework which 
can be found [here](../event_trading_framework/helpers).

### Event queues

An event that the framework cares about is placed on an `event queue`. Each `event queue` has a handler that runs in its
own thread and processes events on the queue. Currently, there are two event implemented event queues:

1. `FIFOEventQueue`: every event placed on this queue is processed with a first in first out strategy
2. `FreshEventQueue`: only the most recent event placed on this queue is processed.

To explain the `FreshEventQueue` further, if the queue handler is busy and multiple events occur then whenever a new
event comes it will replace the current event on the queue. As such, when the handler becomes ready again it will 
immediately pull only the freshest event.

### Threaded transaction manager

The threaded transaction manager allows the framework to handle each new transaction in a new thread. Thus, the 
framework does not need to wait for a transaction to keep on processing events.

The status of transactions is passed back to the transaction result queue. These results are processed by the 
`on_transaction_result` handler in the framework that will be implemented in any strategy inheriting from the
`BaseEventTradingFramework`.

The `ThreadedTransactionManager` also handles nonces so multiple transactions can be placed simultaneously.