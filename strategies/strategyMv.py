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
class MvStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'MvStrategy'
    author = u'ForwardCapital'

    # 策略参数
    mvWindow = 20
    tickN = 6              # 间隔tick数量
    tickCachN = 6               # 缓存tick数量

    # 策略变量    
    tickCount = 0
    askBidVol = []          # 缓存买卖价/成交量数据
    long_Mv = []             # 缓存买动量数据
    short_Mv = []             # 缓存卖动量数据
    sumLongMv = []
    sumShortMv = []
    
    orderList = []                      # 保存委托代码的列表
    buyOrderID = None
    sellOrderID = None
    shortOrderID = None
    coverOrderID = None

    minute = None
    timeFuncTurn = False


    # 参数列表，保存了参数的名称
    paramList = ['className', 'author', 'vtSymbol']    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'sellOrderID', 'coverOrderID', 'shortOrderID', 'buyOrderID', 'orderList']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(MvStrategy, self).__init__(ctaEngine, setting)
        
        # self.bm = MyBarGenerator(self.onBar, self.xMinBar, self.onFiveBar)
        # self.am = ArrayManager()

        # self.ctaEngine.eventEngine.register(EVENT_TIMER, self.onTimeFunc)
        
    #----------------------------------------------------------------------
    def on_init(self):
        """初始化策略（必须由用户继承实现）"""
        self.write_log(u'策略初始化')
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        #     self.onBar(bar)

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
    def updateMv(self, tick):
        if len(self.askBidVol) < self.tickCachN:
            if self.tickCount % self.tickN == 0:
                l = [tick.askPrice1, tick.bidPrice1, tick.volume]
                self.askBidVol.append(l)
                self.tickCount += 1
                return False
            else:
                self.tickCount += 1
                return False

        else:
            if self.tickCount % self.tickN == 0:
                l = [tick.askPrice1, tick.bidPrice1, tick.volume]
                self.askBidVol[:-1] = self.askBidVol[1:]
                self.askBidVol[-1] = l

                if not self.long_Mv:
                    for i in range(1,self.tickCachN,1):
                        lmv = (self.askBidVol[i][0] - self.askBidVol[i-1][0]) * (self.askBidVol[i][2]-self.askBidVol[i-1][2])
                        if lmv < 0:
                            lmv = 0
                        smv = (self.askBidVol[i][1] - self.askBidVol[i-1][1]) * (self.askBidVol[i][2]-self.askBidVol[i-1][2])
                        if smv > 0:
                            smv = 0
                        self.long_Mv.append(lmv)
                        self.short_Mv.append(smv)
                else:
                    self.long_Mv[:-1] = self.long_Mv[1:]
                    lmv = (self.askBidVol[-1][0] - self.askBidVol[-2][0]) * (self.askBidVol[-1][2]-self.askBidVol[-2][2])
                    if lmv < 0:
                        lmv = 0
                    self.long_Mv[-1] = lmv
                    
                    self.short_Mv[:-1] = self.short_Mv[1:]
                    smv = (self.askBidVol[-1][1] - self.askBidVol[-2][1]) * (self.askBidVol[-1][2]-self.askBidVol[-2][2])
                    if smv > 0:
                        smv = 0
                    self.short_Mv[-1] = smv

                self.tickCount += 1
                return True

            else:
                self.tickCount += 1
                return False

    #----------------------------------------------------------------------
    def on_tick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # self.bm.updateTick(tick)
        if not self.updateMv(tick):
            return

        # update sum Mv list
        slmv = sum(self.long_Mv)
        ssmv = sum(self.short_Mv)
        if len(self.sumLongMv) < self.mvWindow+1:
            self.sumLongMv.append(slmv)
            self.sumShortMv.append(ssmv)
            return
        else:
            self.sumLongMv[:-1] = self.sumLongMv[1:]
            self.sumLongMv[-1] = slmv
            self.sumShortMv[:-1] = self.sumShortMv[1:]
            self.sumShortMv[-1] = ssmv

        if slmv > max(self.sumLongMv[:-1])*2:
            slmvN = 0
            for i in self.long_Mv:
                if i > 0:
                    slmvN += 1 
            if slmvN > 2:
                print('%s: buy 1 at %s' % (dt.datetime.now(), tick.askPrice1))
        if ssmv < min(self.sumShortMv[:-1])*2:
            ssmvN = 0
            for i in self.short_Mv:
                if i < 0:
                    ssmvN += 1
            if ssmvN > 2:
                print('%s: short 1 at %s' % (dt.datetime.now(), tick.bidPrice1))

        # print dt.datetime.now()
        # print self.long_Mv
        # print self.short_Mv
        # print self.sumLongMv
        # print self.sumShortMv

    #----------------------------------------------------------------------
    def on_bar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # self.bm.updateBar(bar)

        # if not self.am.inited or not self.trading:
        #     return        

        # # 计算指标数值
        # self.exitUp = min(self.am.low[-self.turtleWindow/2:])
        # self.exitDown = max(self.am.high[-self.turtleWindow/2:])

        # # 只发平仓单
        # if self.pos > 0:
        #     if not self.longExit:
        #         self.longExit = self.exitDown

        #         if self.sellOrderID:
        #             self.cancelOrder(self.sellOrderID)
        #         else:
        #             self.cancelAll()

        #             self.sellOrderID =  self.sell(self.longExit, self.fixedSize, False)
        #             print u'None sellOrderID###多头平仓，单号：%s' % self.sellOrderID
        #             self.sellOrderID = self.orderIDConvert(self.sellOrderID)
        #     else:
        #         if self.longExit != self.exitDown:
        #             self.longExit = self.exitDown
        #             self.cancelOrder(self.sellOrderID)

        # elif self.pos < 0:
        #     if not self.shortExit:
        #         self.shortExit = self.exitUp
        #         if self.coverOrderID:
        #             self.cancelOrder(self.coverOrderID)
        #         else:
        #             self.cancelAll()

        #             self.coverOrderID =  self.cover(self.shortExit, self.fixedSize, False)
        #             print u'None coverOrderID###空头平仓，单号：%s' % self.coverOrderID
        #             self.coverOrderID = self.orderIDConvert(self.coverOrderID)
        #     else:
        #         if self.shortExit != self.exitUp:
        #             self.shortExit = self.exitUp
        #             self.cancelOrder(self.coverOrderID)
        pass
    
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
        # self.am.updateBar(bar)
        # if not self.am.inited or not self.trading:
        #     return        

        # # 计算指标数值
        # print u'highArray is ↓↓↓↓↓↓↓↓↓↓'
        # print self.am.high[-self.turtleWindow:]
        # print u'lowArray is ↓↓↓↓↓↓↓↓↓↓'
        # print self.am.low[-self.turtleWindow:]
        # self.entryUp = max(self.am.high[-self.turtleWindow:])
        # self.entryDown = min(self.am.low[-self.turtleWindow:])
        # # self.exitUp = min(self.am.low[-self.turtleWindow/2:])
        # # self.exitDown = max(self.am.high[-self.turtleWindow/2:])
        # # print u'entryup:%s, entryDown:%s' % (self.entryUp, self.entryDown)
        # # ma1 = self.am.sma(self.ma1Window, False)
        # # ma2 = self.am.sma(self.ma2Window, False)
        # # cci = self.am.cci(self.CCIWindow, True)

        # # 判断是否进行交易，只发开仓单
        # if not self.buyOrderID or self.buyOrderID in self.orderList:
        #     if self.pos == 0:
        #         if not self.longEntry:
        #             if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
        #                 print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
        #                 return
        #             self.longEntry = self.entryDown

        #             self.buyOrderID = self.buy(self.longEntry, self.fixedSize, False)
        #             self.buyOrderID = self.orderIDConvert(self.buyOrderID)
        #             self.orderList.append(self.buyOrderID)

        #         elif self.longEntry != self.entryDown:
        #             self.cancelOrder(self.buyOrderID)
        #             if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
        #                 print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
        #                 return
        #             self.longEntry = self.entryDown

        #             self.buyOrderID = self.buy(self.longEntry, self.fixedSize, False)
        #             self.buyOrderID = self.orderIDConvert(self.buyOrderID)
        #             self.orderList.append(self.buyOrderID)

        # if not self.shortOrderID or self.shortOrderID in self.orderList:
        #     if self.pos == 0:
        #         if not self.shortEntry:
        #             if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
        #                 print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
        #                 return
        #             self.shortEntry = self.entryUp

        #             self.shortOrderID = self.short(self.shortEntry, self.fixedSize, False)
        #             self.shortOrderID = self.orderIDConvert(self.shortOrderID)
        #             self.orderList.append(self.shortOrderID)

        #         elif self.shortEntry != self.entryUp:
        #             self.cancelOrder(self.shortOrderID)
        #             if (self.entryUp-self.entryDown)/self.entryUp < 0.006:
        #                 print u'%s 高低点太窄，放弃交易！' % self.vtSymbol
        #                 return
        #             self.shortEntry = self.entryUp

        #             self.shortOrderID = self.short(self.shortEntry, self.fixedSize, False)
        #             self.shortOrderID = self.orderIDConvert(self.shortOrderID)
        #             self.orderList.append(self.shortOrderID)

        # 发出状态更新事件
        # self.putEvent()    
        pass    

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

        # if trade.offset in [OFFSET_CLOSE, OFFSET_CLOSETODAY, OFFSET_CLOSEYESTERDAY]:
        #     self.buyOrderID = None
        #     self.shortOrderID = None
        #     self.longExit = 0
        #     self.shortExit = 0

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

        # if now_hour == 2 and now_minute == 32 and self.timeFuncTurn:
        #     self.ctaEngine.saveSyncData(self)
        #     self.timeFuncTurn = False

        # elif now_hour == 15 and now_minute == 10 and self.timeFuncTurn:
        #     self.buyOrderID = None
        #     self.shortOrderID = None
        #     self.coverOrderID = None
        #     self.sellOrderID = None
        #     self.longExit = 0
        #     self.shortExit = 0
        #     self.orderList = []
        #     self.ctaEngine.saveSyncData(self)
        #     self.timeFuncTurn = False

