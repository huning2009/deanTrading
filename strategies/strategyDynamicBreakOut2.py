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
from myObject import MyBarGenerator


EVENT_TIMER = 'eTimer' 
########################################################################
class DynamicBreakOut2Strategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'DynamicBreakOut2Strategy'
    author = u'ForwardCapital'

    # 策略参数
    lookBackDays = 20         # 
    devDays = 30           # 计算标准差时间窗口
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量
    xMinBar = 15
    ATR_N = 2

    # 策略变量    
    ATR = 0                         # 布林带中轨
    entryUp = 0                         # 开仓上轨
    entryDown = 0                         # 开仓下轨
    exitUp = 0                          # 平仓上轨    
    exitDown = 0                          # 平仓上轨 

    shortEntry = 0                        
    longEntry = 0
    shortExit = 0 
    longExit = 0                         
    
    orderList = []                      # 保存委托代码的列表
    buyOrderID = None
    sellOrderID = None
    shortOrderID = None
    coverOrderID = None

    minute = None
    timeFuncTurn = False


    # 参数列表，保存了参数的名称
    paramList = ['className', 'author', 'vtSymbol', "fixedSize", "xMinBar", "ATR_N"]    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'sellOrderID', 'coverOrderID', 'shortOrderID', 'buyOrderID', 'longExit', 'shortExit', 'orderList']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DynamicBreakOut2Strategy, self).__init__(ctaEngine, setting)
        self.bg = MyBarGenerator(self.on_bar, self.xMinBar, self.onFiveBar)
        self.am = ArrayManager(60)

        # self.ctaEngine.eventEngine.register(EVENT_TIMER, self.onTimeFunc)
        
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
        self.bg.updateTick(tick)

    #----------------------------------------------------------------------
    def on_bar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)

        if not self.am.inited:
            return        

        # 只发平仓单，各指标已在bg.updateBar()函数内完成
        if self.pos > 0:
            self.longExit = self.exitUp
            self.sellOrderID =  self.sell(self.longExit, self.fixedSize, True)

            # if not self.longExit:
            #     self.longExit = self.exitUp

            #     if self.sellOrderID:
            #         self.cancelOrder(self.sellOrderID)
            #     else:
            #         self.cancelAll()

            #         self.sellOrderID =  self.sell(self.longExit, self.fixedSize, True)
            #         print u'None sellOrderID###多头平仓，单号：%s' % self.sellOrderID
            #         self.sellOrderID = self.orderIDConvert(self.sellOrderID)
            # else:
            #     if self.longExit != self.exitUp:
            #         self.longExit = self.exitUp
            #         self.cancelOrder(self.sellOrderID)

        elif self.pos < 0:
            self.shortExit = self.exitDown
            self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, True)

            # if not self.shortExit:
            #     self.shortExit = self.exitDown
            #     if self.coverOrderID:
            #         self.cancelOrder(self.coverOrderID)
            #     else:
            #         self.cancelAll()

            #         self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, True)
            #         print u'None coverOrderID###空头平仓，单号：%s' % self.coverOrderID
            #         self.coverOrderID = self.orderIDConvert(self.coverOrderID)
            # else:
            #     if self.shortExit != self.exitDown:
            #         self.shortExit = self.exitDown
            #         self.cancelOrder(self.coverOrderID)

    
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
        if not self.am.inited:
            return        

        # 计算指标数值
        volatilityArray = talib.STDDEV(self.am.close, timeperiod=self.devDays)
        self.lookBackDays = int(round(volatilityArray[-1]/volatilityArray[-2]*self.lookBackDays))
        self.lookBackDays = min(self.lookBackDays, 55)
        self.lookBackDays = max(self.lookBackDays, 20)
        bBands = talib.BBANDS(self.am.close, timeperiod=self.lookBackDays)
        self.ATR = talib.ATR(self.am.high, self.am.low, self.am.close, self.lookBackDays)[-1]
        MidLine = bBands[1][-1]
        UpBand = bBands[0][-1]
        DnBand = bBands[2][-1]

        self.entryUp = max(max(self.am.high[-self.lookBackDays:]), UpBand)
        self.entryDown = min(min(self.am.low[-self.lookBackDays:]), DnBand)
        self.exitUp = max(MidLine, self.entryUp-self.ATR_N*self.ATR)
        self.exitDown = min(MidLine, self.entryDown+self.ATR_N*self.ATR)
        print(self.entryUp,self.entryDown)
        print(self.exitUp,self.exitDown)
        # 判断是否进行交易，只发开仓单
        if not self.buyOrderID or self.buyOrderID in self.orderList:
            if self.pos == 0:
                if not self.longEntry:
                    # if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                    #     print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
                    #     return
                    self.longEntry = self.entryUp

                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, True)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    self.orderList.append(self.buyOrderID)

                elif self.longEntry != self.entryUp:
                    self.cancel_order(self.buyOrderID)
                    # if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                    #     print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
                    #     return
                    self.longEntry = self.entryUp

                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, True)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    self.orderList.append(self.buyOrderID)

        if not self.shortOrderID or self.shortOrderID in self.orderList:
            if self.pos == 0:
                if not self.shortEntry:
                    # if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                    #     print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
                    #     return
                    self.shortEntry = self.entryDown

                    self.shortOrderID = self.short(self.shortEntry, self.fixedSize, True)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    self.orderList.append(self.shortOrderID)

                elif self.shortEntry != self.entryDown:
                    self.cancel_order(self.shortOrderID)
                    # if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
                    #     print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
                    #     return
                    self.shortEntry = self.entryDown

                    self.shortOrderID = self.short(self.shortEntry, self.fixedSize, True)
                    self.shortOrderID = self.orderIDConvert(self.shortOrderID)
                    self.orderList.append(self.shortOrderID)

        # 发出状态更新事件
        # self.put_event()        

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

        # if self.sellOrderID:
        #     if order.orderID == self.sellOrderID.split('.')[1]:
        #         if order.status == STATUS_CANCELLED:
        #             self.sellOrderID =  self.sell(self.longExit, self.fixedSize, False)
        #             print u'###多头平仓，单号：%s' % self.sellOrderID
        #             self.sellOrderID = self.orderIDConvert(self.sellOrderID)
        # if self.coverOrderID:
        #     if order.orderID == self.coverOrderID.split('.')[1]:
        #         if order.status == STATUS_CANCELLED:
        #             self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, False)
        #             print u'###空头平仓，单号：%s' % self.coverOrderID
        #             self.coverOrderID = self.orderIDConvert(self.coverOrderID)
        if order.offset in [Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY]:
            if order.status == Status.ALLTRADED:
                self.buyOrderID = None
                self.shortOrderID = None
                self.longExit = 0
                self.shortExit = 0

        pass

    #----------------------------------------------------------------------
    def on_trade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # print u'成交推送：%s' % trade.__dict__
        # if self.buyOrderID:
        #     if trade.tradeID == self.buyOrderID.split('.')[1]:
        #         self.orderList.remove(self.buyOrderID)

        # if self.shortOrderID:
        #     if trade.tradeID == self.shortOrderID.split('.')[1]:
        #         self.orderList.remove(self.shortOrderID)

        # 发出状态更新事件
        # self.put_event()
        pass

    #----------------------------------------------------------------------
    def on_stop_order(self, so):
        """停止单推送"""
        if so.offset == Offset.OPEN:
            if so.status == StopOrderStatus.CANCELLED or so.status == StopOrderStatus.TRIGGERED:
                self.orderList.remove(so.stopOrderID)

        # if so.offset in [OFFSET_CLOSE, OFFSET_CLOSETODAY, OFFSET_CLOSEYESTERDAY]:
        #     if self.sellOrderID:
        #         if so.orderID == self.sellOrderID.split('.')[1]:
        #             if so.status == STATUS_CANCELLED:
        #                 self.sellOrderID =  self.sell(self.longExit, self.fixedSize, True)
        #                 print u'###多头平仓，单号：%s' % self.sellOrderID
        #                 self.sellOrderID = self.orderIDConvert(self.sellOrderID)
        #     if self.coverOrderID:
        #         if so.orderID == self.coverOrderID.split('.')[1]:
        #             if so.status == STATUS_CANCELLED:
        #                 self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, True)
        #                 print u'###空头平仓，单号：%s' % self.coverOrderID
        #                 self.coverOrderID = self.orderIDConvert(self.coverOrderID)
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

