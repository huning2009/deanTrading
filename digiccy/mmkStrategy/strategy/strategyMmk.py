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
        self.contractInfo = self.mmkEngine.mainEngine.dataEngine.contractDict.get(self.vtSymbol)
        if self.contractInfo:
            print self.contractInfo.__dict__
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
            if self.buyQuoteVol+self.holdVol < self.maxSize:
                if self.buyPrice < tick.bidPrice1:
                    if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
                        # print type(tick.bidPrice1+self.contractInfo.priceTick), type(self.fixedSize)
                        p = tick.bidPrice1+self.contractInfo.priceTick
                        d = self.buy(p, self.fixedSize)
                        self.buyOrderDict[d[0]] = [p, self.fixedSize]
                        self.buyPrice = p
                        self.buyQuoteVol += self.fixedSize
                        self.writeMmkLog(u'%s:%s buy %s@%s' % (self.name, d, self.fixedSize, p))

            if self.sellQuoteVol-self.holdVol < self.maxSize:
                if self.sellPrice > tick.askPrice1:
                    if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
                        p = tick.askPrice1-self.contractInfo.priceTick
                        d = self.sell(p, self.fixedSize)
                        self.sellOrderDict[d[0]] = [p, self.fixedSize]
                        self.sellPrice = p
                        self.sellQuoteVol += self.fixedSize
                        self.writeMmkLog(u'%s:%s sell %s@%s' % (self.name, d, self.fixedSize, p))

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
        # print u'委托变化推送：%s' % order.__dict__
        if order.direction == DIRECTION_LONG:                
            if order.status in [STATUS_NOTTRADED, STATUS_PARTTRADED]:
                if order.vtOrderID in self.buyOrderDict:
                    self.buyOrderDict[order.vtOrderID][1] = order.totalVolume-order.tradedVolume

            elif order.status == STATUS_ALLTRADED:
                if order.vtOrderID in self.buyOrderDict:
                    self.buyOrderDict.pop(order.vtOrderID)

        else:
            if order.status in [STATUS_NOTTRADED, STATUS_PARTTRADED]:
                if order.vtOrderID in self.sellOrderDict:
                    self.sellOrderDict[order.vtOrderID][1] = order.totalVolume-order.tradedVolume

            elif order.status == STATUS_ALLTRADED:
                if order.vtOrderID in self.sellOrderDict:
                    self.sellOrderDict.pop(order.vtOrderID)

        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        print u'成交推送：%s' % trade.__dict__
        if trade.direction == DIRECTION_LONG:
            self.holdVol += trade.volume
            self.buyQuoteVol -= trade.volume
        else:
            self.holdVol -= trade.volume
            self.sellQuoteVol -= trade.volume
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
        print self.buyOrderDict, self.sellOrderDict
        print 'buyQuoteVol:%s, sellQuoteVol:%s, holdVol:%s' % (self.buyQuoteVol, self.sellQuoteVol, self.holdVol)
        if not self.buyOrderDict:
            buyPrice = 0
        if not self.sellOrderDict:
            sellPrice = float('inf')

        for orderID, priceAndVol in self.buyOrderDict.items():
            if priceAndVol[0] < self.lastTick.bidPrice5:
                print 'onTimeFunc go on buy, cancelOrderID:%s' % orderID
                self.cancelOrder(orderID)
                p = self.lastTick.bidPrice1+self.contractInfo.priceTick
                d = self.buy(p, priceAndVol[1])
                self.buyPrice = p
                self.buyOrderDict[d[0]] = [p, priceAndVol[1]]
                self.buyOrderDict.pop(orderID)

        for orderID, priceAndVol in self.sellOrderDict.items():
            if priceAndVol[0] > self.lastTick.askPrice5:
                print 'onTimeFunc go on sell, cancelOrderID:%s' % orderID
                self.cancelOrder(orderID)
                p = self.lastTick.askPrice1-self.contractInfo.priceTick
                d = self.sell(p, priceAndVol[1])
                self.sellPrice = p
                self.sellOrderDict[d[0]] = [p, priceAndVol[1]]
                self.sellOrderDict.pop(orderID)


