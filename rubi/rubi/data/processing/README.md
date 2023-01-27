### market aid 
*01.27.23*

currently, we rely upon the [market-aid subgraph](https://github.com/RubiconDeFi/rubi-subgraphs/tree/master/MarketAid) to get data 
related to the market aid program. within this subgraph there is an entity called `AidTokenHistory` which maps any change to 
a market aid asset balance to a transaction level of granularity. this is useful in the tracking of a market aid contract historical
balance, but has some draw backs in practice. specifically, it adds complexity when attempting to track `AidTokenHistory` balances 
in a time series manner. because of this, when tracking a market aid asset balance over time, we rely upon the `balance_change`
field of the `AidTokenHistory` entity to recreate a time series of balances. this necessitates loading all `AidTokenHistory`
entities and is not ideal in a long term context.

going forward, we should strive for a system that allows for the creation of a time series of market aid asset balances for any 
given range of time. this is especially pertinent in the context of coming bedrock iterations, where multiple transactions 
will be batched into a single block (and therefore a single timestamp in the time series).