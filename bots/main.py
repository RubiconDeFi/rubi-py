import logging as log
import os
import signal
from _decimal import Decimal
from multiprocessing import Queue

import yaml
from dotenv import load_dotenv
from rubi import Client

from example_bots import Grid, GridBot

if __name__ == "__main__":
    # setup logging
    log.basicConfig(level=log.INFO)

    # load the bot config
    with open("bot_config.yaml") as file:
        grid_config = yaml.safe_load(file)

    # load and set env variables
    load_dotenv("local.env")

    http_node_url = os.getenv("HTTP_NODE_URL")
    wallet = os.getenv("PROD_WALLET")
    key = os.getenv("PROD_KEY")

    # Setup Grid
    grid = Grid(
        starting_base_asset_amount=Decimal(grid_config["starting_base_asset_amount"]),
        starting_quote_asset_amount=Decimal(grid_config["starting_quote_asset_amount"]),
        starting_base_asset_average_price=None,
        fair_price=Decimal(grid_config["fair_price"]),
        price_tick=Decimal(grid_config["price_tick"]),
        grid_range=Decimal(grid_config["grid_range"]),
        spread=Decimal(grid_config["spread"]),
        min_order_size_in_quote=Decimal(grid_config["min_order_size_in_quote"])
    )

    debug = grid.get_desired_orders()
    log.debug(debug)

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
        pair_name=grid_config["pair_name"],
        grid=grid,
        client=rubicon_client,
    )

    # Shutdown bot on keyboard signal
    signal.signal(signal.SIGINT, grid_bot.stop)  # noqa

    # Start grid bot strategy
    grid_bot.start()
