from logging import DEBUG
from typing import Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import copy
from logging import DEBUG, INFO, CRITICAL

from myConstant import Direction, Offset, Status, Interval
from myObject import (TickData, OrderData, TradeData, HistoryRequest)
from myUtility import round_to

from .template import SpreadAlgoTemplate
from .base import SpreadData

class SpreadMakerAlgo(SpreadAlgoTemplate):
    """"""
    algo_name = "SpreadMaker"
    SELL_BUY_RATIO = 2
    FILT_RATIO = 1
    COMMISSION = 0.0006 + 0.0004

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

        self.spread_series = None
        self.std_series = None
        self.quantile1 = None
        self.quantile9 = None
        self.price_ratio = 1.0

        self.algo_count = 0


        self.trading = False

    def init(self):
        """
        初始化数据
        """
        # self.get_history_data(self)
        self.trading = True

    def get_history_data(self):
        """download history data"""
        endtime = datetime.now()
        starttime = endtime - timedelta(days=7)

        active_gateway = self.algo_engine.spread_engine.get_gateway(self.active_leg.gateway_name)
        passive_gateway = self.algo_engine.spread_engine.get_gateway(self.passive_leg.gateway_name)
        
        act_query = HistoryRequest(self.active_leg.symbol, self.active_leg.exchange, starttime, endtime, Interval.MINUTE)
        active_his_bar = active_gateway.query_history(act_query)
        print(f'active symbol: {self.active_leg.symbol}, {len(active_his_bar)}')
        active_close_arr = np.zeros((len(active_his_bar),2))
        active_df = pd.DataFrame(active_close_arr)
        for i in range(len(active_his_bar)):
            active_df.iloc[i,0] = active_his_bar[i].datetime
            active_df.iloc[i,1] = active_his_bar[i].close_price

        active_df.columns = ['datetime', 'spot_close']
        active_df.set_index('datetime', inplace=True)
        active_df = active_df.loc[active_df.index.drop_duplicates(keep=False), 'spot_close']

        passive_query = HistoryRequest(self.passive_leg.symbol, self.passive_leg.exchange, starttime, endtime, Interval.MINUTE)
        passive_his_bar = passive_gateway.query_history(passive_query)
        print(f'passive symbol: {self.passive_leg.symbol}, {len(passive_his_bar)}')
        pasive_close_arr = np.zeros((len(passive_his_bar),2))
        passive_df = pd.DataFrame(pasive_close_arr)
        for i in range(len(passive_his_bar)):
            passive_df.iloc[i,0] = passive_his_bar[i].datetime
            passive_df.iloc[i,1] = passive_his_bar[i].close_price

        passive_df.columns = ['datetime', 'fu_close']
        passive_df.set_index('datetime', inplace=True)
        passive_df = passive_df.loc[passive_df.index.drop_duplicates(keep=False), 'fu_close']

        data = pd.concat((active_df, passive_df), axis=1, join='inner')
        data.sort_index(inplace=True)
        data.columns = ['spot', 'futures']
        print(data[-5:])
        self.spread_series = data.iloc[:,0] - data.iloc[:,1]

        self.std_series = self.spread_series.diff().rolling(60).std().values[60:]
        self.spread_series = self.spread_series.values
        print(self.spread_series.shape)
        print(self.std_series.shape)
        print(self.std_series[-1])
        quantile80 = np.quantile(self.std_series, 0.8)
        quantile95 = np.quantile(self.std_series, 0.95)
        print(quantile80)
        print(quantile95)
        latest_std = max(self.std_series[-1], quantile80)
        latest_std = min(latest_std, quantile95)
        # 将[quantile01, quantile09]映射到[1,10]区间
        self.price_ratio = 9.0 / (quantile95 - quantile80) * (latest_std - quantile80) + 1.0
        self.write_log(f"init algo, price_ratio: {self.price_ratio}", level=DEBUG)

        self.spread.buy_price *= self.price_ratio
        # self.spread.sell_price *= self.price_ratio
        self.spread.short_price *= self.price_ratio
        # self.spread.cover_price *= self.price_ratio

    def on_tick(self, tick=None):
        """"""
        if not self.trading:
            return

        if (self.active_leg.bids is None) or (self.passive_leg.bids is None):
            return
        # 首先判断是否有敞口，有则对冲
        self.hedge_passive_leg()

        if abs(self.spread.net_pos) < self.pos_threshold:
            # 无持仓
            long_vol = self.max_pos
            short_vol = self.max_pos

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
            long_vol = min(-self.spread.net_pos, self.max_pos)
            short_vol = min(self.max_pos * self.SELL_BUY_RATIO + self.spread.net_pos, self.max_pos)

            bestbid = self.cal_active_bestbid(long_vol)
            bestask = self.cal_active_bestask(short_vol)
            shadow_coverbid = self.cal_shadow_coverbid(long_vol)
            shadow_shortask = self.cal_shadow_shortask(short_vol)
            
            self.long_active_leg(shadow_coverbid, bestbid, long_vol)
            self.short_active_leg(shadow_shortask, bestask, short_vol)

        elif (self.spread.net_pos - self.pos_threshold) < -self.max_pos * self.SELL_BUY_RATIO:
            # 持有active 空单，passive多单。已到最大单量，仅买平
            long_vol = min(-self.spread.net_pos, self.max_pos)

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
        if n ==20:
            # self.write_log(cumshadow_bids, level=CRITICAL)
            n = 19
        shadow_buybid = cumshadow_bids[n,0] * (1 - self.COMMISSION - self.payup + self.spread.buy_price)

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
        if n == 20:
            # self.write_log(cumshadow_asks, level=CRITICAL)
            n = 19
        shadow_shortask = cumshadow_asks[n,0] * (1 + self.COMMISSION + self.payup + self.spread.short_price)

        return shadow_shortask

    def cal_shadow_coverbid(self, max_vol):
        """"""
        cumshadow_bids = copy.copy(self.passive_leg.bids)
        cumshadow_bids[:,1] = np.cumsum(cumshadow_bids[:,1], axis=0)
        cumshadow_bids[:,1][cumshadow_bids[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_bids[:,1])
        if n ==20:
            # self.write_log(cumshadow_bids, level=CRITICAL)
            n = 19

        shadow_coverbid = cumshadow_bids[n,0] * (1 - self.COMMISSION - self.payup + self.spread.cover_price)

        return shadow_coverbid

    def cal_shadow_sellask(self, max_vol):
        """"""
        cumshadow_asks = copy.copy(self.passive_leg.asks)
        cumshadow_asks[:,1] = np.cumsum(cumshadow_asks[:,1], axis=0)
        cumshadow_asks[:,1][cumshadow_asks[:,1] > max_vol] = 0
        n = np.count_nonzero(cumshadow_asks[:,1])
        if n ==20:
            # self.write_log(cumshadow_asks, level=CRITICAL)
            n = 19
        shadow_sellask = cumshadow_asks[n,0] * (1 + self.COMMISSION + self.payup + self.spread.sell_price)

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
        if n == 20:
            # self.write_log(bids, level=CRITICAL)
            n = 19
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
        if n == 20:
            # self.write_log(asks, level=CRITICAL)
            n = 19
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
                self.send_passiveleg_order(vol, PAYUPN=1.5)

    def on_trade(self, trade: TradeData):
        """"""
         # Only care active leg order update
        if trade.vt_symbol == self.active_leg.vt_symbol:
            # Hedge passive legs if necessary
            self.hedge_passive_leg()

    def long_active_leg(self, shadow_bid, bestbid, vol):
        # # 10档价格高于预报价，则不报。
        # if self.active_leg.bids[19,0] > shadow_bid:
        #     if self.submitting_long_dict['order_id'] and self.cancel_long_orderid is None:
        #         if self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
        #             self.cancel_order(self.submitting_long_dict['order_id'])
        #             self.cancel_long_orderid = self.submitting_long_dict['order_id']
        #             self.write_log(f"lower then 9th bids, cancel order, oder_id: {self.cancel_long_orderid}, 9th bids: {self.active_leg.bids[9,0]}, shadow_bid: {shadow_bid}", level=DEBUG)
        # 开始报价
        if bestbid < shadow_bid:
            # if shadow_bid > bestbid:
            #     # 根据 bestbid 调整shadow_bids
            #     shadow_bid = bestbid + self.active_leg.pricetick * 2
            #     shadow_bid = round_to(shadow_bid, self.active_leg.pricetick)
            # else:
            shadow_bid = round_to(shadow_bid, self.active_leg.pricetick)

            # 如果没有报单，则发出委托；否则取消原委托
            if self.submitting_long_dict['order_id'] is None:
                # 可用资金不足，调整数量
                if shadow_bid * vol > self.algo_engine.margin_accounts["USDTUSDT."+self.active_leg.exchange.value].free:
                    vol = self.algo_engine.margin_accounts["USDTUSDT."+self.active_leg.exchange.value].free * 0.9 / shadow_bid
                # 不足最小金额，立即返回
                if shadow_bid * vol < 12:
                    return
                self.submitting_long_dict['order_id'] = self.send_long_order(self.active_leg.vt_symbol, shadow_bid, vol)
                self.submitting_long_dict['price'] = shadow_bid
                self.submitting_long_dict['status'] = Status.SUBMITTING
                self.submitting_long_dict['vol'] = vol
            else:
                if self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    if (abs(self.submitting_long_dict['price'] - shadow_bid) > shadow_bid * 0.0002) and self.cancel_long_orderid is None:
                        self.cancel_order(self.submitting_long_dict['order_id'])
                        self.cancel_long_orderid = self.submitting_long_dict['order_id']
                        self.write_log(f"long more than 2%%, last long: {self.submitting_long_dict['price']}, this shadow_bid: {shadow_bid}")

        else:
            if self.submitting_long_dict['order_id'] and self.submitting_long_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED] and self.cancel_long_orderid is None:
                if (abs(self.submitting_long_dict['price'] - shadow_bid) > shadow_bid * 0.0002) and self.cancel_long_orderid is None:
                    self.cancel_order(self.submitting_long_dict['order_id'])
                    self.cancel_long_orderid = self.submitting_long_dict['order_id']
                    self.write_log(f"price out bestbid: {bestbid}, long more than 3 tick, last long: {self.submitting_long_dict['price']}, this shadow_bid: {shadow_bid}")

    def short_active_leg(self, shadow_ask, bestask, vol):
        # # 10档报价低于要提报价格，则不报。
        # if self.active_leg.asks[19,0] < shadow_ask:
        #     if self.submitting_short_dict['order_id'] and self.cancel_short_orderid is None:
        #         if self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
        #             self.cancel_order(self.submitting_short_dict['order_id'])
        #             self.cancel_short_orderid = self.submitting_short_dict['order_id']
        #             self.write_log(f"higher then 9th asks, cancel order, oder_id: {self.cancel_short_orderid}, 9th ask: {self.active_leg.asks[9,0]}, shadow_ask :{shadow_ask}", level=DEBUG)
        # 开始报价
        if bestask > shadow_ask:
            # if shadow_ask < bestask:
            #     # 根据 bestask shadow_ask
            #     shadow_ask = bestask - self.active_leg.pricetick * 2
            #     shadow_ask = round_to(shadow_ask, self.active_leg.pricetick)
            # else:
            shadow_ask = round_to(shadow_ask, self.active_leg.pricetick)
            # 如果没有报单，则发出委托；否则取消原委托
            if self.submitting_short_dict['order_id'] is None:
                borrow = False
                if vol > self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free:
                    # 可借不足，调整数量
                    if (vol-self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free) > self.algo_engine.margin_accounts[self.active_leg.vt_symbol].max_borrow:
                        vol = self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free + self.algo_engine.margin_accounts[self.active_leg.vt_symbol].max_borrow * 0.9

                    borrow = True
                    self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free = vol
                    self.algo_engine.margin_accounts[self.active_leg.vt_symbol].max_borrow -= (vol-self.algo_engine.margin_accounts[self.active_leg.vt_symbol].free)

                # 不足最小金额，立即返回
                if shadow_ask * vol < 12:
                    return

                self.submitting_short_dict['order_id'] = self.send_short_order(self.active_leg.vt_symbol, shadow_ask, vol, borrow)
                self.submitting_short_dict['price'] = shadow_ask
                self.submitting_short_dict['status'] = Status.SUBMITTING
                self.submitting_short_dict['vol'] = vol
                if borrow:
                    self.cancel_short_orderid = self.submitting_short_dict['order_id']
            else:
                if self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED]:
                    if (abs(self.submitting_short_dict['price'] - shadow_ask) > shadow_ask*0.0002) and self.cancel_short_orderid is None:
                        self.cancel_order(self.submitting_short_dict['order_id'])
                        self.cancel_short_orderid = self.submitting_short_dict['order_id']
                        self.write_log(f"short more than 2%%, last short: {self.submitting_short_dict['price']}, this shadow_ask: {shadow_ask}")
        else:
            if self.submitting_short_dict['order_id'] and self.submitting_short_dict['status'] in [Status.NOTTRADED, Status.PARTTRADED] and self.cancel_short_orderid is None:
                if (abs(self.submitting_short_dict['price'] - shadow_ask) > shadow_ask*0.0002) and self.cancel_short_orderid is None:
                    self.cancel_order(self.submitting_short_dict['order_id'])
                    self.cancel_short_orderid = self.submitting_short_dict['order_id']
                    self.write_log(f"price out, bestask: {bestask} short more than 3 tick, last short: {self.submitting_short_dict['price']}, this shadow_ask: {shadow_ask}")

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

    def send_passiveleg_order(self, leg_volume: float, borrowmoney = False, PAYUPN=1):
        """"""
        if leg_volume > 0:
            price = round_to(self.passive_leg.asks[0,0] * (1 + self.payup * PAYUPN),self.passive_leg.pricetick)
            self.send_long_order(self.passive_leg.vt_symbol, price, leg_volume)
        elif leg_volume < 0:
            price = round_to(self.passive_leg.bids[0,0] * (1 - self.payup * PAYUPN),self.passive_leg.pricetick)
            self.send_short_order(self.passive_leg.vt_symbol, price, abs(leg_volume))

    def on_interval(self):
        if True:
            return

        self.algo_count += 1

        if not self.trading:
            return
        if self.algo_count > 60:
            dtt1 = datetime.now()

            self.algo_count = 0

            self.spread_series[:-1] = self.spread_series[1:]
            self.spread_series[-1] = (self.active_leg.bids[0,0] - self.passive_leg.bids[0,0] + self.active_leg.asks[0,0] - self.passive_leg.asks[0,0]) * 0.5

            new_std = self.spread_series[-60:].std()
            self.std_series[:-1] = self.std_series[1:]
            self.std_series[-1] = new_std
            
            quantile80 = np.quantile(self.std_series, 0.8)
            quantile95 = np.quantile(self.std_series, 0.95)
            self.write_log(f"on_interval, std: {new_std}, quantile80: {quantile80}, quantile95: {quantile95}", level=DEBUG)
            new_std = max(new_std, quantile80)
            new_std = min(new_std, quantile95)
            # 将[quantile01, quantile09]映射到[1,10]区间
            self.price_ratio = 9.0 / (quantile95 - quantile80) * (new_std - quantile80) + 1.0

            dtt2 = datetime.now()
            if self.price_ratio > 1:
                self.write_log(f"on_interval, price_ratio: {self.price_ratio}, cost time: {dtt2-dtt1}", level=CRITICAL)

            # self.spread.buy_price *= self.price_ratio
            # self.spread.sell_price *= self.price_ratio
            # self.spread.short_price *= self.price_ratio
            # self.spread.cover_price *= self.price_ratio