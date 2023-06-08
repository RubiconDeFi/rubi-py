import logging as log
import os
import signal
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv
from rubi import Client

from example_bots import GridParams, GridBot

if __name__ == "__main__":
    # setup logging
    log.basicConfig(level=log.INFO)

    # load and set env variables
    load_dotenv("local.env")

    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("DEV_WALLET")
    key = os.getenv("DEV_KEY")

    # Initialize strategy message queue
    message_queue = Queue()

    # Initialize rubicon client
    rubicon_client = Client.from_http_node_url(
        http_node_url=http_node_url,
        message_queue=message_queue,
        wallet=wallet,
        key=key
    )

    # Setup Grid
    grid = GridParams(
        starting_base_asset_amount=Decimal("0"),
        starting_quote_asset_amount=Decimal("200"),
        starting_mid_price=Decimal("1860"),
        grid_spread_in_quote=Decimal("2"),
        level_spread_multiplier=Decimal("0"),
        number_levels=1,
        level_allocation_multiplier=Decimal("0")
    )

    # Initialize grid bot strategy
    grid_bot = GridBot(
        pair_name="WETH/USDC",
        grid_params=grid,
        min_order_size=Decimal("20"),
        client=rubicon_client,
    )

    # Shutdown bot on keyboard signal
    signal.signal(signal.SIGINT, grid_bot.stop)

    # Start grid bot strategy
    grid_bot.start()
