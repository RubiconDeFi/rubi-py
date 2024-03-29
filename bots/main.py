import logging
import os
import signal
from multiprocessing import Queue

import yaml
from dotenv import load_dotenv
from rubi import OrderTrackingClient

from example_bots import Grid, GridBot


if __name__ == "__main__":
    # setup logging
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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
    rubicon_client = OrderTrackingClient.from_http_node_url(
        http_node_url=http_node_url,
        pair_names=[grid_config["pair_name"]],
        message_queue=message_queue,
        wallet=wallet,
        key=key,
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
