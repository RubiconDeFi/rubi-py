import logging as log
import os
import signal
from _decimal import Decimal
from multiprocessing import Queue

from dotenv import load_dotenv
from rubi import Client

from example_bots import Grid, GridBot

if __name__ == "__main__":
    # setup logging
    log.basicConfig(level=log.INFO)

    # load and set env variables
    load_dotenv("local.env")

    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("DEV_WALLET")
    key = os.getenv("DEV_KEY")

    # Setup Grid
    grid = Grid(
        starting_base_asset_amount=Decimal("1000"),
        starting_quote_asset_amount=Decimal("1000"),
        starting_base_asset_average_price=None,
        fair_price=Decimal("1"),
        price_tick=Decimal("0.01"),
        grid_range=Decimal("0.2"),
        spread=Decimal("0.02"),
        min_order_size_in_quote=Decimal("100")
    )

    o = grid.get_desired_orders()

    print(o)

    # Initialize strategy message queue
    message_queue = Queue()

    # Initialize rubicon client
    rubicon_client = Client.from_http_node_url(
        http_node_url=http_node_url,
        message_queue=message_queue,
        wallet=wallet,
        key=key
    )

    # Initialize grid bot strategy
    grid_bot = GridBot(
        pair_name="USDT/USDC",
        grid=grid,
        client=rubicon_client,
    )

    # Shutdown bot on keyboard signal
    signal.signal(signal.SIGINT, grid_bot.stop)  # noqa

    # Start grid bot strategy
    grid_bot.start()
