from logging import DEBUG
from typing import Any
from datetime import datetime
import numpy as np

from myConstant import Direction, Offset
from myObject import (TickData, OrderData, TradeData)
from myUtility import round_to

from .template import SpreadAlgoTemplate
from .base import SpreadData

class SpreadMakerAlgo(SpreadAlgoTemplate):
    """"""
    algo_name = "SpreadMaker"
    SPREAD_LONG = 1
    SPREAD_SHORT = 2
    SELL_BUY_RATIO = 2
    COMMISSION = (0.0015 + 0.0005) * 2
    PAYUP = 2

    def __init__(
        self,
        algo_engine: Any,
        algoid: str,
        spread: SpreadData):
        """"""
        super().__init__(algo_engine, algoid, spread)

        self.active_leg = self.spread.active_leg
        self.passive_leg = self.spread.passive_leg
        self.pos_threshold = self.spread.max_pos * 0.001

        self.my_bestbid = None
        self.my_bestask = None

        self.active_bestbid = None
        self.active_bestask = None
        self.shadow_buybids = None
        self.shadow_sellasks = None
        self.shadow_shortasks = None
        self.shadow_coverbids = None


    def on_tick(self, tick: TickData):
        """"""
        # 首先判断是否有敞口，有则对冲
        self.hedge_passive_leg()

        if abs(self.spread.net_pos) < self.pos_threshold:
            # 无持仓
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_buybids = self.cal_shadow_buybook()
                self.shadow_shortasks = self.cal_shadow_shortbook()

            buy_vol = self.spread.max_pos
            short_vol = -self.spread.max_pos

            self.long_active_leg(self.shadow_buybids, self.active_bestbid, buy_vol)
            self.short_active_leg(self.shadow_shortasks, self.active_bestask, short_vol)

        elif self.spread.net_pos > self.pos_threshold and (self.spread.net_pos + self.pos_threshold) < self.spread.max_pos:
            # 持有active 多单，passive空单。不到最大单量，买开同时卖平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_buybids = self.cal_shadow_buybook()
                self.shadow_sellasks = self.cal_shadow_sellbook()

            buy_vol = self.spread.max_pos - self.spread.net_pos
            sell_vol = -self.spread.net_pos

            self.long_active_leg(self.shadow_buybids, self.active_bestbid, buy_vol)
            self.short_active_leg(self.shadow_sellasks, self.active_bestask, sell_vol)

        elif (self.spread.net_pos + self.pos_threshold) > self.spread.max_pos:
            # 持有active 多单，passive空单。已到最大单量，仅卖平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_sellasks = self.cal_shadow_sellbook()

            sell_vol = -self.spread.net_pos
            self.short_active_leg(self.shadow_sellasks, self.active_bestask, sell_vol)

        elif self.spread.net_pos < self.pos_threshold and (self.spread.net_pos - self.pos_threshold) > -self.spread.max_pos:
            # 持有active 空单，passive多单。不到最大单量，卖开同时买平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_coverbids = self.cal_shadow_coverbook()
                self.shadow_shortasks = self.cal_shadow_shortbook()
            
            cover_vol = -self.spread.net_pos
            short_vol = -self.spread.max_pos + self.spread.net_pos

            self.long_active_leg(self.shadow_coverbids, self.active_bestbid, cover_vol)
            self.short_active_leg(self.shadow_shortasks, self.active_bestask, short_vol)

        elif (self.spread.net_pos - self.pos_threshold) < -self.spread.max_pos:
            # 持有active 空单，passive多单。已到最大单量，仅买平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
            else:
                self.shadow_coverbids = self.cal_shadow_coverbook()

            cover_vol = -self.spread.net_pos

            self.long_active_leg(self.shadow_coverbids, self.active_bestbid, cover_vol)
        
        # 订单制定完毕，合并统一发单

    # 根据passive的bids asks计算影子盘口
    def cal_shadow_buybook(self):
        """"""
        shadow_bids = self.passive_leg.bids
        shadow_bids[:,0] = shadow_bids[:,0] * (1-self.COMMISSION - self.spread.buy_price) - self.passive_leg.pricetick * self.PAYUP

        return shadow_bids

    def cal_shadow_shortbook(self):
        """"""
        shadow_asks = self.passive_leg.asks
        shadow_asks[:,0] = shadow_asks[:,0] * (1 + self.COMMISSION + self.spread.short_price) + self.passive_leg.pricetick * self.PAYUP

        return shadow_asks

    def cal_shadow_coverbook(self):
        """"""
        shadow_bids = self.passive_leg.bids
        shadow_bids[:,0] = shadow_bids[:,0] * (1-self.COMMISSION - self.spread.cover_price) - self.passive_leg.pricetick * self.PAYUP

        return shadow_bids

    def cal_shadow_sellbook(self):
        """"""
        shadow_asks = self.passive_leg.asks
        shadow_asks[:,0] = shadow_asks[:,0] * (1 + self.COMMISSION + self.spread.sell_price) + self.passive_leg.pricetick * self.PAYUP

        return shadow_asks

    # 根据active bids asks计算最优买卖价
    def cal_active_bestbid(self):
        """"""
        bids = self.active_leg.bids
        # 去掉自己挂单
        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.LONG:
                bids[bids[:,0] - l[1] < self.active_leg.pricetick * 0.5][:,1] -= l[2]
        bids[bids[:,1] < 0][:,1] = 0

        bids[:,1] = np.cumsum(bids[:,1]) < self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)
        n = sum(bids[:,1])
        bestbid = bids[n,0]

        return bestbid

    def cal_active_bestask(self):
        """"""
        asks = self.active_leg.asks
        # 去掉自己挂单
        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.SHORT:
                asks[asks[:,0] - l[1] < self.active_leg.pricetick * 0.5][:,1] -= l[2]
        asks[asks[:,1] < 0][:,1] = 0

        asks[:,1] = np.cumsum(asks[:,1]) < self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)
        n = sum(asks[:,1])
        bestask = asks[n,0]

        return bestask

    def on_order(self, order: OrderData):
        """"""
        pass

    def on_trade(self, trade: TradeData):
        """"""
         # Only care active leg order update
        if trade.vt_symbol == self.spread.active_leg.vt_symbol:
            # Hedge passive legs if necessary
            self.hedge_passive_leg()
            

    # def on_interval(self):
    #     """"""
    #     if not self.check_order_finished():
    #         self.cancel_all_order()
    #         print("algo on_interval cancel_all_order!!!")

    def long_active_leg(self, shadow_bids, bestbid, vol):
        # 超出报价范围的原委托撤销，否则修改挂单数量
        cum_bids = np.cumsum(shadow_bids)
        cum_bids[cum_bids[:,1] > vol][:,1] = 0
        n = np.count_nonzero(cum_bids[:,1])
        if n == 0:
            order_bids = shadow_bids[0,:]
            order_bids[0,1] = vol
        else:
            order_bids = shadow_bids[:n,:]
            order_bids[n,1] = vol - cum_bids[n-1,1]

        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.LONG:
                if (l[1] > order_bids[0,0] or l[1] < order_bids[-1,1]):
                    self.cancel_order(l[0])
                else:
                    min_value = min(abs(order_bids[:,0] - l[1]))
                    index_arr = np.where(abs(order_bids[:,0] - l[1]) == min_value)      #返回的是tuble
                    if order_bids[index_arr,1][0,1] < l[2]:
                        self.cancel_order(l[0])
                    else:
                        order_bids[index_arr,1][0,1] -= l[2]

        # 形成最终order_bids，发出报单
        pass
    def short_active_leg(self, shadow_asks, bestask, vol):
        # 超出报价范围的原委托撤销，否则修改挂单数量
        vol = -vol
        cum_asks = np.cumsum(shadow_asks)
        cum_asks[cum_asks[:,1] > vol][:,1] = 0
        n = np.count_nonzero(cum_asks[:,1])
        if n == 0:
            order_asks = shadow_asks[0,:]
            order_asks[0,1] = vol
        else:
            order_asks = shadow_asks[:n,:]
            order_asks[n,1] = vol - cum_asks[n-1,1]

        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.SHORT:
                if (l[1] > order_asks[0,0] or l[1] < order_asks[-1,1]):
                    self.cancel_order(l[0])
                else:
                    min_value = min(abs(order_asks[:,0] - l[1]))
                    index_arr = np.where(abs(order_asks[:,0] - l[1]) == min_value)      #返回的是tuble
                    if order_asks[index_arr,1][0,1] < l[2]:
                        self.cancel_order(l[0])             #或者修改原挂单，并新委托量变为0
                    else:
                        order_asks[index_arr,1][0,1] -= l[2]

        # 形成最终order_bids，发出报单
        pass
    
    def take_active_leg(self, direction):
        """"""
        # Calculate spread order volume of new round trade
        borrowmoney = False
        if direction == self.SPREAD_LONG:
            if self.spread.net_pos < 0:
                spread_order_volume = -self.spread.net_pos
                # spread_volume_left = self.spread.net_pos
                # spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                # spread_order_volume = min(-spread_volume_left, spread_order_volume)
            else:
                spread_order_volume = self.spread.max_pos - self.spread.net_pos
                # spread_volume_left = self.spread.max_pos - self.spread.net_pos
                # spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                # spread_order_volume = min(spread_order_volume, spread_volume_left)
        else:
            if self.spread.net_pos > 0:
                if self.spread.net_pos > self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free:
                    borrowmoney = True
                    self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free = self.spread.net_pos
                spread_order_volume = -self.spread.net_pos
                # spread_volume_left = self.spread.net_pos
                # spread_order_volume = max(self.spread.ask_volume, self.spread.lot_size)
                # spread_order_volume = -min(spread_volume_left, spread_order_volume)
            else:
                # 裸卖空，自动借款，且借全款
                spread_volume_left = self.spread.max_pos*self.SELL_BUY_RATIO + self.spread.net_pos
                if spread_volume_left > self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free:
                    borrowmoney = True
                    spread_order_volume = min(spread_volume_left, self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].max_borrow * 0.9)
                    if spread_order_volume < self.spread.lot_size:
                        return
                    self.algo_engine.spread_engine.data_engine.margin_accounts[self.spread.active_leg.vt_symbol].free = spread_order_volume
                    spread_order_volume = -spread_order_volume
                else:
                    # spread_order_volume = max(self.spread.bid_volume, self.spread.lot_size)
                    # spread_order_volume = -min(spread_order_volume, spread_volume_left)
                    spread_order_volume = -spread_volume_left


        # Calculate active leg order volume
        leg_order_volume = self.spread.calculate_leg_volume(
            self.spread.active_leg.vt_symbol,
            spread_order_volume
        )
        if abs(leg_order_volume) * self.spread.active_leg.last_price > 12:
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
        #  是否有被动腿对冲单挂单，有则不再进行对冲
        if not self.check_passive_order_finished():
            return
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
        if abs(leg_order_volume) * self.spread.passive_leg.last_price > 12:
            self.send_passiveleg_order(self.spread.passive_leg.vt_symbol, leg_order_volume)
            # self.write_log(f'HEDGE PASSIVE LEG>>>spread.bid_price:{self.spread.bid_price}, activeleg.bid_price:{self.spread.active_leg.bid_price}, passiveleg.ask_price:{self.spread.passive_leg.ask_price}, send order:{datetime.now()}, tick datetime: {self.spread.active_leg.tick.datetime}, event_engine size:{self.algo_engine.event_engine.get_qsize()}. active_traded: {active_traded}, passive_traded: {passive_traded}, passive_target: {passive_target}')
            return False

        return True


    def send_passiveleg_order(self, vt_symbol: str, leg_volume: float, borrowmoney = False):
        """"""
        leg = self.spread.legs[vt_symbol]
        leg_contract = self.get_contract(vt_symbol)

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

    def send_activeleg_order(self, vt_symbol: str, leg_volume: float, borrowmoney = False):
        """"""
        leg = self.spread.legs[vt_symbol]
        leg_contract = self.get_contract(vt_symbol)

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
        