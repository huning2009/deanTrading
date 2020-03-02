from typing import Any

from vnpy.trader.constant import Direction, Offset
from vnpy.trader.object import (TickData, OrderData, TradeData)
from vnpy.trader.utility import round_to

from .template import SpreadAlgoTemplate
from .base import SpreadData


class SpreadTakerAlgo(SpreadAlgoTemplate):
    """"""
    algo_name = "SpreadTaker"

    def __init__(
        self,
        algo_engine: Any,
        algoid: str,
        spread: SpreadData,
        direction: Direction,
        offset: Offset,
        price: float,
        volume: float,
        lot_size: float,
        payup: int,
        interval: int,
        cancel_active_short_interval: int,
        lock: bool
    ):
        """"""
        super().__init__(
            algo_engine, algoid, spread,
            direction, offset, price, volume, lot_size,
            payup, interval, cancel_active_short_interval, lock
        )

        self.cancel_interval: int = 2
        self.timer_count: int = 0
        # print('%s interval:%s' % (self.algoid, self.interval))
        # print('%s cancel_active_short_interval:%s' % (self.algoid, self.cancel_active_short_interval))
    def on_tick(self, tick: TickData):
        """"""
        # Return if tick not inited
        if not self.spread.bid_volume or not self.spread.ask_volume:
            return

        # Return if there are any existing orders
        if not self.check_order_finished():
            return

        # Hedge if active leg is not fully hedged
        if not self.check_hedge_finished():
            self.hedge_passive_legs()
            return

        # Otherwise check if should take active leg
        if self.direction == Direction.LONG:
            if self.spread.ask_price <= self.price:
                self.take_active_leg()
                print(f'spread.ask_price:{self.spread.ask_price}, activeleg.ask_price:{self.spread.active_leg.ask_price}, passiveleg.bid_price:{self.spread.passive_legs[0].bid_price}')
        else:
            if self.spread.bid_price >= self.price:
                self.take_active_leg()
                print(f'spread.bid_price:{self.spread.bid_price}, activeleg.bid_price:{self.spread.active_leg.bid_price}, passiveleg.ask_price:{self.spread.passive_legs[0].ask_price}')

    def on_order(self, order: OrderData):
        """"""
        # Only care active leg order update
        if order.vt_symbol != self.spread.active_leg.vt_symbol:
            return
        # print('got active_leg on_order')
        # Do nothing if still any existing orders
        if not self.check_order_finished():
            return
        print("check_order_finished pass")
        # Hedge passive legs if necessary
        if not self.check_hedge_finished():
            self.hedge_passive_legs()

    def on_trade(self, trade: TradeData):
        """"""
        pass

    # def on_interval(self):
    #     """"""
    #     if not self.check_order_finished():
    #         self.cancel_all_order()
    #         print("algo on_interval cancel_all_order!!!")

    def take_active_leg(self):
        """"""
        # Calculate spread order volume of new round trade
        spread_volume_left = self.target - self.traded

        if self.direction == Direction.LONG:
            spread_order_volume = max(self.spread.ask_volume, self.lot_size)
            spread_order_volume = min(spread_order_volume, spread_volume_left)
        else:
            spread_order_volume = min(-self.spread.bid_volume, -self.lot_size)
            spread_order_volume = max(spread_order_volume, spread_volume_left)

        # Calculate active leg order volume
        leg_order_volume = self.spread.calculate_leg_volume(
            self.spread.active_leg.vt_symbol,
            spread_order_volume
        )

        # Send active leg order
        self.send_leg_order(
            self.spread.active_leg.vt_symbol,
            leg_order_volume
        )

    def hedge_passive_legs(self):
        """
        Send orders to hedge all passive legs.
        """
        # Calcualte spread volume to hedge
        active_leg = self.spread.active_leg
        active_traded = self.leg_traded[active_leg.vt_symbol]
        active_traded = round_to(active_traded, self.spread.min_volume)
        print("algo hedge_passive_legs, active_traded=%s" % active_traded)

        hedge_volume = self.spread.calculate_spread_volume(
            active_leg.vt_symbol,
            active_traded
        )

        # Calculate passive leg target volume and do hedge
        for leg in self.spread.passive_legs:
            passive_traded = self.leg_traded[leg.vt_symbol]
            passive_traded = round_to(passive_traded, self.spread.min_volume)

            passive_target = self.spread.calculate_leg_volume(
                leg.vt_symbol,
                hedge_volume
            )

            leg_order_volume = passive_target - passive_traded
            if leg_order_volume:
                self.send_leg_order(leg.vt_symbol, leg_order_volume)

    def send_leg_order(self, vt_symbol: str, leg_volume: float):
        """"""
        leg = self.spread.legs[vt_symbol]
        leg_tick = self.get_tick(vt_symbol)
        leg_contract = self.get_contract(vt_symbol)

        if leg_volume > 0:
            if vt_symbol == self.spread.active_leg.vt_symbol:
                price = round_to(leg_tick.ask_price_1 + leg_contract.pricetick * self.payup * 10,leg_contract.pricetick)
            else:
                price = round_to(leg_tick.ask_price_1 + leg_contract.pricetick * self.payup,leg_contract.pricetick)
            self.send_long_order(leg.vt_symbol, price, abs(leg_volume))
        elif leg_volume < 0:
            if vt_symbol == self.spread.active_leg.vt_symbol:
                price = round_to(leg_tick.bid_price_1 - leg_contract.pricetick * self.payup * 10,leg_contract.pricetick) 
            else:
                price = round_to(leg_tick.bid_price_1 - leg_contract.pricetick * self.payup,leg_contract.pricetick)
            self.send_short_order(leg.vt_symbol, price, abs(leg_volume))
        