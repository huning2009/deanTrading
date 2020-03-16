from logging import INFO
from collections import defaultdict
from typing import Dict, List, Set, Callable
from copy import copy

from myObject import TickData, TradeData, OrderData, ContractData, BarData
from myConstant import Direction, Status, Offset, Interval
from myUtility import virtual, floor_to, ceil_to, round_to

from .base import SpreadData, calculate_inverse_volume


class SpreadAlgoTemplate:
    """
    Template for implementing spread trading algos.
    """
    algo_name = "AlgoTemplate"

    def __init__(
        self,
        algo_engine,
        algoid: str,
        spread: SpreadData
    ):
        """"""
        self.algo_engine = algo_engine
        self.algoid: str = algoid
        self.spread: SpreadData = spread

        self.status: Status = Status.NOTTRADED  # Algo status
        self.count: int = 0                     # Timer count for passive(futures) order and active buy/sell/cover order
        self.traded: float = 0                  # Volume traded
        self.traded_volume: float = 0           # Volume traded (Abs value)

        # self.leg_traded: Dict[str, float] = defaultdict(int)
        self.leg_orders: Dict[str, List[str]] = defaultdict(list)

        self.write_log(f"算法已启动,max_pos: {self.spread.max_pos}, buy_price: {self.spread.buy_price}, sell_price: {self.spread.sell_price}, short_price: {self.spread.short_price}, cover_price: {self.spread.cover_price}")

    def check_order_finished(self):
        """"""
        finished = True

        for leg in self.spread.legs.values():
            vt_orderids = self.leg_orders[leg.vt_symbol]
            if vt_orderids:
                finished = False
                break
        # print('algo template check_order_finished:%s : %s' % (leg.vt_symbol, finished))
        return finished

    def check_passive_order_finished(self):
        """"""
        finished = True

        vt_orderids = self.leg_orders[self.spread.passive_leg.vt_symbol]
        if vt_orderids:
            finished = False
            return finished
        # print('algo template check_order_finished:%s : %s' % (leg.vt_symbol, finished))
        return finished

    # def check_hedge_finished(self):
    #     """"""
    #     active_symbol = self.spread.active_leg.vt_symbol
    #     active_traded = self.leg_traded[active_symbol]

    #     spread_volume = self.spread.calculate_spread_volume(
    #         active_symbol, active_traded
    #     )

    #     finished = True

    #     passive_symbol = self.spread.passive_leg.vt_symbol

    #     leg_target = self.spread.calculate_leg_volume(
    #         passive_symbol, spread_volume
    #     )
    #     leg_traded = self.leg_traded[passive_symbol]

    #     if leg_traded != leg_target:
    #         finished = False
    #     # print("check_hedge_finished: %s, passive leg_traded %s" % (finished, leg_traded))
    #     return finished

    def stop(self):
        """"""
        # self.cancel_all_order()
        self.status = Status.CANCELLED
        self.write_log("算法已停止")

    def update_tick(self, tick: TickData):
        """"""
        self.on_tick(tick)

    def update_trade(self, trade: TradeData):
        """"""
        # For inverse contract:
        # record coin trading volume as leg trading volume,
        # not contract volume!
        # if self.spread.is_inverse(trade.vt_symbol):
        #     size = self.spread.get_leg_size(trade.vt_symbol)

        #     trade_volume = calculate_inverse_volume(
        #         trade.volume,
        #         trade.price,
        #         size
        #     )
        # else:
        #     trade_volume = trade.volume

        # if trade.direction == Direction.LONG:
        #     self.leg_traded[trade.vt_symbol] += trade_volume
        # else:
        #     self.leg_traded[trade.vt_symbol] -= trade_volume
        self.on_trade(trade)

        msg = "委托成交，{}，{}，{}@{}".format(
            trade.vt_symbol,
            trade.direction,
            trade.volume,
            trade.price
        )
        self.write_log(msg)

        # self.calculate_traded()


    def update_order(self, order: OrderData):
        """"""
        # print('algo template update_order, order.is_active:%s' % order.is_active())
        if not order.is_active():
            vt_orderids = self.leg_orders[order.vt_symbol]
            if order.vt_orderid in vt_orderids:
                vt_orderids.remove(order.vt_orderid)

            # if order.vt_orderid in self.active_short_orderids:
            #     self.active_short_orderids.remove(order.vt_orderid)
        self.on_order(order)

    def update_timer(self):
        """"""
        # self.count += 1
        # self.count_active_short += 1
        # if self.count > self.interval:
        #     self.count = 0
        #     self.cancel_all_order_but_active_short()

        # if self.count_active_short > self.cancel_active_short_interval:
        #     self.count_active_short = 0
        #     self.cancel_active_short_order()

        # self.put_algo_event()
        pass

    def write_log(self, msg: str, level=INFO):
        """"""
        self.algo_engine.write_algo_log(self, msg, level=level)

    def send_long_order(self, vt_symbol: str, price: float, volume: float):
        """"""
        self.send_order(vt_symbol, price, volume, Direction.LONG)

    def send_short_order(self, vt_symbol: str, price: float, volume: float, borrowmoney=False):
        """"""
        self.send_order(vt_symbol, price, volume, Direction.SHORT, borrowmoney)

    def send_order(
        self,
        vt_symbol: str,
        price: float,
        volume: float,
        direction: Direction,
        borrowmoney=False
    ):
        """"""
        # For inverse contract:
        # calculate contract trading volume from coin trading volume
        if self.spread.is_inverse(vt_symbol):
            size = self.spread.get_leg_size(vt_symbol)
            volume = volume * price / size

        # Round order volume to min_volume of contract
        leg = self.spread.legs[vt_symbol]
        volume = round_to(volume, leg.min_volume)

        vt_orderid = self.algo_engine.send_order(
            self,
            vt_symbol,
            price,
            volume,
            direction,
            borrowmoney
        )

        self.leg_orders[vt_symbol].append(vt_orderid)

        msg = "发出委托，{}，{}，{}@{}".format(
            vt_symbol,
            direction,
            volume,
            price
        )
        self.write_log(msg)

    # def cancel_leg_order(self, vt_symbol: str):
    #     """"""
    #     for vt_orderid in self.leg_orders[vt_symbol]:
    #         self.algo_engine.cancel_order(self, vt_orderid)

    # def cancel_all_order(self):
    #     """"""
    #     for vt_symbol in self.leg_orders.keys():
    #         self.cancel_leg_order(vt_symbol)

    # def cancel_all_order_but_active_short(self):
    #     """"""
    #     for vt_symbol in self.leg_orders.keys():
    #         for vt_orderid in self.leg_orders[vt_symbol]:
    #             if vt_orderid not in self.active_short_orderids:
    #                 self.algo_engine.cancel_order(self, vt_orderid)
    #                 self.write_log("cancel_all_order_but_active_short: %s" % vt_orderid)
    # def cancel_active_short_order(self):
    #     for vt_orderid in self.leg_orders[self.spread.active_leg.vt_symbol]:
    #         if vt_orderid in self.active_short_orderids:
    #             self.algo_engine.cancel_order(self, vt_orderid)
    #             self.write_log("cancel_active_short_order: %s" % vt_orderid)

    # def calculate_traded(self):
    #     """"""
    #     self.traded = 0
    #     # print('algo template calculate_traded>>>>')
    #     for n, leg in enumerate(self.spread.legs.values()):
    #         leg_traded = self.leg_traded[leg.vt_symbol]
    #         trading_multiplier = self.spread.trading_multipliers[
    #             leg.vt_symbol]

    #         adjusted_leg_traded = leg_traded / trading_multiplier
    #         adjusted_leg_traded = round_to(
    #             adjusted_leg_traded, self.spread.min_volume)

    #         if adjusted_leg_traded > 0:
    #             adjusted_leg_traded = floor_to(
    #                 adjusted_leg_traded, self.spread.min_volume)
    #         else:
    #             adjusted_leg_traded = ceil_to(
    #                 adjusted_leg_traded, self.spread.min_volume)

    #         if not n:
    #             self.traded = adjusted_leg_traded
    #         else:
    #             if adjusted_leg_traded > 0:
    #                 self.traded = min(self.traded, adjusted_leg_traded)
    #             elif adjusted_leg_traded < 0:
    #                 self.traded = max(self.traded, adjusted_leg_traded)
    #             else:
    #                 self.traded = 0

    #     self.traded_volume = abs(self.traded)

    #     if self.traded_volume == self.spread.max_pos:
    #         self.status = Status.ALLTRADED
    #         print("algo calculate_traded: %s status is ALLTRADE" % self.algoid)
    #     elif not self.traded_volume:
    #         self.status = Status.NOTTRADED
    #         print("algo calculate_traded: %s status is NOTTRADED" % self.algoid)
    #     else:
    #         self.status = Status.PARTTRADED
    #         print("algo calculate_traded: %s status is PARTTRADED" % self.algoid)

    def get_contract(self, vt_symbol: str) -> ContractData:
        """"""
        return self.algo_engine.get_contract(vt_symbol)

    def borrow_money(self):
        pass

    @virtual
    def on_tick(self, tick: TickData):
        """"""
        pass

    @virtual
    def on_order(self, order: OrderData):
        """"""
        pass

    @virtual
    def on_trade(self, trade: TradeData):
        """"""
        pass

    @virtual
    def on_interval(self):
        """"""
        pass


