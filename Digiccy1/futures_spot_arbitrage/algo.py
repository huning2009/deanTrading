from typing import Any
from datetime import datetime

from myConstant import Direction, Offset
from myObject import (TickData, OrderData, TradeData)
from myUtility import round_to

from .template import SpreadAlgoTemplate
from .base import SpreadData


class SpreadTakerAlgo(SpreadAlgoTemplate):
    """"""
    algo_name = "SpreadTaker"
    SPREAD_LONG = 1
    SPREAD_SHORT = 2

    def __init__(
        self,
        algo_engine: Any,
        algoid: str,
        spread: SpreadData):
        """"""
        super().__init__(algo_engine, algoid, spread)
        self.interval = 1800
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
        check_hedge_finished = self.hedge_passive_leg()
        if not check_hedge_finished:
            return

        # Otherwise check if should take active leg
        if (self.spread.net_pos >= 0 and
            self.spread.net_pos < self.spread.max_pos and
            self.spread.ask_price <= self.spread.buy_price):
            """买入开仓"""
            self.take_active_leg(self.SPREAD_LONG)
            self.write_log(f'ACTIVE LONG>>>spread.ask_price:{self.spread.ask_price}, activeleg.ask_price:{self.spread.active_leg.ask_price}, passiveleg.bid_price:{self.spread.passive_leg.bid_price}, tick datetime: {self.spread.active_leg.tick.datetime}, send order:{datetime.now()}, event_engine size:{self.algo_engine.event_engine.get_qsize()}')
        elif (self.spread.net_pos > 0 and
            self.spread.bid_price >= self.spread.sell_price):
            """卖出平仓"""
            self.take_active_leg(self.SPREAD_SHORT)
            self.write_log(f'ACTIVE SELL>>>spread.ask_price:{self.spread.ask_price}, activeleg.ask_price:{self.spread.active_leg.ask_price}, passiveleg.bid_price:{self.spread.passive_leg.bid_price}, tick datetime: {self.spread.active_leg.tick.datetime}, send order:{datetime.now()}, event_engine size:{self.algo_engine.event_engine.get_qsize()}')
        elif (self.spread.net_pos <= 0 and
            self.spread.net_pos > -self.spread.max_pos*4 and
            self.spread.bid_price >= self.spread.short_price):
            """卖出开仓"""
            self.take_active_leg(self.SPREAD_SHORT)
            self.write_log(f'ACTIVE SHORT>>>spread.ask_price:{self.spread.ask_price}, activeleg.ask_price:{self.spread.active_leg.ask_price}, passiveleg.bid_price:{self.spread.passive_leg.bid_price}, tick datetime: {self.spread.active_leg.tick.datetime}, send order:{datetime.now()}, event_engine size:{self.algo_engine.event_engine.get_qsize()}')
        elif (self.spread.net_pos < 0 and
            self.spread.ask_price < self.spread.cover_price):
            """买入平仓"""
            self.take_active_leg(self.SPREAD_LONG)
            self.write_log(f'ACTIVE COVER>>>spread.ask_price:{self.spread.ask_price}, activeleg.ask_price:{self.spread.active_leg.ask_price}, passiveleg.bid_price:{self.spread.passive_leg.bid_price}, tick datetime: {self.spread.active_leg.tick.datetime}, send order:{datetime.now()}, event_engine size:{self.algo_engine.event_engine.get_qsize()}')

    def on_order(self, order: OrderData):
        """"""
        pass

    def on_trade(self, trade: TradeData):
        """"""
         # Only care active leg order update
        if trade.vt_symbol == self.spread.active_leg.vt_symbol:
            if not self.check_passive_order_finished():
                return
            # Hedge passive legs if necessary
            self.hedge_passive_leg()
            

    # def on_interval(self):
    #     """"""
    #     if not self.check_order_finished():
    #         self.cancel_all_order()
    #         print("algo on_interval cancel_all_order!!!")

    def take_active_leg(self, direction):
        """"""
        # Calculate spread order volume of new round trade
        borrowmoney = False
        if direction == self.SPREAD_LONG:
            if self.spread.net_pos < 0:
                spread_volume_left = self.spread.net_pos
                spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                spread_order_volume = min(-spread_volume_left, spread_order_volume)
            else:
                spread_volume_left = self.spread.max_pos - self.spread.net_pos
                spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                spread_order_volume = min(spread_order_volume, spread_volume_left)
        else:
            if self.spread.net_pos > 0:
                spread_volume_left = self.spread.net_pos
                spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                spread_order_volume = -min(spread_volume_left, spread_order_volume)
            else:
                # 裸卖空，自动借款，且借全款
                spread_volume_left = self.spread.max_pos*4 + self.spread.net_pos
                if abs(spread_volume_left) > self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free:
                    borrowmoney = True
                    spread_order_volume = spread_volume_left
                    self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free = spread_order_volume
                else:
                    spread_order_volume = max(self.spread.bid_volume, self.spread.lot_size)
                    spread_order_volume = -min(spread_order_volume, spread_volume_left)


        # Calculate active leg order volume
        leg_order_volume = self.spread.calculate_leg_volume(
            self.spread.active_leg.vt_symbol,
            spread_order_volume
        )

        # Send active leg order
        self.send_leg_order(
            self.spread.active_leg.vt_symbol,
            leg_order_volume,
            borrowmoney
        )

    def hedge_passive_leg(self):
        """
        Send orders to hedge all passive legs.
        """
        # Calcualte spread volume to hedge
        # active_leg = self.spread.active_leg
        # active_traded = self.leg_traded[active_leg.vt_symbol]
        active_traded = round_to(self.spread.active_leg.net_pos, self.spread.min_volume)

        hedge_volume = self.spread.calculate_spread_volume(
            self.spread.active_leg.vt_symbol,
            active_traded
        )

        # Calculate passive leg target volume and do hedge
        # passive_traded = self.leg_traded[self.spread.passive_leg.vt_symbol]
        passive_traded = round_to(self.spread.passive_leg.net_pos, self.spread.min_volume)

        passive_target = self.spread.calculate_leg_volume(
            self.spread.passive_leg.vt_symbol,
            hedge_volume
        )

        leg_order_volume = passive_target - passive_traded
        if leg_order_volume:
            self.send_leg_order(self.spread.passive_leg.vt_symbol, leg_order_volume)
            self.write_log(f'HEDGE PASSIVE LEG>>>spread.bid_price:{self.spread.bid_price}, activeleg.bid_price:{self.spread.active_leg.bid_price}, passiveleg.ask_price:{self.spread.passive_leg.ask_price}, send order:{datetime.now()}, tick datetime: {self.spread.active_leg.tick.datetime}, event_engine size:{self.algo_engine.event_engine.get_qsize()}. active_traded: {active_traded}, passive_traded: {passive_traded}, passive_target: {passive_target}')
            return False

        return True


    def send_leg_order(self, vt_symbol: str, leg_volume: float, borrowmoney = False):
        """"""
        leg = self.spread.legs[vt_symbol]
        leg_contract = self.get_contract(vt_symbol)
        # check min notion
        if abs(leg_volume) * leg.last_price <12:
            return

        if leg_volume > 0:
            if vt_symbol == self.spread.active_leg.vt_symbol:
                price = round_to(self.spread.active_leg.ask_price + leg_contract.pricetick * self.spread.payup * 10,leg_contract.pricetick)
            else:
                price = round_to(self.spread.passive_leg.ask_price + leg_contract.pricetick * self.spread.payup,leg_contract.pricetick)
            self.send_long_order(leg.vt_symbol, price, abs(leg_volume))
        elif leg_volume < 0:
            if vt_symbol == self.spread.active_leg.vt_symbol:
                # print(self.algo_engine.spread_engine.data_engine.margin_accounts)
                price = round_to(self.spread.active_leg.bid_price - leg_contract.pricetick * self.spread.payup * 10,leg_contract.pricetick) 
            else:
                price = round_to(self.spread.passive_leg.bid_price - leg_contract.pricetick * self.spread.payup,leg_contract.pricetick)
            self.send_short_order(leg.vt_symbol, price, abs(leg_volume), borrowmoney)
        