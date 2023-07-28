from rubi import OrderSide

class Cancel: 

    def __init__(
        self,
        id, 
        block_number,
        block_index,
        log_index,
    ):
        
        self.id = id
        self.block_number = block_number
        self.block_index = block_index
        self.log_index = log_index
        

# the goal here is to build an order book history for a given pair
def get_book_history(
    client, 
    pair_name, 
    start_block, 
    # end_block, TODO: need to either handle nested filtering or add a block_number to the subgraph offer entity
    ):

    # we will create a dictionary of blocks : block index : log index : event
    ordering = {}

    # get the closed offers
    closed_offers = client.market_data.get_limit_orders(
        pair_name=pair_name, # "WETH/USDC",
        book_side=OrderSide.NEUTRAL,
        open=False,
        first=10000000000,
        removed_block_start=start_block,
    )

    # get any open offers
    open_offers = client.market_data.get_limit_orders(
        pair_name=pair_name, # "WETH/USDC",
        book_side=OrderSide.NEUTRAL,
        open=True,
        first=10000000000,
        # TODO: need to either handle nested filtering or add a block_number to the subgraph offer entity
    )

    # combine the offers
    offers = []
    offers.extend(closed_offers[0])
    offers.extend(closed_offers[1])
    offers.extend(open_offers[0])
    offers.extend(open_offers[1])

    for offer in offers:
        block = offer.block_number
        block_index = offer.block_index
        log_index = offer.log_index

        # if the block does not exist in the dictionary, add it 
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = offer

    # get the smallest block number
    smallest_block = min(ordering.keys())

    # get the smallest block index
    smallest_block_index = min(ordering[smallest_block].keys())

    # get the smallest log index
    smallest_log_index = min(ordering[smallest_block][smallest_block_index].keys())

    # get the first offer
    first_offer = ordering[smallest_block][smallest_block_index][smallest_log_index]
    start_time = first_offer.timestamp - 2

    # get any trades
    trade_objects = client.market_data.get_trades_objects(
        pair_name=pair_name, 
        book_side=OrderSide.NEUTRAL, 
        first=10000000000, 
        start_time=start_time, # TODO: either extend the trade entity to contain the block number or resolve nested filtering (subgrounds issue)
        # end_time=end_time
    )

    # TODO: add cancel entity to subgraph and its query 
    # build the cancels from the closed offers
    cancels = []
    for offer in offers: 
        if offer.removed_block_number==None: 
            continue
        cancels.append(Cancel(
            id=offer.id,
            block_number=offer.removed_block_number,
            block_index=offer.removed_block_index,
            log_index=offer.removed_log_index,
        ))

    # sort them by block number, block_index, log_index
    for trade in trade_objects: 
        block = trade.block_number
        block_index = trade.block_index
        log_index = trade.log_index

        # if the block does not exist in the dictionary, add it
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = trade

    for cancel in cancels: 
        block = cancel.block_number
        block_index = cancel.block_index
        log_index = cancel.log_index

        # if the block does not exist in the dictionary, add it
        if block not in ordering:
            ordering[block] = {}

        # if the block index does not exist in the block's dictionary, add it
        if block_index not in ordering[block]:
            ordering[block][block_index] = {}

        # assign the offer to the log index
        ordering[block][block_index][log_index] = cancel

    # return the list of events
    return ordering