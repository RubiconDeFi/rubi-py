from rubi import LimitOrder, Trade
from .data import Cancel

# For now, we are just going to assume that we are only handling one pair at a time.
class TraderNode: 

    def __init__(self, trader_id, book):
        
        self.trader_id = trader_id
        self.offers = 0
        self.usd_offered = 0
        self.usd_filled = 0
        self.fills = 0
        
        self.trades = 0
        self.usd_traded = 0
        self.book = book
        
        # useful for now
        # Optimism specific
        self.stables = ['0x7f5c764cbc14f9669b88837ca1490cca17c31607', '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58', '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1']
        self.stable_decimals = {
            '0x7f5c764cbc14f9669b88837ca1490cca17c31607': 6,
            '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58': 6,
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1': 18
        }

    def make_offer(self, usd_amt): # TODO: update to pass in limit order and order book objects
        
        self.offers += 1
        self.usd_offered += usd_amt

    def make_trade(self, usd_amt): # TODO: update to pass in trade and order book objects
        
        self.trades += 1
        self.usd_traded += usd_amt

    def add_fill(self, usd_amt):

        self.fills += 1   
        self.usd_filled += usd_amt

    # TODO: assumes that we are always dealing with a stable pair
    def add_order(self, order: LimitOrder): 

        self.book.add_order(order)

        # assumes the quote amount is the stable amount
        usd_amt = order.get_value()
        self.make_offer(usd_amt)

    def add_fill_trade(self, market_order: Trade):

        # determines the stable amount
        if market_order.take_gem in self.stables: 
            decimals = self.stable_decimals[market_order.take_gem]
            usd_amt = market_order.take_amt / (10 ** decimals)
        elif market_order.give_gem in self.stables:
            decimals = self.stable_decimals[market_order.give_gem]
            usd_amt = market_order.give_amt / (10 ** decimals)

        self.add_fill(usd_amt)

    def add_market_order(self, market_order: Trade): 

        self.book.market_order(market_order)

        # determines the stable amount
        if market_order.take_gem in self.stables: 
            decimals = self.stable_decimals[market_order.take_gem]
            usd_amt = market_order.take_amt / (10 ** decimals)
        elif market_order.give_gem in self.stables:
            decimals = self.stable_decimals[market_order.give_gem]
            usd_amt = market_order.give_amt / (10 ** decimals)

        self.make_trade(usd_amt)

    def add_cancel(self, cancel: Cancel): 

        self.book.remove_order(cancel.id)

    def handle_event(self, event): 

        if isinstance(event, LimitOrder):
            self.add_order(event)
        elif isinstance(event, Trade):
            self.add_market_order(event)
        elif isinstance(event, Cancel):
            self.add_cancel(event)
        else: 
            raise Exception("Error: event type not supported")
        
    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))
    
class Edge: # TODO: we may want to use bidirectional edges

    def __init__(
            self, 
            maker: TraderNode,
            taker: TraderNode,
        ):

        self.usd_amt = 0
        self.trades = 0
        self.maker = maker
        self.taker = taker
        self.relative_maker_volume = 0
        self.relative_maker_trades = 0
        self.relative_taker_volume = 0
        self.relative_taker_trades = 0

        # stats related to the offers


        # useful for now
        # Optimism specific
        self.stables = ['0x7f5c764cbc14f9669b88837ca1490cca17c31607', '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58', '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1']
        self.stable_decimals = {
            '0x7f5c764cbc14f9669b88837ca1490cca17c31607': 6,
            '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58': 6,
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1': 18
        }

    def add_trade(self, usd_amt): 

        self.trades += 1
        self.usd_amt += usd_amt

        if self.maker.usd_filled > 0:
            self.relative_maker_volume = self.usd_amt / self.maker.usd_filled
        else:
            self.relative_maker_volume = 0
        
        if self.maker.fills > 0:
            self.relative_maker_trades = self.trades / self.maker.fills
        else:
            self.relative_maker_trades = 0
        
        if self.taker.usd_traded > 0:
            self.relative_taker_volume = self.usd_amt / self.taker.usd_traded
        else:
            self.relative_taker_volume = 0
        
        if self.taker.trades > 0:
            self.relative_taker_trades = self.trades / self.taker.trades
        else:
            self.relative_taker_trades = 0

    def add_market_order(self, market_order: Trade): 

        # determines the stable amount
        if market_order.take_gem in self.stables: 
            decimals = self.stable_decimals[market_order.take_gem]
            usd_amt = market_order.take_amt / (10 ** decimals)
        elif market_order.give_gem in self.stables:
            decimals = self.stable_decimals[market_order.give_gem]
            usd_amt = market_order.give_amt / (10 ** decimals)

        self.add_trade(usd_amt)

    def __repr__(self):
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in self.__dict__)
        return "{}({})".format(type(self).__name__, ", ".join(items))