# encoding: UTF-8

"""
海龟系统1的反策略，20天high的最高价卖出，10天low的最低价的买平。
限价单策略，同时发出20天high的最高价卖单和20天low的最低价买单。
如果成交，则撤掉反方向的开仓单，改挂平仓单
"""

from __future__ import division

# import talib
import numpy as np
from time import sleep
import datetime as dt
import random

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.vtConstant import *
from mmkTemplate import MmkTemplate


EVENT_TIMER = 'eTimer' 
########################################################################
class MmkStrategy(MmkTemplate):
    """基于布林通道的交易策略"""
    className = 'MmkStrategy'
    author = u'ForwardCapital'

    # 策略参数
    spRatio = 0.001
    maxSize = 0
    fixedSize = 0

    # 策略变量    
    buyQuoteVol = 0
    sellQuoteVol = 0
    holdVol = 0
    buyPrice = 0
    sellPrice = float('inf')
    lastTick = None                        # 多头平仓    
    
    buyOrderDict = {}                      # 保存委托代码的列表
    sellOrderDict = {}                      # 保存委托代码的列表
    # buyOrderID = None
    # sellOrderID = None
    # shortOrderID = None
    # coverOrderID = None

    # minute = None
    # timeFuncTurn = False

    orderList = []
    # 参数列表，保存了参数的名称
    paramList = ['name', 'className', 'author', 'vtSymbol', 'spRatio', 'maxSize', 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'orderList']

    #----------------------------------------------------------------------
    def __init__(self, mmkEngine, setting):
        """Constructor"""
        super(MmkStrategy, self).__init__(mmkEngine, setting)
        self.contractInfo = {}
        for vtsym in self.vtSymbol:
            self.contractInfo[vtsym] = self.mmkEngine.mainEngine.dataEngine.contractDict.get(vtsym)
        for vtsym in self.contractInfo:
            print self.contractInfo[vtsym].__dict__
            print self.spRatio, self.maxSize, self.fixedSize
        self.mmkEngine.eventEngine.register(EVENT_TIMER, self.onTimeFunc)
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeMmkLog(u'%s策略初始化' %self.name)
        
        # 载入历史数据，并采用回放计算的方式初始化策略数值
        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        #     self.onBar(bar)

        self.putEvent()

    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeMmkLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""

        self.writeMmkLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        if (tick.askPrice1 - tick.bidPrice1)/tick.bidPrice1 > self.spRatio:
            if self.buyQuoteVol+self.holdVol < self.maxSize and self.buyQuoteVol<self.maxSize:
                if self.buyPrice < tick.bidPrice1:
                    if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
                        # print type(tick.bidPrice1+self.contractInfo[tick.vtSymbol].priceTick), type(self.fixedSize)
                        p = tick.bidPrice1+self.contractInfo[tick.vtSymbol].priceTick
                        vol = self.fixedSize + random.randint(-20, 20) * self.contractInfo[tick.vtSymbol].size
                        d = self.buy(tick.vtSymbol, p, vol)
                        self.buyOrderDict[d[0]] = [p, vol]
                        self.buyPrice = p
                        self.buyQuoteVol += vol
                        self.writeMmkLog(u'%s:%s buy %s@%s' % (self.name, d, vol, p))

            if self.sellQuoteVol-self.holdVol < self.maxSize and self.sellQuoteVol< self.maxSize:
                if self.sellPrice > tick.askPrice1:
                    if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
                        p = tick.askPrice1-self.contractInfo[tick.vtSymbol].priceTick
                        vol = self.fixedSize + random.randint(-20, 20) * self.contractInfo[tick.vtSymbol].size
                        d = self.sell(tick.vtSymbol, p, vol)
                        self.sellOrderDict[d[0]] = [p, vol]
                        self.sellPrice = p
                        self.sellQuoteVol += vol
                        self.writeMmkLog(u'%s:%s sell %s@%s' % (self.name, d, vol, p))

        self.lastTick = tick

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        # self.bm.updateBar(bar)
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
        pass
        # 发出状态更新事件
        # self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        if order.status == STATUS_CANCELLED:
            # print u'cancel委托变化推送：%s' % order.__dict__
            if order.direction == DIRECTION_LONG:
                self.buyQuoteVol -= order.totalVolume
            elif order.direction == DIRECTION_SHORT:
                self.sellQuoteVol -= order.totalVolume

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # print u'成交推送：%s' % trade.__dict__
        if trade.direction == DIRECTION_LONG:
            self.holdVol += trade.volume
            self.buyQuoteVol -= trade.volume
            if abs(self.buyOrderDict[trade.vtOrderID][1] - trade.volume) < 0.00000001:
                self.buyOrderDict.pop(trade.vtOrderID)
            elif self.buyOrderDict[trade.vtOrderID][1] > trade.volume:
                self.buyOrderDict[trade.vtOrderID][1] -= trade.volume
        else:
            self.holdVol -= trade.volume
            self.sellQuoteVol -= trade.volume
            if abs(self.sellOrderDict[trade.vtOrderID][1] - trade.volume) < 0.00000001:
                self.sellOrderDict.pop(trade.vtOrderID)
            elif self.sellOrderDict[trade.vtOrderID][1] > trade.volume:
                self.sellOrderDict[trade.vtOrderID][1] -= trade.volume
        # 发出状态更新事件
        # self.putEvent()
        pass

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        # print u'StopOrder回报,stopOrderID:%s, status:%s' % (so.stopOrderID, so.status)
        # if so.status == STOPORDER_CANCELLED or so.status == STOPORDER_TRIGGERED:
        #     self.orderList.remove(so.stopOrderID)
        pass

    #----------------------------------------------------------------------
    def onTimeFunc(self, event):
        for vtOrderID, priceAndVol in self.buyOrderDict.items():
            if priceAndVol[0] < self.lastTick.bidPrice1*0.998:
                # print 'onTimeFunc go on buy, cancelvtOrderID:%s' % vtOrderID
                self.cancelOrder(vtOrderID)
                self.buyOrderDict.pop(vtOrderID)
                print '*******MmkStrategy cancel Buyorder:%s, myPrice:%s, lastTick.bidPrice:%s, lastPrice:%s' % (vtOrderID, priceAndVol[0], self.lastTick.bidPrice1, self.lastTick.lastPrice)
                # p = self.lastTick.bidPrice1+self.contractInfo[tick.vtSymbol].priceTick
                # d = self.buy(p, priceAndVol[1])
                # self.buyPrice = p
                # self.buyOrderDict[d[0]] = [p, priceAndVol[1]]
                # self.buyOrderDict.pop(vtOrderID)

        for vtOrderID, priceAndVol in self.sellOrderDict.items():
            if priceAndVol[0] > self.lastTick.askPrice1*1.002:
                # print 'onTimeFunc go on sell, cancelvtOrderID:%s' % vtOrderID
                self.cancelOrder(vtOrderID)
                self.sellOrderDict.pop(vtOrderID)
                print '*********MmkStrategy cancel Sellorder:%s, myPrice:%s, lastTick.askPrice1:%s, lastPrice:%s' % (vtOrderID, priceAndVol[0], self.lastTick.askPrice1, self.lastTick.lastPrice)
                # p = self.lastTick.askPrice1-self.contractInfo[tick.vtSymbol].priceTick
                # d = self.sell(p, priceAndVol[1])
                # self.sellPrice = p
                # self.sellOrderDict[d[0]] = [p, priceAndVol[1]]
                # self.sellOrderDict.pop(vtOrderID)

        print '%s---%s' % (self.buyOrderDict, self.sellOrderDict)
        if not self.buyOrderDict:
            self.buyPrice = 0
        if not self.sellOrderDict:
            self.sellPrice = float('inf')
        print 'buyQuoteVol:%s, sellQuoteVol:%s, holdVol:%s,---buyPrice:%s, sellPrice:%s' % (self.buyQuoteVol, self.sellQuoteVol, self.holdVol, self.buyPrice, self.sellPrice)



