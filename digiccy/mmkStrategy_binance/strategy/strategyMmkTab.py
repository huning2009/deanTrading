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
from mmkTemplate import *


EVENT_TIMER = 'eTimer' 
########################################################################
class MmkTabStrategy(MmkTemplate):
    """基于布林通道的交易策略"""
    className = 'MmkTabStrategy'
    author = u'ForwardCapital'

    # 策略参数
    mmkSpread = 0.0015
    tabSpread = 0.002
    maxSize = 0
    fixedSize = 0
    balanceRatio = 0.25
    # buyQuoteVol = 0
    # sellQuoteVol = 0
    # holdVol = 0
    # buyPrice = 0
    # sellPrice = float('inf')
    # lastTick = None                        # 多头平仓    
    
    # buyOrderDict = {}                      # 保存委托代码的列表
    # sellOrderDict = {}                      # 保存委托代码的列表
    # buyOrderID = None
    # sellOrderID = None
    # shortOrderID = None
    # coverOrderID = None
    # tradeID = 0
    # minute = None
    # timeFuncTurn = False
    minute = 0
    orderList = []
    # 参数列表，保存了参数的名称
    paramList = ['name', 'className', 'author', 'vtSymbol', 'mmkSpread', 'tabSpread', 'maxQuote', 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = []
    
    # 同步列表
    syncList = ['pos', 'orderList']

    #----------------------------------------------------------------------
    def __init__(self, mmkEngine, setting):
        """Constructor"""
        super(MmkTabStrategy, self).__init__(mmkEngine, setting)
        self.lastTickDict = {}
        self.legDict = {}                   # vtSymbol:TabLeg
        self.contractInfoDict = {}
        self.detailDict = {}
        self.tradeIDDick = {}

        self.tabPair = TabPair()
        print u'mmkSpread:%s, tabSpread:%s, maxQuote:%s, fixedSize:%s' % (self.mmkSpread, self.tabSpread, self.maxQuote, self.fixedSize)
        print u'vtSymbol:%s' % self.vtSymbol
        for n, vtsym in enumerate(self.vtSymbol):
            # 获取contract 信息
            self.contractInfoDict[vtsym] = self.mmkEngine.mainEngine.dataEngine.contractDict.get(vtsym)
            if self.contractInfoDict[vtsym]:
                print self.contractInfoDict[vtsym].__dict__

            # 创建tabPair的腿
            leg = Leg()
            leg.vtSymbol = vtsym
            leg.maxQuote = float(setting['maxQuote'].split(",")[n])
            if n == 0 or n ==1:
                leg.ratio = 1.0
            leg.baseSymbol = vtsym.split('.')[0][:3]
            leg.quoteSymbol = vtsym.split('.')[0][3:]
            # leg.multiplier = float(activeSetting['multiplier'])
            # leg.payup = int(activeSetting['payup'])
            self.legDict[vtsym] = leg            
            if n == 0:
                self.tabPair.addActiveLeg(leg)
            else:
                self.tabPair.addPassiveLeg(leg)
        # 初始化tabPair
        self.tabPair.initPair()

        self.lastDepth = None
    #----------------------------------------------------------------                                                                                                          ------
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
        self.mmkEngine.eventEngine.register(EVENT_TIMER, self.onTimeFunc)

        self.writeMmkLog(u'%s策略启动' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""

        self.writeMmkLog(u'%s策略停止' %self.name)
        self.putEvent()

    #----------------------------------------------------------------------
    def onTick(self, tick):
        print u'onTick!'
        """收到行情TICK推送（必须由用户继承实现）"""
        # leg = self.legDict[tick.vtSymbol]
        # leg.bidPrice1 = tick.bidPrice1
        # leg.bidVolume1 = tick.bidVolume1
        # leg.askPrice1 = tick.askPrice1
        # leg.askVolume1 = tick.askVolume1
        # leg.datetime = tick.datetime

        # self.tabPair.calculatePrice()

        # if self.tabPair.bidPrice < 1.0 - self.tabSpread and self.tabPair.bidPrice > 0:
        #     print 'tabPair.bidPrice:%s, askPrice:%s, less than %s' % (self.tabPair.bidPrice, self.tabPair.askPrice, 1.0 - self.tabSpread)
            # self.quoteBuyTabPair()

        # if self.tabPair.askPrice > 1.0 + self.tabSpread:
        #     print 'tabPair.bidPrice:%s, askPrice:%s, more than %s' % (self.tabPair.bidPrice, self.tabPair.askPrice, 1.0 + self.tabSpread)
            # self.quoteSellTabPair()

        # if (leg.askPrice1 - leg.bidPrice1)/leg.bidPrice1 > self.mmkSpread:
        #     print 'mmkTab %s: mmk spread is %s, more than %s' % (leg.vtSymbol, (leg.askPrice1 - leg.bidPrice1)/leg.bidPrice1, self.mmkSpread)




        """收到行情TICK推送（必须由用户继承实现）"""
        # if (tick.askPrice1 - tick.bidPrice1)/tick.bidPrice1 > self.spRatio:
        #     if self.buyQuoteVol+self.holdVol < self.maxSize and self.buyQuoteVol<self.maxSize:
        #         if self.buyPrice < tick.bidPrice1:
        #             if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
        #                 # print type(tick.bidPrice1+self.contractInfoDict.priceTick), type(self.fixedSize)
        #                 p = tick.bidPrice1+self.contractInfoDict.priceTick
        #                 vol = self.fixedSize + random.randint(-20, 20) * self.contractInfoDict.size
        #                 d = self.buy(p, vol)
        #                 self.buyOrderDict[d[0]] = [p, vol]
        #                 self.buyPrice = p
        #                 self.buyQuoteVol += vol
        #                 self.writeMmkLog(u'%s:%s buy %s@%s' % (self.name, d, vol, p))

        #     if self.sellQuoteVol-self.holdVol < self.maxSize and self.sellQuoteVol< self.maxSize:
        #         if self.sellPrice > tick.askPrice1:
        #             if not self.lastTick or tick.datetime.second != self.lastTick.datetime.second:
        #                 p = tick.askPrice1-self.contractInfoDict.priceTick
        #                 vol = self.fixedSize + random.randint(-20, 20) * self.contractInfoDict.size
        #                 d = self.sell(p, vol)
        #                 self.sellOrderDict[d[0]] = [p, vol]
        #                 self.sellPrice = p
        #                 self.sellQuoteVol += vol
        #                 self.writeMmkLog(u'%s:%s sell %s@%s' % (self.name, d, vol, p))

        # self.lastTick = tick

    #----------------------------------------------------------------------
    def onDepth(self, tick):
        """收到行情depth推送（必须由用户继承实现）"""
        # print 'strategy onDepth:%s' % tick
        leg = self.legDict[tick.vtSymbol]
        leg.calculatePriceAndVol(tick)

        self.tabPair.calculatePrice()

        # 先检验撤单，偏离一定范围，或者没有利润，或者三个里面两个被撤掉，则撤单
        if leg.buyOrderID:
            if leg.buyPrice < tick.bidPrice1*0.998:
                self.cancelOrder(leg.buyOrderID)
        elif leg.sellOrderID:
            if leg.sellPrice > tick.askPrice1*1.002:
                self.cancelOrder(leg.sellOrderID)
        pass
        # 如果价差足够大
        if self.tabPair.bidPrice < 1.0 - self.tabSpread and self.tabPair.bidPrice > 0:
            # 判断leg是否是牛熊市、是否有大的挂单、是否最新价格偏离上一个价格太远
            self.tabPair.calculateLegsTrendFarPriceLargeVol()
            # 无上述情况，打开tabpair的tradeTurn，进行交易
            if self.tabPair.tradeTurn:
                self.quoteBuyTabPair()
        
        self.lastDepth = tick
    #----------------------------------------------------------------------
    def onDetail(self, detail):
        """收到市场成交明细detail推送（必须由用户继承实现）"""
        # print 'strategy onDetail:%s' % detail
        leg = self.legDict[detail.vtSymbol]
        leg.calculateMarketDetailList(detail.detailPrice, detail.detailVol, detail.detailID)
        
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
        leg = self.legDict[order.vtSymbol]

        if order.status == STATUS_CANCELLED:
            if order.direction == DIRECTION_LONG:
                if order.vtOrderID == leg.buyOrderID:
                    leg.buyOrderID = EMPTY_STRING

            elif order.direction == DIRECTION_SHORT:
                if order.vtOrderID == leg.sellOrderID:
                    leg.sellOrderID = EMPTY_STRING

        # elif order.status == STATUS_NOTTRADED:
        #     if order.direction == DIRECTION_LONG:
        #         if order.vtOrderID == leg.buyOrderID:
        #             leg.quoteBuyVol = order.volume
        #         elif order.vtOrderID == leg.buyMmkOrderID:
        #             leg.quoteBuyMmkVol = order.volume

        #     elif order.direction == DIRECTION_SHORT:
        #         if order.vtOrderID == leg.sellOrderID:
        #             leg.quoteSellVol = order.volume
        #         elif order.vtOrderID == leg.sellMmkOrderID:
        #             leg.quoteSellMmkVol = order.volume
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # print u'成交推送：%s' % trade.__dict__
        leg = self.legDict[trade.vtSymbol]
        # 买成交回报
        if trade.direction == DIRECTION_LONG:
            if trade.vtOrderID == leg.buyOrderID:
                if trade.status == STATUS_ALLTRADED:
                    leg.buyOrderID = EMPTY_STRING
            elif trade.vtOrderID == leg.buyMmkOrderID:
                if trade.status == STATUS_ALLTRADED:
                    leg.buyMmkOrderID = EMPTY_STRING
            # else:
            #     self.buyOrderDict[trade.vtOrderID][1] -= trade.volume
        # 卖成交回报
        else:
            if trade.vtOrderID == leg.sellOrderID:
                if trade.status == STATUS_ALLTRADED:
                    leg.sellOrderID = EMPTY_STRING
            elif trade.vtOrderID == leg.sellMmkOrderID:
                if trade.status == STATUS_ALLTRADED:
                    leg.sellMmkOrderID = EMPTY_STRING

        # 发出状态更新事件
        # self.putEvent()
        pass

    #----------------------------------------------------------------------
    def onPos(self, pos):
        """收到持仓推送"""
        # for leg in self.posDict[pos.symbol]:
        #     if pos.symbol == leg.baseSymbol:
        #         leg.posBase = pos.position
        #     else:
        #         leg.posQuote = pos.position
        self.tabPair.calculateLegPos(pos.symbol, pos.position)

    #----------------------------------------------------------------------
    def onOrderStatus(self, orderStatus):
        print 'strategy onOrderStatus:%s' % orderStatus
        leg = self.legDict[orderStatus['vtSymbol']]
        if leg.buyOrderID == orderStatus['clientOrderID']:
            print 'clear %s:%s' % (orderStatus['vtSymbol'], orderStatus['clientOrderID'])
            leg.buyOrderID = EMPTY_STRING
        elif leg.sellOrderID == orderStatus['clientOrderID']:
            print 'clear %s:%s' % (orderStatus['vtSymbol'], orderStatus['clientOrderID'])
            leg.sellOrderID = EMPTY_STRING
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
        # for vtOrderID, priceAndVol in self.buyOrderDict.items():
        #     if priceAndVol[0] < self.lastTick.bidPrice1*0.998:
        #         # print 'onTimeFunc go on buy, cancelvtOrderID:%s' % vtOrderID
        #         self.cancelOrder(vtOrderID)
        #         self.buyOrderDict.pop(vtOrderID)
        #         print '*******MmkTabStrategy cancel Buyorder:%s, myPrice:%s, lastTick.bidPrice:%s, lastPrice:%s' % (vtOrderID, priceAndVol[0], self.lastTick.bidPrice1, self.lastTick.lastPrice)
        #         # p = self.lastTick.bidPrice1+self.contractInfoDict.priceTick
        #         # d = self.buy(p, priceAndVol[1])
        #         # self.buyPrice = p
        #         # self.buyOrderDict[d[0]] = [p, priceAndVol[1]]
        #         # self.buyOrderDict.pop(vtOrderID)

        # for vtOrderID, priceAndVol in self.sellOrderDict.items():
        #     if priceAndVol[0] > self.lastTick.askPrice1*1.002:
        #         # print 'onTimeFunc go on sell, cancelvtOrderID:%s' % vtOrderID
        #         self.cancelOrder(vtOrderID)
        #         self.sellOrderDict.pop(vtOrderID)
        #         print '*********MmkTabStrategy cancel Sellorder:%s, myPrice:%s, lastTick.askPrice1:%s, lastPrice:%s' % (vtOrderID, priceAndVol[0], self.lastTick.askPrice1, self.lastTick.lastPrice)
        #         # p = self.lastTick.askPrice1-self.contractInfoDict.priceTick
        #         # d = self.sell(p, priceAndVol[1])
        #         # self.sellPrice = p
        #         # self.sellOrderDict[d[0]] = [p, priceAndVol[1]]
        #         # self.sellOrderDict.pop(vtOrderID)

        # print '%s---%s' % (self.buyOrderDict, self.sellOrderDict)
        # if not self.buyOrderDict:
        #     self.buyPrice = 0
        # if not self.sellOrderDict:
        #     self.sellPrice = float('inf')
        # print 'buyQuoteVol:%s, sellQuoteVol:%s, holdVol:%s,---buyPrice:%s, sellPrice:%s' % (self.buyQuoteVol, self.sellQuoteVol, self.holdVol, self.buyPrice, self.sellPrice)
        now = dt.datetime.now()
        now_hour = now.hour
        now_minute = now.minute

        if self.minute != now_minute:
            self.minute = now_minute
            # print 'lastDepth:%s' % self.lastDepth.__dict__
            for leg in self.tabPair.allLegs:
                if leg.buyOrderID:
                    print '%s:%s is in leg' % (leg.vtSymbol, leg.buyOrderID)
                    self.mmkEngine.checkOrderStatus(leg.vtSymbol, leg.buyOrderID)
                if leg.sellOrderID:
                    print '%s:%s is in leg' % (leg.vtSymbol, leg.sellOrderID)
                    self.mmkEngine.checkOrderStatus(leg.vtSymbol, leg.sellOrderID)
        #     if not self.timeFuncTurn:
        #         self.timeFuncTurn = True

        # if now_hour == 2 and now_minute == 32 and self.timeFuncTurn:
        #     self.ctaEngine.saveSyncData(self)
        #     self.timeFuncTurn = False
        # pass

    #----------------------------------------------------------------------
    def quoteBuyTabPair(self):
        """报价买pair"""
        for n, leg in enumerate(self.tabPair.allLegs):
            print '^' * 50
            print 'leg%s:buyOrderID:%s, sellOrderID:%s' % (n, leg.buyOrderID, leg.sellOrderID)
            print self.tabPair.legsPos
            vol = self.fixedSize*leg.ratio
            if n == 0:
                # if leg.quoteBuyVol<vol and leg.quoteBuyVol+leg.holdVol<vol:
                if not leg.buyOrderID:
                    if self.tabPair.legsPos[leg.quoteSymbol][1]/self.tabPair.unifyPos > self.balanceRatio:
                        bp = leg.bidPrice1 + self.contractInfoDict[leg.vtSymbol].priceTick
                        buyOrderIDList = self.buy(leg.vtSymbol, bp, vol)
                        if buyOrderIDList:
                            print 'buy leg1:%s@%s' % (vol, bp)
                            leg.buyOrderID = buyOrderIDList[0]
                            leg.buyPrice = bp
                        # leg.buyOrderDict[buyOrderID] = p  
                        # 单腿对冲单
                        # sp = max(leg.bidPrice1*(1+self.mmkSpread), leg.askPrice1-self.contractInfoDict[leg.vtSymbol].priceTick)
                        # sellOrderIDList = self.sell(leg.vtSymbol, sp, vol)
                        # leg.sellMmkOrderID = sellOrderIDList[0]
                        # leg.quoteSellMmkVol += vol
                        # leg.sellMmkPrice = sp
                # else:
                #     # tabSpread很大，并且已经有挂单
                #     if leg.buyPrice < leg.bidPrice1:
                #         vol = leg.quoteBuyVol
                #         self.cancelOrder(leg.buyOrderID)
                #         print 'cancel leg1 orderID:%s' % leg.buyOrderID
                        
                        # 单腿对冲单
                        # self.cancelOrder(leg.sellMmkOrderID)
                        # sp = max(leg.bidPrice1*(1+self.mmkSpread), leg.askPrice1-self.contractInfoDict[leg.vtSymbol].priceTick)
                        # sellOrderID = self.sell(leg.vtSymbol, sp, self.fixedSize)
                        # leg.sellMmkOrderID = sellOrderID
                        # leg.quoteSellMmkVol += self.fixedSize
                        # leg.sellMmkPrice = sp
            else:
                # if leg.quoteSellVol<vol and leg.quoteSellVol-leg.holdVol<vol:
                if not leg.sellOrderID:
                    if self.tabPair.legsPos[leg.baseSymbol][1]/self.tabPair.unifyPos > self.balanceRatio:
                        sp = leg.askPrice1 - self.contractInfoDict[leg.vtSymbol].priceTick
                        sellOrderIDList = self.sell(leg.vtSymbol, sp, vol)
                        if sellOrderIDList:
                            print 'sell leg%s:%s@%s' % (n, vol, sp)
                            leg.sellOrderID = sellOrderIDList[0]
                            leg.sellPrice = sp
                        # leg.sellOrderDict[sellOrderID] = p 
                        # 单腿对冲单
                        # bp = min(leg.askPrice1*(1-self.mmkSpread), leg.bidPrice1+self.contractInfoDict[leg.vtSymbol].priceTick)
                        # buyOrderIDList = self.buy(leg.vtSymbol, bp, vol)
                        # leg.buyMmkOrderID = buyOrderIDList[0]
                        # leg.quoteBuyMmkVol += vol
                        # leg.buyMmkPrice = bp
                # else:
                #     # tabSpread很大，并且已经有挂单
                #     if leg.sellPrice > leg.askPrice1:
                #         vol = leg.quoteSellVol
                #         self.cancelOrder(leg.sellOrderID)
                #         print 'cancel leg%s orderID:%s' % (n, leg.sellOrderID)
                        
    #----------------------------------------------------------------------
    def quoteSellTabPair(self):
        """报价卖pair"""
        for n, leg in enumerate(self.tabPair.allLegs):
            print '^' * 50
            print 'leg%s:buyOrderID:%s, sellOrderID:%s' % (n, leg.buyOrderID, leg.sellOrderID)
            vol = self.fixedSize*leg.ratio
            if n == 0:
                # if leg.quoteBuyVol<vol and leg.quoteBuyVol+leg.holdVol<vol:
                if not leg.sellOrderID:
                    if self.tabPair.legsPos[leg.baseSymbol][1]/self.tabPair.unifyPos > self.balanceRatio:
                        sp = leg.askPrice1 - self.contractInfoDict[leg.vtSymbol].priceTick
                        sellOrderIDList = self.sell(leg.vtSymbol, bp, vol)
                        if sellOrderIDList:
                            print 'sell leg1:%s@%s' % (vol, sp)
                            leg.sellOrderID = sellOrderIDList[0]
                            leg.sellPrice = sp
            else:
                # if leg.quoteSellVol<vol and leg.quoteSellVol-leg.holdVol<vol:
                if not leg.buyOrderID:
                    if self.tabPair.legsPos[leg.quoteSymbol][1]/self.tabPair.unifyPos > self.balanceRatio:
                        bp = leg.bidPrice1 + self.contractInfoDict[leg.vtSymbol].priceTick
                        buyOrderIDList = self.buy(leg.vtSymbol, bp, vol)
                        if buyOrderIDList:
                            print 'buy leg%s:%s@%s' % (n, vol, bp)
                            leg.buyOrderID = buyOrderIDList[0]
                            leg.buyPrice = bp
        pass

