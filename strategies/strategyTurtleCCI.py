# encoding: UTF-8

"""
仅在知乎Live中分享，请勿外传。

基于布林通道通道的交易策略，适合用在股指上5分钟线上。
"""

from __future__ import division

import talib
import numpy as np

from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.app.cta_strategy.base import StopOrderStatus, Direction, Offset
from vnpy.trader.constant import Status



########################################################################
class TurtleCCIStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'TurtleCCIStrategy'
    author = u'ForwardCapital'

    # 策略参数
    turtleWindow = 20         # 通道窗口数
    trailingPrcnt = 0.4     # 移动止损百分比
    CCIWindow = 14           # 过滤用均线窗口
    ma1Window = 10           # 过滤用均线窗口
    ma2Window = 20           # 过滤用均线窗口
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量    
    periodHigh = 0                         # 布林带中轨
    periodLow = 0                         # 布林带宽度
    entryUp = 0                         # 开仓上轨
    exitUp = 0                          # 平仓上轨    
    
    CCIFilter = 0                        # 均线过滤
    CCIFilter1 = 0                       # 上一期均线                   
    
    intraTradeHigh = 0                  # 持仓期内的最高点  
    intraTradeLow = 0                  # 持仓期内的最低点  
    longEntry = 0                       # 多头开仓
    longExit = 0                        # 多头平仓    
    
    orderList = []                      # 保存委托代码的列表
    buyOrderID = None
    sellOrderID = None
    shortOrderID = None
    coverOrderID = None

    # 参数列表，保存了参数的名称
    paramList = []    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'intraTradeHigh', 'intraTradeLow']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(TurtleCCIStrategy, self).__init__(ctaEngine, setting)
        
        self.bm = BarGenerator(self.on_bar, 15, self.onFiveBar)
        self.am = ArrayManager()
        
    #----------------------------------------------------------------------
    def on_init(self):
        """初始化策略（必须由用户继承实现）"""
        self.write_log(u'策略初始化')
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        self.load_bar(self.initDays)

        self.put_event()

    #----------------------------------------------------------------------
    def on_start(self):
        """启动策略（必须由用户继承实现）"""
        self.write_log(u'策略启动')
        self.put_event()

    #----------------------------------------------------------------------
    def on_stop(self):
        """停止策略（必须由用户继承实现）"""
        self.write_log(u'策略停止')
        self.put_event()

    #----------------------------------------------------------------------
    def on_tick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bm.update_tick(tick)

    #----------------------------------------------------------------------
    def on_bar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bm.update_bar(bar)
    
    #----------------------------------------------------------------------
    def orderIDConvert(self, orderList):
        if not orderList:
            return []
        else:
            return orderList[0]
    #----------------------------------------------------------------------
    def onFiveBar(self, bar, lastTick):
        """收到5分钟K线"""        
        # 保存K线数据
        self.am.update_bar(bar)
        if not self.am.inited or not self.trading:
            return        

        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        print(u'onFiveBar↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓,datetime:%s' % bar.datetime)
        # 计算指标数值
        self.entryUp = max(self.am.high[-self.turtleWindow:])
        self.entryDown = min(self.am.low[-self.turtleWindow:])
        self.entryUp = self.bollMid + self.bollStd * self.entryDev
        self.exitUp = self.bollMid + self.bollStd * self.exitDev
        
        ma1 = self.am.sma(self.ma1Window, False)
        ma2 = self.am.sma(self.ma2Window, False)
        cci = self.am.cci(self.CCIWindow, True)
        
        # 判断是否要进行交易
        if not self.buyOrderID or not self.shortOrderID:
            if self.pos == 0:
                # 下开仓单
                if ma1 > ma2:
                    self.buyOrderID = self.buy(self.entryUp, self.fixedSize, True)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    print('None order!!!buyOrderID is : %s ' % self.buyOrderID)
                    if self.buyOrderID:
                        self.orderList.append(self.buyOrderID)
                else:
                    self.shortOrderID = self.short(self.entryDown, self.fixedSize, True)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    print('None order!!!shortOrderID is : %s ' % self.shortOrderID)
                    if self.shortOrderID:
                        self.orderList.append(self.shortOrderID)

            elif self.pos > 0:
                # 下平仓单
                if cci[-1] < 100 and cci[-2] > 100:
                    # ######此处实盘需要修改发单价格
                    self.sellOrderID = self.sell(bar.low*0.9, self.fixedSize)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                    print('order None!!!sellOrderID is : %s ' % self.sellOrderID)
                    if self.sellOrderID:
                        self.orderList.append(self.sellOrderID)
            elif self.pos < 0:
                # 下平仓单
                if cci[-1] > -100 and cci[-2] < -100:
                    # ######此处实盘需要修改发单价格
                    self.coverOrderID = self.cover(bar.high*0.9, self.fixedSize)
                    self.coverOrderID = self.orderIDConvert(self.coverOrderID)
                    print('order None!!!coverOrderID is : %s ' % self.coverOrderID)
                    if self.coverOrderID:
                        self.orderList.append(self.coverOrderID)
        else:
            if self.buyOrderID in self.orderList or self.shortOrderID in self.orderList:
                self.cancel_all()
                # 下开仓单
                if ma1 > ma2:
                    self.buyOrderID = self.buy(self.entryUp, self.fixedSize, True)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    print('buyOrderID is : %s ' % self.buyOrderID)
                    if self.buyOrderID:
                        self.orderList.append(self.buyOrderID)
                else:
                    self.shortOrderID = self.short(self.entryDown, self.fixedSize, True)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    print('shortOrderID is : %s ' % self.shortOrderID)
                    if self.shortOrderID:
                        self.orderList.append(self.shortOrderID)
            else:
                if self.pos > 0:
                    # 下平仓单
                    if cci[-1] < 100 and cci[-2] > 100:
                        # ######此处实盘需要修改发单价格
                        self.sellOrderID = self.sell(bar.low*0.9, self.fixedSize)
                        self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                        print('order None!!!sellOrderID is : %s ' % self.sellOrderID)
                        if self.sellOrderID:
                            self.orderList.append(self.sellOrderID)
                elif self.pos < 0:
                    # 下平仓单
                    if cci[-1] > -100 and cci[-2] < -100:
                        # ######此处实盘需要修改发单价格
                        self.coverOrderID = self.cover(bar.high*0.9, self.fixedSize)
                        self.coverOrderID = self.orderIDConvert(self.coverOrderID)
                        print('order None!!!coverOrderID is : %s ' % self.coverOrderID)
                        if self.coverOrderID:
                            self.orderList.append(self.coverOrderID)
                elif self.pos == 0:
                    # 下开仓单
                    if ma1 > ma2:
                        self.buyOrderID = self.buy(self.entryUp, self.fixedSize, True)
                        self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                        print('buyOrderID is : %s ' % self.buyOrderID)
                        if self.buyOrderID:
                            self.orderList.append(self.buyOrderID)
                    else:
                        self.shortOrderID = self.short(self.entryDown, self.fixedSize, True)
                        self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                        print('shortOrderID is : %s ' % self.shortOrderID)
                        if self.shortOrderID:
                            self.orderList.append(self.shortOrderID)

        # 发出状态更新事件
        # self.putEvent()        

    #----------------------------------------------------------------------
    def on_order(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def on_trade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        print(u'成交推送：%s' % trade)
        self.orderList.remove(trade.tradeID)
        # 发出状态更新事件
        # self.putEvent()

    #----------------------------------------------------------------------
    def on_stop_order(self, so):
        """停止单推送"""
        print(u'StopOrder回报,stopOrderID:%s, status:%s' % (so.stopOrderID, so.status))
        if so.status == StopOrderStatus.CANCELLED or so.status == StopOrderStatus.TRIGGERED:
            self.orderList.remove(so.stopOrderID)
        pass