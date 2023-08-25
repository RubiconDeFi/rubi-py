# Event trading framework

The base event trading framework provides a base class which can be inherited from to develop any conceivable event
strategy. When implementing your own strategy all you need to do is inherit the `BaseEventTradingFramework` and 
implement the following abstract methods:

* on_startup
* on_shutdown
* on_orderbook
* on_order

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
