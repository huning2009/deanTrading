# encoding: UTF-8

"""
海龟系统1的反策略，20天high的最高价卖出，10天low的最低价的买平。
限价单策略，同时发出20天high的最高价卖单和20天low的最低价买单。
如果成交，则撤掉反方向的开仓单，改挂平仓单
"""

from __future__ import division

import talib
import numpy as np
from time import sleep
import datetime as dt

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


EVENT_TIMER = 'eTimer' 
########################################################################
class HLBeatStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'HLBeatStrategy'
    author = u'ForwardCapital'

    # 策略参数
    turtleWindow = 20         # 通道窗口数
    ma1Window = 5           # 过滤用均线窗口
    ma2Window = 10           # 过滤用均线窗口
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    xMinBar = 15

    # 策略变量    
    periodHigh = 0                         # 布林带中轨
    periodLow = 0                         # 布林带宽度

    entryUp = 0                         # 开仓上轨
    longEntry = 0
    entryDown = 0
    shortEntry = 0                         # 开仓下轨
    exitUp = 0                          # 平仓上轨   
    shortExit = 0 
    exitDown = 0 
    longExit = 0                         # 平仓上轨  

    
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

    minute = None
    timeFuncTurn = False


    # 参数列表，保存了参数的名称
    paramList = ['className', 'author', 'vtSymbol', "turtleWindow", "ma1Window", "ma2Window", "xMinBar"]    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'sellOrderID', 'coverOrderID', 'shortOrderID', 'buyOrderID', 'longExit', 'shortExit', 'orderList']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(HLBeatStrategy, self).__init__(ctaEngine, setting)
        self.bm = BarGenerator(self.on_bar, self.xMinBar, self.onFiveBar)
        self.am = ArrayManager()

        self.cta_engine.eventEngine.register(EVENT_TIMER, self.onTimeFunc)
        
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

        if not self.am.inited or not self.trading:
            return        

        # 计算指标数值
        self.exitUp = min(self.am.low[-self.turtleWindow/2:])
        self.exitDown = max(self.am.high[-self.turtleWindow/2:])

        # 只发平仓单
        if self.pos > 0:
            if not self.longExit:
                self.longExit = self.exitDown

                if self.sellOrderID:
                    self.cancel_order
                    (self.sellOrderID)
                else:
                    self.cancel_all()

                    self.sellOrderID =  self.sell(self.longExit, self.fixedSize, False)
                    print(u'None sellOrderID###多头平仓，单号：%s' % self.sellOrderID)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
            else:
                if self.longExit != self.exitDown:
                    self.longExit = self.exitDown
                    self.cancel_order(self.sellOrderID)

        elif self.pos < 0:
            if not self.shortExit:
                self.shortExit = self.exitUp
                if self.coverOrderID:
                    self.cancel_order(self.coverOrderID)
                else:
                    self.cancel_all()

                    self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, False)
                    print(u'None coverOrderID###空头平仓，单号：%s' % self.coverOrderID)
                    self.coverOrderID = self.orderIDConvert(self.coverOrderID)
            else:
                if self.shortExit != self.exitUp:
                    self.shortExit = self.exitUp
                    self.cancel_order(self.coverOrderID)

    
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

        # 计算指标数值
        print(u'highArray is ↓↓↓↓↓↓↓↓↓↓')
        print(self.am.high[-self.turtleWindow:])
        print(u'lowArray is ↓↓↓↓↓↓↓↓↓↓')
        print(self.am.low[-self.turtleWindow:])
        self.entryUp = max(self.am.high[-self.turtleWindow:])
        self.entryDown = min(self.am.low[-self.turtleWindow:])
        # self.exitUp = min(self.am.low[-self.turtleWindow/2:])
        # self.exitDown = max(self.am.high[-self.turtleWindow/2:])
        # print u'entryup:%s, entryDown:%s' % (self.entryUp, self.entryDown)
        # ma1 = self.am.sma(self.ma1Window, False)
        # ma2 = self.am.sma(self.ma2Window, False)
        # cci = self.am.cci(self.CCIWindow, True)

        # 判断是否进行交易，只发开仓单
        if not self.buyOrderID or self.buyOrderID in self.orderList:
            if self.pos == 0:
                if not self.longEntry:
                    if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                        print(u'%s 高低点太窄，放弃交易！' % self.vt_symbol)
                        return
                    self.longEntry = self.entryDown

                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, False)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    self.orderList.append(self.buyOrderID)

                elif self.longEntry != self.entryDown:
                    self.cancel_order(self.buyOrderID)
                    if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                        print(u'%s 高低点太窄，放弃交易！' % self.vt_symbol)
                        return
                    self.longEntry = self.entryDown

                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, False)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    self.orderList.append(self.buyOrderID)

        if not self.shortOrderID or self.shortOrderID in self.orderList:
            if self.pos == 0:
                if not self.shortEntry:
                    if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                        print(u'%s 高低点太窄，放弃交易！' % self.vt_symbol)
                        return
                    self.shortEntry = self.entryUp

                    self.shortOrderID = self.short(self.shortEntry, self.fixedSize, False)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    self.orderList.append(self.shortOrderID)

                elif self.shortEntry != self.entryUp:
                    self.cancel_order(self.shortOrderID)
                    if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                        print(u'%s 高低点太窄，放弃交易！' % self.vt_symbol)
                        return
                    self.shortEntry = self.entryUp

                    self.shortOrderID = self.short(self.shortEntry, self.fixedSize, False)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    self.orderList.append(self.shortOrderID)

        # 发出状态更新事件
        # self.putEvent()        

    #----------------------------------------------------------------------
    def on_order(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # print u'委托变化推送：%s' % order.__dict__
        # if self.buyOrderID:
        #     if order.orderID == self.buyOrderID.split('.')[1]:
        #         if order.status == STATUS_CANCELLED:
        #             self.orderList.remove(self.buyOrderID)

        # if self.shortOrderID:
        #     if order.orderID == self.shortOrderID.split('.')[1]:
        #         if order.status == STATUS_CANCELLED:
        #             self.orderList.remove(self.shortOrderID)

        if self.sellOrderID:
            if order.orderID == self.sellOrderID.split('.')[1]:
                if order.status == Status.CANCELLED:
                    self.sellOrderID =  self.sell(self.longExit, self.fixedSize, False)
                    print(u'###多头平仓，单号：%s' % self.sellOrderID)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
        if self.coverOrderID:
            if order.orderID == self.coverOrderID.split('.')[1]:
                if order.status == Status.CANCELLED:
                    self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, False)
                    print(u'###空头平仓，单号：%s' % self.coverOrderID)
                    self.coverOrderID = self.orderIDConvert(self.coverOrderID)

        pass

    #----------------------------------------------------------------------
    def on_trade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # print u'成交推送：%s' % trade.__dict__
        if self.buyOrderID:
            if trade.tradeID == self.buyOrderID.split('.')[1]:
                self.orderList.remove(self.buyOrderID)

        if self.shortOrderID:
            if trade.tradeID == self.shortOrderID.split('.')[1]:
                self.orderList.remove(self.shortOrderID)

        if trade.offset in [Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY]:
            self.buyOrderID = None
            self.shortOrderID = None
            self.longExit = 0
            self.shortExit = 0

        # 发出状态更新事件
        # self.putEvent()
        pass

    #----------------------------------------------------------------------
    def on_stop_order(self, so):
        """停止单推送"""
        # print u'StopOrder回报,stopOrderID:%s, status:%s' % (so.stopOrderID, so.status)
        # if so.status == STOPORDER_CANCELLED or so.status == STOPORDER_TRIGGERED:
        #     self.orderList.remove(so.stopOrderID)
        pass

    #----------------------------------------------------------------------
    def onTimeFunc(self, event):
        now = dt.datetime.now()
        now_hour = now.hour
        now_minute = now.minute

        if self.minute != now_minute:
            self.minute = now_minute
            if not self.timeFuncTurn:
                self.timeFuncTurn = True

        if now_hour == 2 and now_minute == 32 and self.timeFuncTurn:
            self.cta_engine.saveSyncData(self)
            self.timeFuncTurn = False

        elif now_hour == 15 and now_minute == 10 and self.timeFuncTurn:
            self.buyOrderID = None
            self.shortOrderID = None
            self.coverOrderID = None
            self.sellOrderID = None
            self.longExit = 0
            self.shortExit = 0
            self.orderList = []
            self.cta_engine.saveSyncData(self)
            self.timeFuncTurn = False

