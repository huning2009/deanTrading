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
    SELL_BUY_RATIO = 2
    COMMISSION = (0.0015 + 0.0005) * 2

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
        if (self.active_leg.bids is None) or (self.passive_leg.bids is None):
            # 初始化
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_buybids = self.cal_shadow_buybook()
                self.shadow_shortasks = self.cal_shadow_shortbook()
            return
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

            self.long_active_leg(self.shadow_buybids, self.active_bestbid, self.spread.max_pos)
            self.short_active_leg(self.shadow_shortasks, self.active_bestask, self.spread.max_pos * self.SELL_BUY_RATIO)

        elif self.spread.net_pos > self.pos_threshold and (self.spread.net_pos + self.pos_threshold) < self.spread.max_pos:
            # 持有active 多单，passive空单。不到最大单量，买开同时卖平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_buybids = self.cal_shadow_buybook()
                self.shadow_sellasks = self.cal_shadow_sellbook()

            self.long_active_leg(self.shadow_buybids, self.active_bestbid, self.spread.max_pos - self.spread.net_pos)
            self.short_active_leg(self.shadow_sellasks, self.active_bestask, self.spread.net_pos)

        elif (self.spread.net_pos + self.pos_threshold) > self.spread.max_pos:
            # 持有active 多单，passive空单。已到最大单量，仅卖平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                if self.shadow_sellasks is not None:
                    self.active_bestask = self.cal_active_bestask()
                else:
                    self.active_bestask = self.cal_active_bestask()
                    self.shadow_sellasks = self.cal_shadow_sellbook()
            else:
                if self.active_bestask is not None:
                    self.shadow_sellasks = self.cal_shadow_sellbook()
                else:
                    self.active_bestask = self.cal_active_bestask()
                    self.shadow_sellasks = self.cal_shadow_sellbook()
                    
            self.short_active_leg(self.shadow_sellasks, self.active_bestask, self.spread.net_pos)

        elif self.spread.net_pos < -self.pos_threshold and (self.spread.net_pos - self.pos_threshold) > -self.spread.max_pos * self.SELL_BUY_RATIO:
            # 持有active 空单，passive多单。不到最大单量，卖开同时买平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
                self.active_bestask = self.cal_active_bestask()
            else:
                self.shadow_coverbids = self.cal_shadow_coverbook()
                self.shadow_shortasks = self.cal_shadow_shortbook()
            
            self.long_active_leg(self.shadow_coverbids, self.active_bestbid, -self.spread.net_pos)
            self.short_active_leg(self.shadow_shortasks, self.active_bestask, self.spread.max_pos * self.SELL_BUY_RATIO + self.spread.net_pos)

        elif (self.spread.net_pos - self.pos_threshold) < -self.spread.max_pos * self.SELL_BUY_RATIO:
            # 持有active 空单，passive多单。已到最大单量，仅买平
            if tick.vt_symbol == self.active_leg.vt_symbol:
                self.active_bestbid = self.cal_active_bestbid()
            else:
                self.shadow_coverbids = self.cal_shadow_coverbook()

            self.long_active_leg(self.shadow_coverbids, self.active_bestbid, -self.spread.net_pos)
        

    # 根据passive的bids asks计算影子盘口
    def cal_shadow_buybook(self):
        """"""
        shadow_bids = self.passive_leg.bids
        shadow_bids[:,0] = shadow_bids[:,0] * (1-self.COMMISSION - self.spread.buy_price) - self.passive_leg.pricetick * self.spread.payup

        return shadow_bids

    def cal_shadow_shortbook(self):
        """"""
        shadow_asks = self.passive_leg.asks
        shadow_asks[:,0] = shadow_asks[:,0] * (1 + self.COMMISSION + self.spread.short_price) + self.passive_leg.pricetick * self.spread.payup

        return shadow_asks

    def cal_shadow_coverbook(self):
        """"""
        shadow_bids = self.passive_leg.bids
        shadow_bids[:,0] = shadow_bids[:,0] * (1-self.COMMISSION - self.spread.cover_price) - self.passive_leg.pricetick * self.spread.payup

        return shadow_bids

    def cal_shadow_sellbook(self):
        """"""
        shadow_asks = self.passive_leg.asks
        shadow_asks[:,0] = shadow_asks[:,0] * (1 + self.COMMISSION + self.spread.sell_price) + self.passive_leg.pricetick * self.spread.payup

        return shadow_asks

    # 根据active bids asks计算最优买卖价
    def cal_active_bestbid(self):
        """"""
        bids = self.active_leg.bids
        # 去掉自己挂单
        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.LONG:
                min_value = min(abs(bids[:,0] - l[1]))
                index_arr = np.where(abs(bids[:,0] - l[1]) == min_value)
                bids[index_arr][0,1] -= l[2]
        bids[:,1][bids[:,1] < 0] = 0
        # 
        bids[:,1] = np.cumsum(bids[:,1], axis=0)
        bids[:,1][bids[:,1] > self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)]=0
        n = np.count_nonzero(bids[:,1])
        bestbid = bids[n,0]
        return bestbid

    def cal_active_bestask(self):
        """"""
        asks = self.active_leg.asks
        # 去掉自己挂单
        for l in self.leg_orders[self.active_leg.vt_symbol]:
            if l[3] == Direction.SHORT:
                min_value = min(abs(asks[:,0] - l[1]))
                index_arr = np.where(abs(asks[:,0] - l[1]) == min_value)
                asks[index_arr][0,1] -= l[2]
        asks[:,1][asks[:,1] < 0] = 0

        asks[:,1] = np.cumsum(asks[:,1], axis=0)
        asks[:,1][asks[:,1] > self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)]=0
        n = np.count_nonzero(asks[:,1])
        bestask = asks[n,0]

        return bestask

    def on_order(self, order: OrderData):
        """"""
        pass

    def on_trade(self, trade: TradeData):
        """"""
         # Only care active leg order update
        if trade.vt_symbol == self.active_leg.vt_symbol:
            # Hedge passive legs if necessary
            self.hedge_passive_leg()
            

    # def on_interval(self):
    #     """"""
    #     if not self.check_order_finished():
    #         self.cancel_all_order()
    #         print("algo on_interval cancel_all_order!!!")

    def long_active_leg(self, shadow_bids, bestbid, vol):
        # 超出报价范围的原委托撤销，否则修改挂单数量
        if bestbid > shadow_bids[0,0]:
            for l in self.leg_orders[self.active_leg.vt_symbol]:
                if l[3] == Direction.LONG:
                    if l[1] > bestbid:
                        if l[0] in self.hanging_orders:
                            self.cancel_order(l[0])
        else:
            # 根据 bestbid 调整shadow_bids
            n = shadow_bids[shadow_bids[:,0] > bestbid].shape[0]
            shadow_bids[:n,1] = np.cumsum(shadow_bids[:n,1], axis=0)
            shadow_bids = shadow_bids[n-1:,:]
            shadow_bids[0,0] = bestbid + self.active_leg.pricetick * 2
            # 根据调整后的shadow_bids计算挂单簿
            cum_bids = np.cumsum(shadow_bids, axis=0)
            cum_bids[:,1][cum_bids[:,1] > vol] = 0
            n = np.count_nonzero(cum_bids[:,1])
            if n == 0:
                order_bids = shadow_bids[0,:].reshape(1,2)
                order_bids[0,1] = vol
            else:
                order_bids = shadow_bids[:n+1,:]
                order_bids[n,1] = vol - cum_bids[n-1,1]
                print(order_bids)

            for l in self.leg_orders[self.active_leg.vt_symbol]:
                if l[3] == Direction.LONG:
                    if (l[1] > order_bids[0,0] or l[1] < order_bids[-1,1]):
                        if l[0] in self.hanging_orders:
                            self.cancel_order(l[0])
                        else:
                            return
                    else:
                        min_value = min(abs(order_bids[:,0] - l[1]))
                        index_arr = np.where(abs(order_bids[:,0] - l[1]) == min_value)      #返回的是tuble
                        if order_bids[index_arr][0,1] < l[2]:
                            if l[0] in self.hanging_orders:
                                self.cancel_order(l[0])
                            else:
                                return
                        else:
                            order_bids[index_arr,1][0,1] -= l[2]

            # 形成最终order_bids，发出报单
            self.send_activeleg_order(order_bids, Direction.LONG)

    def short_active_leg(self, shadow_asks, bestask, vol):
        # 超出报价范围的原委托撤销，否则修改挂单数量
        if bestask < shadow_asks[0,0]:
            for l in self.leg_orders[self.active_leg.vt_symbol]:
                if l[3] == Direction.SHORT:
                    if l[1] < bestask:
                        if l[0] in self.hanging_orders:
                            self.cancel_order(l[0])
        else:
            # 根据 bestbid 调整shadow_bids
            n = shadow_asks[shadow_asks[:,0] < bestask].shape[0]
            shadow_asks[:n,1] = np.cumsum(shadow_asks[:n,1], axis=0)
            shadow_asks = shadow_asks[n-1:,:]
            shadow_asks[0,0] = bestask - self.active_leg.pricetick * 2
            # 根据调整后的shadow_bids计算挂单簿
            cum_asks = np.cumsum(shadow_asks, axis=0)
            cum_asks[:,1][cum_asks[:,1] > vol] = 0
            n = np.count_nonzero(cum_asks[:,1])
            if n == 0:
                order_asks = shadow_asks[0,:].reshape(1,2)
                order_asks[0,1] = vol
            else:
                order_asks = shadow_asks[:n+1,:]
                order_asks[n,1] = vol - cum_asks[n-1,1]

            for l in self.leg_orders[self.active_leg.vt_symbol]:
                if l[3] == Direction.SHORT:
                    if (l[1] > order_asks[0,0] or l[1] < order_asks[-1,1]):
                        if l[0] in self.hanging_orders:
                            self.cancel_order(l[0])
                        else:
                            return
                    else:
                        min_value = min(abs(order_asks[:,0] - l[1]))
                        index_arr = np.where(abs(order_asks[:,0] - l[1]) == min_value)      #返回的是tuble
                        if order_asks[index_arr,1][0,1] < l[2]:
                            if l[0] in self.hanging_orders:
                                self.cancel_order(l[0])             #或者修改原挂单，并更新委托量为0
                            else:
                                return
                        else:
                            order_asks[index_arr,1][0,1] -= l[2]

            # 形成最终order_bids，发出报单
            self.send_activeleg_order(order_asks, Direction.SHORT)
    
    def send_activeleg_order(self, order_arr, direction):
        """"""
        if direction == Direction.LONG:
            for row in order_arr:
                price = round_to(row[0], self.active_leg.pricetick)
                if row[1] * row[0] > 12:
                    self.send_long_order(self.active_leg.vt_symbol, price, row[1])
        else:
            # 检查是否需要借款
            sum_short_vol = order_arr[:,1].sum()
            if sum_short_vol > self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free:
                self.borrow_money(sum_short_vol - self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free)
                self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free = sum_short_vol

            for row in order_arr:
                price = round_to(row[0], self.active_leg.pricetick)
                if row[1] * row[0] > 12:
                    self.send_short_order(self.active_leg.vt_symbol, price, row[1])

    def hedge_passive_leg(self):
        """
        Send orders to hedge all passive legs.
        """
        #  是否有被动腿对冲单挂单，有则不再进行对冲
        if not self.check_passive_order_finished():
            return
        active_traded = round_to(self.active_leg.net_pos, self.spread.min_volume)

        hedge_volume = self.spread.calculate_spread_volume(
            self.active_leg.vt_symbol,
            active_traded
        )

        # Calculate passive leg target volume and do hedge
        # passive_traded = self.leg_traded[self.passive_leg.vt_symbol]
        passive_traded = round_to(self.passive_leg.net_pos, self.spread.min_volume)

        passive_target = self.spread.calculate_leg_volume(
            self.passive_leg.vt_symbol,
            hedge_volume
        )
        self.write_log(f'hedge_passive_leg active_traded: {active_traded}, passive_target: {passive_target}, passive_traded: {passive_traded}')
        leg_order_volume = passive_target - passive_traded
        if abs(leg_order_volume) * self.passive_leg.bids[0,0] > 12:
            self.send_passiveleg_order(leg_order_volume)
            return False

        return True

    def send_passiveleg_order(self, leg_volume: float, borrowmoney = False):
        """"""

        if leg_volume > 0:
            price = round_to(self.passive_leg.asks[0,0] + self.passive_leg.pricetick * self.spread.payup,self.passive_leg.pricetick)
            self.send_long_order(self.passive_leg.vt_symbol, price, leg_volume)
        elif leg_volume < 0:
            price = round_to(self.spread.passive_leg.bids[0,0] - self.passive_leg.pricetick * self.spread.payup,self.passive_leg.pricetick)
            self.send_short_order(self.passive_leg.vt_symbol, price, abs(leg_volume))
