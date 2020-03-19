import numpy as np
import pandas as pd
import talib as ta
from gateway import Gateway

class TradingEngine(object):
    """
    震荡/趋势策略
    入场条件:
    1、震荡市中采用开盘区间突破进场
    2、趋势市中采用布林通道突破进场
    出场条件:
    1、震荡市时进场单的出场为反手信号和ATR保护性止损
    2、趋势市时进场单的出场为反手信号和均线出场
    """
    # params
    ATR_N = 1.0         # ATR 保护性止损倍数
    PERIOD = 15         # 布林通道周期
    MAX_POS = 1         # 最大开仓手数
    SYMBOL = ''         # 交易合约
    STD = 0.01          # 波动率阈值，高于阈值则采用震荡策略，反之则采用趋势策略
    STD_N = 10          # 计算波动率的历史数据期数

    def __init__(self, event_engine, gateway):
        self.gateway = Gateway()
        self.orders = []
        self.pos = 0

        self.trend = True               # 是否为趋势行情
        self.boll_up = 0
        self.boll_dn = 0
        self.boll_mid = 0

        self.market_start = False       # 开盘时间区间是否过去，过去则开始震荡策略交易
        self.daily_high = 0             # 震荡策略买入点，空仓出场点
        self.daily_low = 0              # 震荡策略卖出点，多仓出场点
        self.atr = 0
        self.buy_price = 0              # 多单开仓价格
        self.short_price = 0            # 空单开仓价格

    def init(self):
        """
        初始化策略，根据历史数据计算波动率std，当过去N期波动率大于设定参数阈值STD，
        则启动震荡策略，否则启动趋势策略。
        每日定时启动，进行初始化
        """

        history_price = self.query_history(self.SYMBOL)
        cal_std_price = history_price['close'].iloc[-(self.STD_N+1):]
        # 计算价格收益率序列的标准差（市场波动率），也可用talib直接算STDDEV
        std = (cal_std_price.diff() / cal_std_price).std()

        if std > self.STD:
            self.trend = False
            cal_atr_price = history_price.iloc[-self.STD_N:,:]
            self.atr = ta.ATR(cal_atr_price['high'], cal_atr_price['low'], cal_atr_price['close'], self.STD_N).iloc[-1]
        else:
            self.trend = True
            # 计算趋势策略出入场点
            cal_boll_price = history_price.iloc[-self.PERIOD:,:]
            u, m, d = ta.BBANDS( cal_boll_price['close'], self.PERIOD)
            self.boll_up = u.iloc[-1]
            self.boll_mid = m.iloc[-1]
            self.boll_dn = d.iloc[-1]

        # 初始化市场状态
        self.market_start = False            

    def on_tick(self, tick):
        if self.trend:
            self.trend_trading(tick)
        else:
            self.cal_daily_market_price(tick)

    def trend_trading(self, tick):
        if self.pos >= 0 and self.pos < self.MAX_POS and tick.ask_price > self.boll_up:
            # 买入开仓
            vol = self.MAX_POS - self.pos
            self.send_order(tick.ask_price, vol)
            
        elif self.pos > 0 and tick.ask_price < self.boll_mid:
            # 卖出平仓，均线高于反手入场点，仅参考均线即可
            vol = -self.pos 
            self.send_order(tick.bid_price, vol)

        elif self.pos <= 0 and self.pos > -self.MAX_POS and tick.bid_price < self.boll_dn:
            # 卖出开仓
            vol = -self.MAX_POS - self.pos
            self.send_order(tick.bid_price, vol)

        elif self.pos < 0 and tick.bid_price > self.boll_mid:
            # 买入平仓
            vol = - self.pos
            self.send_order(tick.ask_price, vol)

    def cal_daily_market_price(self, tick):

        if self.market_start:
            """开始交易"""
            self.volatile_market_trading(tick) 
        else:
            """等待交易"""
            if self.daily_high:
                self.daily_high = max(self.daily_high, tick.last_price)
            else:
                self.daily_high = tick.last_price
            if self.daily_low:
                self.daily_low = min(self.daily_low, tick.last_price)
            else:
                self.daily_low = tick.last_price

            if tick.datetime.hour == 9 and tick.datetime.minute == 31:
                self.market_start = True


    def volatile_market_trading(self, tick):
        if self.pos >= 0 and self.pos < self.MAX_POS and tick.bid_price > self.daily_high:
            # 买入开仓
            vol = self.MAX_POS - self.pos
            self.send_order(tick.ask_price, vol)
            
        elif self.pos > 0 and (tick.ask_price < self.daily_low or (self.buy_price - tick.ask_price) > self.atr*self.ATR_N):
            # 卖出平仓，仅平现有仓位
            vol = -self.pos
            self.send_order(tick.bid_price, vol)

        elif self.pos <= 0 and self.pos > -self.MAX_POS and tick.ask_price < self.daily_low:
            # 卖出开仓
            vol = -self.MAX_POS - self.pos
            self.send_order(tick.bid_price, vol)

        elif self.pos < 0 and (tick.bid_price > self.daily_high or (tick.bid_price - self.short_price) > self.atr*self.ATR_N):
            # 买入平仓，仅平现有仓位
            vol = -self.pos
            self.send_order(tick.ask_price, vol)

    def on_bar(self, bar):
        pass

    def on_order(self, order):
        # 如果订单全部成交或取消，则移除order_id
        if order.status=='cancel' or order.status=='allTrade':
            self.orders.remove(order.order_id)

    def on_trader(self, trade):
        # 计算策略持仓
        if trade.direction=='long':
            if self.pos == 0:
                # 实盘需要设定一定阈值
                self.buy_price = trade.price
            self.pos += trade.vol
        else:
            if self.pos == 0:
                # 实盘需要设定一定阈值
                self.short_price = trade.price
            self.pos -+ trade.vol
    
    def query_history(self, symbol):
        """
        获取历史数据
        """
        df = pd.DataFrame()
        df.columns = ['close', 'high', 'low']
        return df

    def send_order(self, price, vol):
        # 如果有挂单，暂不发单，直接返回
        if len(self.orders) > 0:
            return
            
        if vol > 0:
            direction = 'long'
        else:
            direction = 'short'

        # 实盘需对vol设定阈值
        order_id = self.gateway.send_order(self.SYMBOL, price, abs(vol), direction)
        self.orders.append(order_id)
