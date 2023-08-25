import math
from _decimal import Decimal
from typing import List, Tuple, Optional, Dict

from rubi import OrderSide, NewLimitOrder, LimitOrder


class DesiredOrder:
    def __init__(
        self,
        side: OrderSide,
        price: Decimal,
        size: Decimal,
    ):
        self.side = side
        self.price = price
        self.size = size


class GridLevel:
    def __init__(self, bid: DesiredOrder, ask: DesiredOrder):
        self.bid = bid
        self.ask = ask


class Grid:
    def __init__(
        self,
        # Assets
        pair_name: str,
        # Inventory
        starting_base_asset_amount: Decimal | str,
        starting_quote_asset_amount: Decimal | str,
        # Grid
        fair_price: Decimal | str,
        price_tick: Decimal | str,
        grid_range: Decimal | str,
        spread: Decimal | str,
        min_level_size_in_base: Decimal | str,
        # Order
        min_order_size_in_base: Decimal | str,
        # Transaction
        min_transaction_size_in_base: Decimal | str,
    ):
        base_asset, quote_asset = pair_name.split("/")

        # Assets
        self.base_asset = base_asset
        self.quote_asset = quote_asset

        self.pair_name = f"{base_asset}/{quote_asset}"

        # Grid Inventory
        self._inventory = {
            base_asset: Decimal(starting_base_asset_amount),
            quote_asset: Decimal(starting_quote_asset_amount),
        }

        self._last_sold_price: Optional[Decimal] = None
        self._last_bought_price: Optional[Decimal] = None

        # Grid Parameters
        self.fair_price = Decimal(fair_price)
        self.price_tick = Decimal(price_tick)
        self.grid_range = Decimal(grid_range)
        self.spread = Decimal(spread)
        self.min_level_size_in_base = Decimal(min_level_size_in_base)

        self.grid_size = (
            self._inventory[self.base_asset]
            + self._inventory[self.quote_asset] / self.fair_price
        )

        # Grid
        self.desired_grid: List[GridLevel] = self._construct_grid()
        self.num_grid_levels = len(self.desired_grid)
        self.middle_index = math.ceil(self.num_grid_levels / 2)

        self.current_grid_index: int = self._calculate_grid_index()

        # Order
        self.min_order_size_in_base = Decimal(min_order_size_in_base)

        # Transaction
        self.min_transaction_size_in_base = Decimal(min_transaction_size_in_base)

    ######################################################################
    # inventory functions
    ######################################################################

    def update_inventory(
        self,
        open_orders: Dict[int, LimitOrder],
        base_asset_wallet_balance: Decimal,
        quote_asset_wallet_balance: Decimal,
    ):
        self._inventory[self.base_asset] = (
            self._amount_in_market(
                side=OrderSide.SELL, open_limit_orders=list(open_orders.values())
            )
            + base_asset_wallet_balance
        )
        self._inventory[self.quote_asset] = (
            self._amount_in_market(
                side=OrderSide.BUY, open_limit_orders=list(open_orders.values())
            )
            + quote_asset_wallet_balance
        )
        self.current_grid_index = self._calculate_grid_index()

    def add_trade(self, order_side: OrderSide, price: Decimal, size: Decimal) -> None:
        self._inventory[self.base_asset] += size * order_side.sign()
        self._inventory[self.quote_asset] -= size * price * order_side.sign()

        match order_side:
            case OrderSide.BUY:
                self._last_bought_price = price
            case OrderSide.SELL:
                self._last_sold_price = price

        self.grid_size = (
            self._inventory[self.base_asset]
            + self._inventory[self.quote_asset] / self.fair_price
        )
        self.current_grid_index = self._calculate_grid_index()

    def get_base_asset_amount(self):
        return self._inventory[self.base_asset]

    def get_quote_asset_amount(self):
        return self._inventory[self.quote_asset]

    ######################################################################
    # grid functions
    ######################################################################

    def get_orders(
        self, best_bid_price: Decimal, best_ask_price: Decimal
    ) -> List[NewLimitOrder]:
        desired_bids, desired_asks = self._get_desired_orders(
            best_bid_price=best_bid_price, best_ask_price=best_ask_price
        )

        bid_amount_available = self._inventory[self.quote_asset]
        ask_amount_available = self._inventory[self.base_asset]

        bids_to_place = []
        for bid in desired_bids:
            size = min(bid_amount_available / bid.price, bid.size)
            if size >= self.min_order_size_in_base:
                bids_to_place.append(
                    NewLimitOrder(
                        pair_name=self.pair_name,
                        order_side=OrderSide.BUY,
                        size=size,
                        price=bid.price,
                    )
                )
            bid_amount_available -= size * bid.price

        asks_to_place = []
        for ask in desired_asks:
            size = min(ask_amount_available, ask.size)
            if size >= self.min_order_size_in_base:
                asks_to_place.append(
                    NewLimitOrder(
                        pair_name=self.pair_name,
                        order_side=OrderSide.SELL,
                        size=size,
                        price=ask.price,
                    )
                )
            ask_amount_available -= size

        return bids_to_place + asks_to_place

    def _get_desired_orders(
        self, best_bid_price: Decimal, best_ask_price: Decimal
    ) -> Tuple[List[DesiredOrder], List[DesiredOrder]]:

        bid_below = best_ask_price
        if self._last_sold_price:
            if self._last_sold_price < bid_below:
                bid_below = self._last_sold_price

        ask_above = best_bid_price
        if self._last_bought_price:
            if self._last_bought_price > ask_above:
                ask_above = self._last_bought_price

        desired_bids = list(
            map(
                lambda level: level.bid,
                self.desired_grid[self.current_grid_index :: -1],
            )
        )
        desired_bids = list(filter(lambda bid: bid.price < bid_below, desired_bids))
        desired_asks = list(
            map(lambda level: level.ask, self.desired_grid[self.current_grid_index :])
        )
        desired_asks = list(filter(lambda ask: ask.price > ask_above, desired_asks))

        return desired_bids, desired_asks

    def _calculate_grid_index(self) -> int:
        quote_as_percent_of_size = self._inventory[self.quote_asset] / (
            self.grid_size * self.fair_price
        )

        index = self.num_grid_levels * quote_as_percent_of_size

        if index <= self.middle_index:
            current_grid_index = math.ceil(index)
        else:
            current_grid_index = math.floor(index)

        return current_grid_index - 1

    def _construct_grid(self) -> List[GridLevel]:
        bid_side = self._construct_grid_side(OrderSide.BUY)
        bid_side.reverse()

        ask_side = self._construct_grid_side(OrderSide.SELL)

        bid_price = self.round_to_grid_tick(
            self.fair_price - self.spread / Decimal("2")
        )
        ask_price = self.round_to_grid_tick(
            self.fair_price + self.spread / Decimal("2")
        )

        middle_level = GridLevel(
            bid=DesiredOrder(
                price=bid_price, size=bid_side[-1].bid.size, side=OrderSide.BUY
            ),
            ask=DesiredOrder(
                price=ask_price, size=ask_side[0].ask.size, side=OrderSide.SELL
            ),
        )

        desired_grid = bid_side + [middle_level] + ask_side

        return desired_grid

    def _construct_grid_side(self, side: OrderSide) -> List[GridLevel]:
        half_size_in_base = self.grid_size / Decimal("2")

        capital_restricted_number_of_levels = (
            half_size_in_base / self.min_level_size_in_base
        )

        edge = self.fair_price - side.sign() * self.grid_range / 2

        price = (
            self.round_to_grid_tick(self.fair_price - (side.sign() * self.spread) / 2)
            - side.sign() * self.price_tick
        )

        max_number_levels = (price * side.sign() - edge * side.sign()) / self.price_tick

        skip_capital = round(max_number_levels / capital_restricted_number_of_levels)

        level_size = half_size_in_base / min(
            max_number_levels / skip_capital, capital_restricted_number_of_levels
        )

        grid_side_levels = []
        remaining_capital = half_size_in_base
        i = 1
        match side:
            case OrderSide.BUY:
                while price >= edge:
                    size = (
                        level_size
                        if (
                            i % skip_capital == 0
                            and remaining_capital >= self.min_level_size_in_base
                        )
                        else Decimal("0")
                    )

                    grid_side_levels.append(
                        GridLevel(
                            bid=DesiredOrder(
                                price=price, size=size, side=OrderSide.BUY
                            ),
                            ask=DesiredOrder(
                                price=price + self.spread,
                                size=size,
                                side=OrderSide.SELL,
                            ),
                        )
                    )
                    price = price - self.price_tick
                    i += 1
                    remaining_capital -= size

            case OrderSide.SELL:
                while price <= edge:
                    size = (
                        level_size
                        if (
                            i % skip_capital == 0
                            and remaining_capital > self.min_level_size_in_base
                        )
                        else Decimal("0")
                    )

                    grid_side_levels.append(
                        GridLevel(
                            bid=DesiredOrder(
                                price=price - self.spread, size=size, side=OrderSide.BUY
                            ),
                            ask=DesiredOrder(
                                price=price, size=size, side=OrderSide.SELL
                            ),
                        )
                    )
                    price = price + self.price_tick
                    i += 1
                    remaining_capital -= size

        return list(
            filter(
                lambda level: level.bid.size != Decimal("0")
                or level.ask.size != Decimal("0"),
                grid_side_levels,
            )
        )

    ######################################################################
    # helper functions
    ######################################################################

    @staticmethod
    def _amount_in_market(
        side: OrderSide, open_limit_orders: List[LimitOrder]
    ) -> Decimal:
        open_orders = list(
            filter(lambda order: order.order_side == side, open_limit_orders)
        )

        if side == OrderSide.BUY:
            amount = Decimal(
                sum(map(lambda order: order.remaining_size * order.price, open_orders))
            )
        else:
            amount = Decimal(sum(map(lambda order: order.remaining_size, open_orders)))

        return amount

    def round_to_grid_tick(self, number: Decimal) -> Decimal:
        if self.price_tick < Decimal("1"):
            rounded = round(number / self.price_tick) * self.price_tick
        else:
            rounded = round(number * self.price_tick) / self.price_tick

        return rounded
