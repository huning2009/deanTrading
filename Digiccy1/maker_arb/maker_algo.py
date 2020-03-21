from logging import DEBUG
from typing import Any
from datetime import datetime
import numpy as np
import pandas as pd

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

        self.my_bestbid = 0.0
        self.my_bestask = 0.0


    def on_tick(self, tick: TickData):
        """"""
        # 首先判断是否有敞口，有则对冲
        self.hedge_passive_leg()

        if abs(self.spread.net_pos) < self.pos_threshold:
            # 无持仓
            shadow_bids = self.cal_shadow_buybook()
            bestbid = self.cal_active_bestbid()
            shadow_asks = self.cal_shadow_shortbook()
            bestask = self.cal_active_bestask()

            self.long_active_leg(shadow_bids, bestbid)
            
            self.short_active_leg(shadow_asks, bestask)

        elif self.spread.net_pos > self.pos_threshold and (self.spread.net_pos + self.pos_threshold) < self.spread.max_pos:
            # 持有active 多单，passive空单。不到最大单量，买开同时卖平
            shadow_bids = self.cal_shadow_buybook()
            bestbid = self.cal_active_bestbid()
            shadow_asks = self.cal_shadow_sellbook()
            bestask = self.cal_active_bestask()

            self.long_active_leg(shadow_bids, bestbid)
            
            self.short_active_leg(shadow_asks, bestask)

        elif (self.spread.net_pos + self.pos_threshold) > self.spread.max_pos:
            # 持有active 多单，passive空单。已到最大单量，仅卖平
            shadow_asks = self.cal_shadow_sellbook()
            bestask = self.cal_active_bestask()

            self.short_active_leg(shadow_asks, bestask)

        elif self.spread.net_pos < self.pos_threshold and (self.spread.net_pos - self.pos_threshold) > -self.spread.max_pos:
            # 持有active 空单，passive多单。不到最大单量，卖开同时买平
            shadow_bids = self.cal_shadow_coverbook()
            bestbid = self.cal_active_bestbid()
            shadow_asks = self.cal_shadow_shortbook()
            bestask = self.cal_active_bestask()

            self.long_active_leg(shadow_bids, bestbid)
            
            self.short_active_leg(shadow_asks, bestask)

        elif (self.spread.net_pos - self.pos_threshold) < -self.spread.max_pos:
            # 持有active 空单，passive多单。已到最大单量，仅买平
            shadow_bids = self.cal_shadow_coverbook()
            bestbid = self.cal_active_bestbid()

            self.long_active_leg(shadow_bids, bestbid)
        
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
        my_bid_order_df = self.leg_orders_df[(self.leg_orders_df['vt_symbol']==self.active_leg.vt_symbol) & (self.leg_orders_df['direction']==Direction.LONG)]
        # for index in my_bid_order_df.index:
        #     bids[bids[:0] - my_bid_order_df.loc[index, 'order_price'] < self.active_leg.pricetick * 0.5][:,1] -= my_bid_order_df.loc[index, 'order_vol']
        my_bid_order_df.apply(lambda x: bids[bids[:,0] - x['order_price'] < self.active_leg.pricetick * 0.5][:,1] -= x['order_vol'], axis=1)
        bids[bids[:,1] < 0][:,1] = 0

        bids[:,1] = np.cumsum(bids[:,1]) < self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)
        n = sum(bids[:,1])
        active_bid1 = bids[n,0]

        return active_bid1

    def cal_active_bestask(self):
        """"""
        asks = self.active_leg.asks
        # 去掉自己挂单
        my_ask_order_df = self.leg_orders_df[(self.leg_orders_df['vt_symbol']==self.active_leg.vt_symbol) & (self.leg_orders_df['direction']==Direction.SHORT)]
        # for index in my_ask_order_df.index:
        #     asks[asks[:,0] - my_ask_order_df.loc[index, 'order_price'] < self.active_leg.pricetick * 0.5][:,1] -= my_ask_order_df.loc[index, 'order_vol']
        my_ask_order_df.apply(lambda x: asks[asks[:,0] - x['order_price'] < self.active_leg.pricetick * 0.5][:,1] -= x['order_vol'], axis=1)
        asks[asks[:,1] < 0][:,1] = 0

        asks[:,1] = np.cumsum(asks[:,1]) < self.spread.calculate_leg_volume(self.active_leg.vt_symbol, self.spread.max_pos * 0.1)
        n = sum(asks[:,1])
        active_ask1 = asks[n,0]

        return active_ask1

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

    def long_active_leg(self, shadow_bids, bestbid):
        # 先取消买委托价格高于影子盘口的买委托
        self.leg_orders_df[(self.leg_orders_df['direction']==Direction.LONG) & (self.leg_orders_df['order_price'] > shadow_bids[0,0])].index.map(self.cancel_order)

        # 如果影子盘口小于最优报价，则不发单;反之则发出委托
        if shadow_bids[0,0] > bestbid:
            pass

    def short_active_leg(self, shadow_asks, bestask):
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
        