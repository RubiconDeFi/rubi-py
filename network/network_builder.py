import os
import pickle

from rubi_network.network import Network
from rubi import Client, OrderSide, DetailedOrderBook

from dotenv import load_dotenv
from multiprocessing import Queue

load_dotenv('.env')

op_node = os.getenv('OP_MAIN_HTTP_NODE_URL')

queue = Queue()

# the timestamp of the first rewards period
start_time = 1688187600
end_time = 1690866000

# the block number of the first rewards period
start_block = 106300428 # TODO: get actual block and not estimate
end_block = 107710993



client = Client.from_http_node_url(
    http_node_url=op_node,
    #custom_token_addresses_file="custom_token_addresses.yaml",
    #wallet=wallet,
    #key=key,
    message_queue=queue,
)
# load the pickled data 
# TODO: there has to be a cleaner way to do this with file strings
with open('weth_usdc_trades.pickle', 'rb') as f:
   weth_usdc_trades = pickle.load(f)
with open('weth_usdc_offers.pickle', 'rb') as f:
   weth_usdc_offers = pickle.load(f)

'''
weth_usdc_trades = client.get_trades(pair_name="WETH/USDC", book_side=OrderSide.NEUTRAL, first=1000000, start_time=start_time, end_time=end_time)
with open('weth_usdc_trades.pickle', 'wb') as handle:
   pickle.dump(weth_usdc_trades, handle, protocol=pickle.HIGHEST_PROTOCOL)


weth_usdc_offers = client.get_offers(pair_name="WETH/USDC", book_side=OrderSide.NEUTRAL, first=1000000, end_time=end_time, removed_block_start=start_block, formatted=False)
with open('weth_usdc_offers.pickle', 'wb') as handle:
   pickle.dump(weth_usdc_offers, handle, protocol=pickle.HIGHEST_PROTOCOL)
'''

print(weth_usdc_trades.head(1))
print(weth_usdc_offers.head(1))

print(weth_usdc_offers.columns)
print(weth_usdc_trades.columns)

network = Network(
   graph=None,
   client=client,
   pair_names=[],
   book_histories=[],
)

print('\nsuccess, network object')
print(network)

book = DetailedOrderBook(
   bids=None,
   asks=None,
)

print('\nsuccess, book object')
print(book)

network = Network.from_df(
   client=client,
   pair_names=["WETH/USDC"],
   offers=[weth_usdc_offers],
   trades=[weth_usdc_trades]
)

history = network.book_histories["WETH/USDC"]
offers = history.offers[0] # TODO: figure out why this is not a list 
trades = history.trades[0] # TODO: figure out why this is not a list
cancels = history.cancels 

print(cancels[0])

offer_ids = []

# add the first offer
for offer in offers:
   
   # very important, we must set the base_amt & quote_amt to their original values
   offer.base_amt = offer.base_amt_original
   offer.quote_amt = offer.quote_amt_original
   
   offer_ids.append(offer.id)

   if offer.id == 2050831: 
      print('found the offer')

   book.add_order(offer)

trade_ids = []

for trade in trades: 
   book.market_order(trade)
   trade_ids.append(trade.order_id)

# find the trade_ids that are not in the offer_ids
for trade in trade_ids:
   if trade not in offer_ids:
      print('id not found in offers: ')
      print(trade)

for cancel in cancels: 
   book.remove_order(cancel.id)
      

print(len(offer_ids))
print(len(trade_ids))


print()

print(offer_ids[0])
print(trade_ids[0])

#print(book.bid_ids)

if 2050831 in book.bid_ids:
   print('found the bid')
if 2050831 in book.ask_ids:
   print('found the ask')

print('there are a total of ', len(book.bid_ids), ' bids')
print(len(book.bid_ids))
print('there are a total of ', len(book.ask_ids), ' asks')
print(len(book.ask_ids))

#print(book)

#print(network)



'''
with open('data/trades/dai_usdc_trades.pickle', 'rb') as f:
   dai_usdc_trades = pickle.load(f)
with open('data/trades/op_usdc_trades.pickle', 'rb') as f:
   op_usdc_trades = pickle.load(f)
with open('data/trades/weth_dai_trades.pickle', 'rb') as f:
   weth_dai_trades = pickle.load(f)
with open('data/trades/weth_usdc_trades.pickle', 'rb') as f:
   weth_usdc_trades = pickle.load(f)
with open('data/trades/weth_usdt_trades.pickle', 'rb') as f:
   weth_usdt_trades = pickle.load(f)


with open('data/offers/dai_usdc_trades.pickle', 'rb') as f:
   dai_usdc_offers = pickle.load(f)
with open('data/offers/op_usdc_trades.pickle', 'rb') as f:
   op_usdc_offers = pickle.load(f)
with open('data/offers/weth_dai_trades.pickle', 'rb') as f:
   weth_dai_offers = pickle.load(f)
with open('data/offers/weth_usdc_trades.pickle', 'rb') as f:
   weth_usdc_offers = pickle.load(f)
with open('data/offers/weth_usdt_trades.pickle', 'rb') as f:
   weth_usdt_offers = pickle.load(f)
'''



'''

g = nx.DiGraph()

# set logging config
log.basicConfig(level=log.INFO)

# set the env variables
http_node_url = os.getenv("HTTP_NODE_URL")
print('the node url is: ', http_node_url)
etherscan_api = os.getenv("ETHERSCAN_API")
mainnet_etherscan_api = os.getenv("MAINNET_ETHERSCAN_API")

# create a queue to receive messages
queue = Queue()

try: 
    book = DetailedOrderBook.from_rubicon_offer_book(([], []))
except:
    print('failed to initialize the book')
    exit()

# create client
client = Client.from_http_node_url(
    http_node_url=http_node_url,
    message_queue=queue
)

start_time = 1688187600
end_time = 1690606800
#erc = client.get_network_tokens()['WETH']
stables = ['USDC', 'USDT', 'DAI']

# Initialize an empty directed graph
order_book_history = get_book_history(client, "DAI/USDC", 107481004)

# get the min block number
min_block = min(order_book_history.keys())
print(order_book_history[min_block])

# get the keys and sort them in ascending order
blocks = list(order_book_history.keys())
blocks.sort()



book = None
bids = []
asks = []

for block in blocks: 

    # get the keys and sort them in ascending order
    block_indexes = list(order_book_history[block].keys())
    block_indexes.sort()

    for block_index in block_indexes:

        log_indexes = list(order_book_history[block][block_index].keys())
        log_indexes.sort()

        for log_index in log_indexes:

            event = order_book_history[block][block_index][log_index]

            if isinstance(event, LimitOrder):
                book.add_order(event)
            elif isinstance(event, Trade):
                # TODO: we need to handle the side here, trade currently does not have a side
                book.update_order(event.order_id, event.take_amt, event.give_amt)
            elif isinstance(event, Cancel):
                book.remove_order(event.id)


            print('this is block: ', block, ' block index: ', block_index, ' log index: ', log_index)
            print(order_book_history[block][block_index][log_index])

print(book)

#block_number=107481004
'''

# load the trades 
'''
trades = client.get_trades(pair_name="DAI/USDC", book_side=OrderSide.NEUTRAL, first=10, start_time=start_time, end_time=end_time)
trade_objects = client.market_data.get_trades_objects(pair_name="DAI/USDC", book_side=OrderSide.NEUTRAL, first=10, start_time=start_time, end_time=end_time)
trades = trades.sort_values(by=['block_number', 'block_index', 'log_index']).reset_index(drop=True)

trades['usd_amt'] = 0
trades['usd_amt'] = np.where(trades['give_gem'].isin(stables), trades['give_amt'], trades['take_amt'])

# pickle the trades
trades.to_pickle('dai_usdc.pkl')

# load the trades
trades = pd.read_pickle('dai_usdc.pkl')

print('dai_usdc: ', trades.columns)

#trade_objects = client.market_data.trade_query.dataframe_to_trades(trades)

print(trade_objects)

# Process trades
for index, trade in trades.iterrows():

    maker = trade['offer_from_address']
    taker = trade['from_address']
    usd_amt = trade['usd_amt']

    # Add/update maker node
    if maker not in g:
        g.add_node(maker, data=TraderNode(maker))
    g.nodes[maker]['data'].make_trade(usd_amt)

    # Add/update taker node
    if taker not in g:
        g.add_node(taker, data=TraderNode(taker))
    g.nodes[taker]['data'].make_trade(usd_amt)

    # Add/update the edge # TODO: we may want to use bidirectional edges
    # for now, the edge is directed from maker to taker
    if not g.has_edge(maker, taker):
        g.add_edge(maker, taker, data=Edge())
    g.edges[maker, taker]['data'].add_trade(usd_amt)

pure_pairs = find_pure_pairs(g)
print(f"Pairs where 100% of their trades are with each other: {pure_pairs}")
'''