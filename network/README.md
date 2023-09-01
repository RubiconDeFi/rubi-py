# Network

the `network` project combines data collection from `rubi-py` with `networkx` functionality to build a comprehensive network 
structure that maps activity on the order book to `edges & nodes` in order to better visualize activity between order book 
actors at the low level. it utilizes the `DetailedOrderBook` defined within `rubi-py` to reconstruct a period of activity and
provide granular insight into the orderbook at a given point in time. this project is still in `beta` and exists within this 
branch of the repository. the main entrypoint is from the `Network` object, the file `network_builder.py` provides an example
of how to initialize the object given a dataframe of both `offers` & `trades`. it is important to note, to accurately represent
an orderbook for a given period you must have all offers that were open during the period. this can include offers that were 
previously created and closed/open in the period or created and closed/open during the period. given the current constraints
of the available filters for subgraph queries, this requires multiple queries in order to properly gather all offers.
the process to retrieve the appropriate offer data for a given pair will be similar to the following: 

```python
start_time = <unix startime>
end_time = <unix endtime>
start_block = <starting block>

# get offers created during the period 
weth_usdc_offers_created = client.get_offers(pair_name="WETH/USDC", book_side=OrderSide.NEUTRAL, start_time=start_time, end_time=end_time, formatted=False)

# get offers created before the period and closed during/after the period 
weth_usdc_offers_prior = client.get_offers(pair_name="WETH/USDC", book_side=OrderSide.NEUTRAL, removed_block_start=start_block, formatted=False)

# get any offers that were created before the period and still open 
weth_usdc_offers_prior_live = client.get_offers(pair_name="WETH/USDC", book_side=OrderSide.NEUTRAL, start_time=start_time, open=True, formatted=False)

weth_usdc_offers = pd.concat([weth_usdc_offers_created, weth_usdc_offers_prior, weth_usdc_offers_prior_live]).drop_duplicates()

# collect all trades during the period 
weth_usdc_trades = client.get_trades(pair_name="WETH/USDC", start_time=start_time, end_time=end_time)
```

the offer entity for the `RubiconV2` subgraphs now all contain the relevant close information to properly determine when they were closed, removing the need to use the `_Internal` subgraph version that is present within this branch. 

## Visualizing the Graph

once the network object has been constructed, it is trivial to create an `html` representation of it that can be used to 
visualize the network. the following demonstrates how to do so for a given pair: 

```python 

from pyvis.network import Network as Net

# load trade data
with open('weth_usdc_trades.pickle', 'rb') as f:
   weth_usdc_trades = pickle.load(f)
with open('weth_usdc_offers.pickle', 'rb') as f:
   weth_usdc_offers = pickle.load(f)

# build the network 
network = Network.from_df(
   client=client,
   pair_names=["WETH/USDC"],
   offers=[weth_usdc_offers],
   trades=[weth_usdc_trades]
)

# build the graph
network.build_graph(
   pair_name="WETH/USDC",
)

# get the graph object 
g = network.graphs['WETH/USDC']

# create the visualization
net = Net()
net.from_nx(g)
net.show("mygraph.html")

```

## Going Forward

This intial work sets the foundation for: 1) retroactiveley evaluating order book activity, 2): creating a network graph based
upon order book activity. `BookHistory.from_df` will take the dataframes created above to build a dictionary that maps
order book events to a dictionary that is `{"block_number": {"block_index": {"log_index": "Event"}}}. `Network.build_graph` can 
then process this dictionary to rebuild the `DetailedOrderBook` from these events. The logic within this function can be 
utilized to rebuild instances of the `DetailedOrderBook` at any point in time, allowing for granular data anlysis on historical
activity. This can be incredibly useful when attempting to determine if an actor achieved certain depth requirements for a DDMM
campaign, and can be supplemented with price data in order to perform further analysis. 