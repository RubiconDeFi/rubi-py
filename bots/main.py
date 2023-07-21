import logging as log
import os
import signal
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
    grid = Grid(**grid_config)

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
