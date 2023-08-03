
class TraderNode: 

    def __init__(self, trader_id):
        
        self.trader_id = trader_id
        self.offers = 0
        self.usd_offered = 0
        self.trades = 0
        self.usd_traded = 0

    def make_offer(self, usd_amt): # TODO: update to pass in limit order and order book objects
        
        self.offers += 1
        self.usd_offered += usd_amt

    def make_trade(self, usd_amt): # TODO: update to pass in trade and order book objects
        
        self.trades += 1
        self.usd_traded += usd_amt

    # def cancel_offer(self, order_id, order_book):
    
class Edge: # TODO: we may want to use bidirectional edges

    def __init__(
            self, 
        ):

        self.usd_amt = 0
        self.trades = 0

    def add_trade(self, usd_amt): 

        self.trades += 1
        self.usd_amt += usd_amt