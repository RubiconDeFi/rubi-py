# Grid Bot

An explanation of what a Grid bot is can be found [here](https://cointelegraph.com/news/what-is-a-grid-trading-bot-and-how-do-you-use-it).

## Description of Strategy

The grid bot places bids and asks around a fair price. As these bids and asks are taken the balance of the base and 
quote asset are tracked and new bids and asks are placed based on these balances.

The bot aims to profit by always making the specified spread plus maker rebates.

## How to run the bot

Create a `local.env` file with the following format:

```
HTTP_NODE_URL=<node url>
PROD_WALLET=<address>
PROD_KEY=<key>
```

and additionally a `bot_config.yaml` with the following format:

```yaml
pair_name: "DAI/USDC"
starting_base_asset_amount: "100" # amount of DAI
starting_quote_asset_amount: "100" # amount of USDC
fair_price: "1" # fair price of DAI/USDC
price_tick: "0.1"
grid_range: "0.0016" # the range of the grif
spread: "0.0001" # the spread the grid will earn
min_level_size_in_base: "50" # grid level size
min_order_size_in_base: "50" # min order size in DAI
min_transaction_size_in_base: "50" # min size of a transaction in DAI
```

Now all you need to do is install the poetry dependencies:

```shell
    poetry shell && poetry update
```

and then run `main.py`:

```shell
    python main.py
```