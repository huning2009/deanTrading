from logging import DEBUG
from typing import Any
from datetime import datetime
import numpy as np
import copy

from myConstant import Direction, Offset, Status
from myObject import (TickData, OrderData, TradeData)
from myUtility import round_to

from .template import SpreadAlgoTemplate
from .base import SpreadData

class SpreadMakerAlgo(SpreadAlgoTemplate):
    """"""
    algo_name = "SpreadMaker"
    SELL_BUY_RATIO = 2
    FILT_RATIO = 0.6
    COMMISSION = 0.0008 + 0.0004

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
        self.max_pos = self.spread.max_pos
        self.payup = self.spread.payup

        self.submitting_long_dict = {}   # key: orderid (None or orderid), status, price, vol, traded
        self.submitting_long_dict['order_id'] = None
        self.submitting_short_dict = {}
        self.submitting_short_dict['order_id'] = None

        self.cancel_long_orderid = None
        self.cancel_short_orderid = None

    def on_tick(self, tick=None):
        """"""
        if (self.active_leg.bids is None) or (self.passive_leg.bids is None):
            return
        # 首先判断是否有敞口，有则对冲
        self.hedge_passive_leg()

        if abs(self.spread.net_pos) < self.pos_threshold:
            # 无持仓
            long_vol = self.max_pos
            short_vol = self.max_pos * self.SELL_BUY_RATIO

            bestbid = self.cal_active_bestbid(long_vol)
            bestask = self.cal_active_bestask(short_vol)
            shadow_buybid = self.cal_shadow_buybid(long_vol)
            shadow_shortask = self.cal_shadow_shortask(short_vol)

            self.long_active_leg(shadow_buybid, bestbid, long_vol)
            self.short_active_leg(shadow_shortask, bestask, short_vol)

        elif self.spread.net_pos > self.pos_threshold and (self.spread.net_pos + self.pos_threshold) < self.max_pos:
            # 持有active 多单，passive空单。不到最大单量，买开同时卖平
            long_vol = self.max_pos - self.spread.net_pos
            short_vol = self.spread.net_pos

            bestbid = self.cal_active_bestbid(long_vol)
            bestask = self.cal_active_bestask(short_vol)
            shadow_buybid = self.cal_shadow_buybid(long_vol)
            shadow_sellask = self.cal_shadow_sellask(short_vol)

            self.long_active_leg(shadow_buybid, bestbid, long_vol)
            self.short_active_leg(shadow_sellask, bestask, short_vol)

        elif (self.spread.net_pos + self.pos_threshold) > self.max_pos:
            # 持有active 多单，passive空单。已到最大单量，仅卖平
            short_vol = self.spread.net_pos

            bestask = self.cal_active_bestask(short_vol)
            shadow_sellask = self.cal_shadow_sellask(short_vol)
                    
            self.short_active_leg(shadow_sellask, bestask, short_vol)

        elif self.spread.net_pos < -self.pos_threshold and (self.spread.net_pos - self.pos_threshold) > -self.max_pos * self.SELL_BUY_RATIO:
            # 持有active 空单，passive多单。不到最大单量，卖开同时买平
            long_vol = -self.spread.net_pos
            short_vol = self.max_pos * self.SELL_BUY_RATIO + self.spread.net_pos

            bestbid = self.cal_active_bestbid(long_vol)
            bestask = self.cal_active_bestask(short_vol)
            shadow_coverbid = self.cal_shadow_coverbid(long_vol)
            shadow_shortask = self.cal_shadow_shortask(short_vol)
            
            self.long_active_leg(shadow_coverbid, bestbid, long_vol)
            self.short_active_leg(shadow_shortask, bestask, short_vol)

        elif (self.spread.net_pos - self.pos_threshold) < -self.max_pos * self.SELL_BUY_RATIO:
            # 持有active 空单，passive多单。已到最大单量，仅买平
            long_vol = -self.spread.net_pos

            bestbid = self.cal_active_bestbid(long_vol)
            shadow_coverbid = self.cal_shadow_coverbid(long_vol)

            self.long_active_leg(shadow_coverbid, bestbid, long_vol)
        
    # 根据passive的bids asks计算影子盘口
    def cal_shadow_buybid(self, max_vol):
        """"""
        cumshadow_bids = copy.copy(self.passive_leg.bids)
        cumshadow_bids[:,1] = np.cumsum(cumshadow_bids[:,1], axis=0)
        cumshadow_bids[:,1][cumshadow_bids[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_bids[:,1])
        # print(f'n = {n}')
        # print(cumshadow_bids)
        # print(self.passive_leg.bids)
        shadow_buybid = (cumshadow_bids[n,0] - self.passive_leg.pricetick * self.payup) * (1-self.COMMISSION + self.spread.buy_price)

        return shadow_buybid

    def cal_shadow_shortask(self, max_vol):
        """"""
        cumshadow_asks = copy.copy(self.passive_leg.asks)
        cumshadow_asks[:,1] = np.cumsum(cumshadow_asks[:,1], axis=0)
        cumshadow_asks[:,1][cumshadow_asks[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_asks[:,1])
        # print(f'n = {n}')
        # print(cumshadow_asks)
        # print(self.passive_leg.asks)
        shadow_shortask = (cumshadow_asks[n,0] + self.passive_leg.pricetick * self.payup) * (1 + self.COMMISSION + self.spread.short_price)

        return shadow_shortask

    def cal_shadow_coverbid(self, max_vol):
        """"""
        cumshadow_bids = copy.copy(self.passive_leg.bids)
        cumshadow_bids[:,1] = np.cumsum(cumshadow_bids[:,1], axis=0)
        cumshadow_bids[:,1][cumshadow_bids[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_bids[:,1])

        shadow_coverbid = (cumshadow_bids[n,0] - self.passive_leg.pricetick * self.payup) * (1 - self.COMMISSION + self.spread.cover_price)

        return shadow_coverbid

    def cal_shadow_sellask(self, max_vol):
        """"""
        cumshadow_asks = copy.copy(self.passive_leg.asks)
        cumshadow_asks[:,1] = np.cumsum(cumshadow_asks[:,1], axis=0)
        cumshadow_asks[:,1][cumshadow_asks[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_asks[:,1])

        shadow_sellask = (cumshadow_asks[n,0] + self.passive_leg.pricetick * self.payup) * (1 + self.COMMISSION + self.spread.sell_price)

        return shadow_sellask

    # 根据active bids asks计算最优买卖价
    def cal_active_bestbid(self, max_vol):
        """"""
        bids = copy.copy(self.active_leg.bids)
        # 去掉自己挂单
        if self.submitting_long_dict['order_id'] is not None:
            min_value = min(abs(bids[:,0] - self.submitting_long_dict['price']))
            index_arr = np.where(abs(bids[:,0] - self.submitting_long_dict['price']) == min_value)
            bids[index_arr][0,1] -= min(self.submitting_long_dict['vol'], bids[index_arr][0,1])
        # 
        bids[:,1] = np.cumsum(bids[:,1], axis=0)
        bids[:,1][bids[:,1] > max_vol * self.FILT_RATIO] = 0
        n = np.count_nonzero(bids[:,1])
        bestbid = bids[n,0]
        return bestbid

    def cal_active_bestask(self, max_vol):
        """"""
        asks = copy.copy(self.active_leg.asks)
        # 去掉自己挂单
        if self.submitting_short_dict['order_id'] is not None:
            min_value = min(abs(asks[:,0] - self.submitting_short_dict['price']))
            index_arr = np.where(abs(asks[:,0] - self.submitting_short_dict['price']) == min_value)
            asks[index_arr][0,1] -= min(self.submitting_short_dict['vol'], asks[index_arr][0,1])

        asks[:,1] = np.cumsum(asks[:,1], axis=0)
        asks[:,1][asks[:,1] > max_vol * self.FILT_RATIO] = 0
        n = np.count_nonzero(asks[:,1])
        bestask = asks[n,0]

        return bestask

    def on_order(self, order: OrderData):
        """"""
        if order.vt_symbol == self.active_leg.vt_symbol:
            if order.status in [Status.REJECTED, Status.ALLTRADED]:
                self.write_log(f'rejected or alltrade: order id: {order.vt_orderid}, volume: {order.volume}', level=DEBUG)

                if order.vt_orderid == self.submitting_long_dict['order_id']:
                    self.submitting_long_dict['order_id'] = None
                    self.submitting_long_dict['price'] = None
                    self.submitting_long_dict['status'] = None
                    self.submitting_long_dict['vol'] = None
                elif order.vt_orderid == self.submitting_short_dict['order_id']:
                    self.submitting_short_dict['order_id'] = None
                    self.submitting_short_dict['price'] = None
                    self.submitting_short_dict['status'] = None
                    self.submitting_short_dict['vol'] = None

                if order.vt_orderid == self.cancel_long_orderid:
                    self.cancel_long_orderid = None
                elif order.vt_orderid == self.cancel_short_orderid:
                    self.cancel_short_orderid = None

            elif order.status == Status.CANCELLED:
                self.write_log(f'cancel: order id: {order.vt_orderid}, volume: {order.volume}', level=DEBUG)

                if order.vt_orderid == self.submitting_long_dict['order_id']:
                    self.submitting_long_dict['order_id'] = None
                    self.submitting_long_dict['price'] = None
                    self.submitting_long_dict['status'] = None
                    self.submitting_long_dict['vol'] = None
                elif order.vt_orderid == self.submitting_short_dict['order_id']:
                    self.submitting_short_dict['order_id'] = None
                    self.submitting_short_dict['price'] = None
                    self.submitting_short_dict['status'] = None
                    self.submitting_short_dict['vol'] = None

                if order.vt_orderid == self.cancel_long_orderid:
                    self.cancel_long_orderid = None
                elif order.vt_orderid == self.cancel_short_orderid:
                    self.cancel_short_orderid = None

                self.on_tick()
            
            elif order.status == Status.NOTTRADED:
                if order.vt_orderid == self.submitting_long_dict['order_id']:
                    self.submitting_long_dict['status'] = Status.NOTTRADED
                elif order.vt_orderid == self.submitting_short_dict['order_id']:
                    self.submitting_short_dict['status'] = Status.NOTTRADED

        else:
            if order.status == Status.CANCELLED:
                if order.direction == Direction.LONG:
                    vol = order.volume - order.traded
                else:
                    vol = -(order.volume - order.traded)
                self.send_passiveleg_order(vol, PAYUPN=2)

    def on_trade(self, trade: TradeData):
        """"""
         # Only care active leg order update
        if trade.vt_symbol == self.active_leg.vt_symbol:
            # Hedge passive legs if necessary
            self.hedge_passive_leg()

    def long_active_leg(self, shadow_bid, bestbid, vol):
        # 10档价格高于预报价，则不报。
        if self.active_leg.bids[19,0] > shadow_bid:
            if self.submitting_long_dict['order_id'] and self.cancel_long_orderid is None:
                if self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    self.cancel_order(self.submitting_long_dict['order_id'])
                    self.cancel_long_orderid = self.submitting_long_dict['order_id']
                    self.write_log(f"lower then 9th bids, cancel order, oder_id: {self.cancel_long_orderid}, 9th bids: {self.active_leg.bids[9,0]}, shadow_bid: {shadow_bid}", level=DEBUG)
        # 开始报价
        elif self.active_leg.bids[9,0] < shadow_bid:
            if shadow_bid > bestbid:
                # 根据 bestbid 调整shadow_bids
                shadow_bid = bestbid + self.active_leg.pricetick * 2
                shadow_bid = round_to(shadow_bid, self.active_leg.pricetick)
            else:
                shadow_bid = round_to(shadow_bid, self.active_leg.pricetick)

            # 如果没有报单，则发出委托；否则取消原委托
            if self.submitting_long_dict['order_id'] is None:
                # 不足最小金额，立即返回
                if shadow_bid * vol < 12:
                    return
                # 可用资金不足，立即返回
                if shadow_bid * vol > self.algo_engine.margin_accounts["USDTUSDT."+self.get_contract(self.active_leg.vt_symbol).exchange.value].free:
                    return
                self.submitting_long_dict['order_id'] = self.send_long_order(self.active_leg.vt_symbol, shadow_bid, vol)
                self.submitting_long_dict['price'] = shadow_bid
                self.submitting_long_dict['status'] = Status.SUBMITTING
                self.submitting_long_dict['vol'] = vol
            else:
                if self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    if abs(self.submitting_long_dict['price'] - shadow_bid) > self.active_leg.pricetick * 3 and self.cancel_long_orderid is None:
                        self.cancel_order(self.submitting_long_dict['order_id'])
                        self.cancel_long_orderid = self.submitting_long_dict['order_id']
                        self.write_log(f"long more than 3 tick, last short: {self.submitting_long_dict['price']}, this shadow_bid: {shadow_bid}")

        else:
            if self.submitting_long_dict['order_id'] and self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                 if abs(self.submitting_long_dict['price'] - shadow_bid) > self.active_leg.pricetick * 3 and self.cancel_long_orderid is None:
                    self.cancel_order(self.submitting_long_dict['order_id'])
                    self.cancel_long_orderid = self.submitting_long_dict['order_id']
                    self.write_log(f"<9-19> long more than 3 tick, last short: {self.submitting_long_dict['price']}, this shadow_bid: {shadow_bid}")

    def short_active_leg(self, shadow_ask, bestask, vol):
        # 10档报价低于要提报价格，则不报。
        if self.active_leg.asks[19,0] < shadow_ask:
            if self.submitting_short_dict['order_id'] and self.cancel_short_orderid is None:
                if self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    self.cancel_order(self.submitting_short_dict['order_id'])
                    self.cancel_short_orderid = self.submitting_short_dict['order_id']
                    self.write_log(f"higher then 9th asks, cancel order, oder_id: {self.cancel_short_orderid}, 9th ask: {self.active_leg.asks[9,0]}, shadow_ask :{shadow_ask}", level=DEBUG)
        # 开始报价
        elif self.active_leg.asks[9,0] > shadow_ask:
            if shadow_ask < bestask:
                # 根据 bestask shadow_ask
                shadow_ask = bestask - self.active_leg.pricetick * 2
                shadow_ask = round_to(shadow_ask, self.active_leg.pricetick)
            else:
                shadow_ask = round_to(shadow_ask, self.active_leg.pricetick)
            # 如果没有报单，则发出委托；否则取消原委托
            if self.submitting_short_dict['order_id'] is None:
                # 不足最小金额，立即返回
                if shadow_ask * vol < 12:
                    return
                borrow = False
                if vol > self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free:
                    # 可借不足，立即返回
                    if vol > self.algo_engine.margin_accounts[self.active_leg.vt_symbol].max_borrow:
                        return
                    borrow = True
                    self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free += vol
                    self.algo_engine.margin_accounts[self.active_leg.vt_symbol].max_borrow -= vol
                self.submitting_short_dict['order_id'] = self.send_short_order(self.active_leg.vt_symbol, shadow_ask, vol, borrow)
                self.submitting_short_dict['price'] = shadow_ask
                self.submitting_short_dict['status'] = Status.SUBMITTING
                self.submitting_short_dict['vol'] = vol
                if borrow:
                    self.cancel_short_orderid = self.submitting_short_dict['order_id']
            else:
                if self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    if abs(self.submitting_short_dict['price'] - shadow_ask) > self.active_leg.pricetick*3 and self.cancel_short_orderid is None:
                        self.cancel_order(self.submitting_short_dict['order_id'])
                        self.cancel_short_orderid = self.submitting_short_dict['order_id']
                        self.write_log(f"short more than 3 tick, last short: {self.submitting_short_dict['price']}, this shadow_ask: {shadow_ask}")
        else:
            if self.submitting_short_dict['order_id'] and self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                if abs(self.submitting_short_dict['price'] - shadow_ask) > self.active_leg.pricetick*3 and self.cancel_short_orderid is None:
                    self.cancel_order(self.submitting_short_dict['order_id'])
                    self.cancel_short_orderid = self.submitting_short_dict['order_id']
                    self.write_log(f"<9-19> short more than 3 tick, last short: {self.submitting_short_dict['price']}, this shadow_ask: {shadow_ask}")

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
        leg_order_volume = passive_target - passive_traded
        if abs(leg_order_volume) * self.passive_leg.bids[0,0] > 12:
            self.send_passiveleg_order(leg_order_volume)
            self.write_log(f'hedge_passive_leg active_traded: {active_traded}, passive_target: {passive_target}, passive_traded: {passive_traded}')
            return False

        return True

    def send_passiveleg_order(self, leg_volume: float, borrowmoney = False, PAYUPN=0):
        """"""
        if leg_volume > 0:
            price = round_to(self.passive_leg.asks[0,0] + self.passive_leg.pricetick * (self.payup + PAYUPN),self.passive_leg.pricetick)
            self.send_long_order(self.passive_leg.vt_symbol, price, leg_volume)
        elif leg_volume < 0:
            price = round_to(self.spread.passive_leg.bids[0,0] - self.passive_leg.pricetick * (self.payup + PAYUPN),self.passive_leg.pricetick)
            self.send_short_order(self.passive_leg.vt_symbol, price, abs(leg_volume))
