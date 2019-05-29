# encoding: UTF-8

'''
本文件中包含了MMK模块中用到的一些基础设置、类和常量等。
'''
import datetime
import copy
import numpy as np
# MMK引擎中涉及的数据类定义
from vnpy.trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

# 常量定义
# MMK引擎中涉及到的交易方向类型
MMKORDER_BUY = u'买开'
MMKORDER_SELL = u'卖平'
MMKORDER_SHORT = u'卖开'
MMKORDER_COVER = u'买平'

# 本地停止单状态
STOPORDER_WAITING = u'等待中'
STOPORDER_CANCELLED = u'已撤销'
STOPORDER_TRIGGERED = u'已触发'

# 本地停止单前缀
STOPORDERPREFIX = 'MmkStopOrder.'

# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
POSITION_DB_NAME = 'VnTrader_Position_Db'

TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'

# 引擎类型，用于区分当前策略的运行环境
ENGINETYPE_BACKTESTING = 'backtesting'  # 回测
ENGINETYPE_TRADING = 'trading'          # 实盘

# MMK模块事件
EVENT_MMK_LOG = 'eMmkLog'               # MMK相关的日志事件
EVENT_MMK_STRATEGY = 'eMmkStrategy.'    # MMK策略状态变化事件


########################################################################
class StopOrder(object):
    """本地停止单"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT
        
        self.strategy = None             # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号 
        self.status = EMPTY_STRING       # 停止单状态

########################################################################
class Leg(object):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING      # 代码
        self.baseSymbol = EMPTY_STRING      # 代码
        self.quoteSymbol = EMPTY_STRING      # 代码
        self.maxQuote = EMPTY_FLOAT         
        self.ratio = EMPTY_FLOAT          # 实际交易时的比例
        # self.buyMultiplier = EMPTY_FLOAT   # 计算价差时的乘数
        # self.sellMultiplier = EMPTY_FLOAT   # 计算价差时的乘数
        self.payup = EMPTY_INT          # 对冲时的超价tick
        self.datetime = EMPTY_INT          # 对冲时的超价tick
        self.tradeID = EMPTY_INT          
        
        self.bidPrice1 = EMPTY_FLOAT
        # self.bidPrice2 = EMPTY_FLOAT
        # self.bidPrice3 = EMPTY_FLOAT
        # self.bidPrice4 = EMPTY_FLOAT
        # self.bidPrice5 = EMPTY_FLOAT
        
        self.askPrice1 = EMPTY_FLOAT
        # self.askPrice2 = EMPTY_FLOAT
        # self.askPrice3 = EMPTY_FLOAT
        # self.askPrice4 = EMPTY_FLOAT
        # self.askPrice5 = EMPTY_FLOAT        
        
        self.bidVolume1 = EMPTY_FLOAT
        # self.bidVolume2 = EMPTY_FLOAT
        # self.bidVolume3 = EMPTY_FLOAT
        # self.bidVolume4 = EMPTY_FLOAT
        # self.bidVolume5 = EMPTY_FLOAT
        
        self.askVolume1 = EMPTY_FLOAT
        # self.askVolume2 = EMPTY_FLOAT
        # self.askVolume3 = EMPTY_FLOAT
        # self.askVolume4 = EMPTY_FLOAT
        # self.askVolume5 = EMPTY_FLOAT
        
        self.buyPrice = 0
        self.sellMmkPrice = 0
        self.sellPrice = float('inf')
        self.buyMmkPrice = 0

        self.buyOrderID = EMPTY_STRING                   # 保存委托代码的列表
        self.sellMmkOrderID = EMPTY_STRING                   # 保存委托代码的列表
        self.sellOrderID = EMPTY_STRING                      # 保存委托代码的列表
        self.buyMmkOrderID = EMPTY_STRING                      # 保存委托代码的列表

        # self.quoteBuyVol = EMPTY_FLOAT
        # self.quoteSellMmkVol = EMPTY_FLOAT
        # self.quoteSellVol = EMPTY_FLOAT
        # self.quoteBuyMmkVol = EMPTY_FLOAT

        # self.holdVol = EMPTY_FLOAT
        # self.posBase = EMPTY_FLOAT
        # self.posQuote = EMPTY_FLOAT

        self.marketDetailPriceList = []
        self.marketDetailQtyList = []

        self.isBullTrend = False
        self.isBearTrend = False
        self.lastPriceTooFarFromLatest = False
        self.hasLargeVolTrade = False

        self.bidPriceList = np.zeros(5)
        self.bidVolList = np.zeros(5)
        self.askPriceList = np.zeros(5)
        self.askVolList = np.zeros(5)

        # self.lastTick = None

    def calculatePriceAndVol(self, tick):
        self.bidPrice1 = tick.bidPrice1
        # self.bidPrice2 = tick.bidPrice2
        # self.bidPrice3 = tick.bidPrice3
        # self.bidPrice4 = tick.bidPrice4
        # self.bidPrice5 = tick.bidPrice5
        
        self.askPrice1 = tick.askPrice1
        # self.askPrice2 = tick.askPrice2
        # self.askPrice3 = tick.askPrice3
        # self.askPrice4 = tick.askPrice4
        # self.askPrice5 = tick.askPrice5        
        
        self.bidVolume1 = tick.bidVolume1
        # self.bidVolume2 = tick.bidVolume2
        # self.bidVolume3 = tick.bidVolume3
        # self.bidVolume4 = tick.bidVolume4
        # self.bidVolume5 = tick.bidVolume5
        
        self.askVolume1 = tick.askVolume1
        # self.askVolume2 = tick.askVolume2
        # self.askVolume3 = tick.askVolume3
        # self.askVolume4 = tick.askVolume4
        # self.askVolume5 = tick.askVolume5
        
        for i in range(5):
            self.bidPriceList[i] = tick.__getattribute__('bidPrice'+str(i+1))
            self.askPriceList[i] = tick.__getattribute__('askPrice'+str(i+1))
            self.bidVolList[i] = tick.__getattribute__('bidVolume'+str(i+1))
            self.askVolList[i] = tick.__getattribute__('askVolume'+str(i+1))           
    # def calculateMarketDetailStatus(self):
    #     if len(self.marketDetailQtyList) > 4:
    #         pass
    #     else:
    #         self.buyMultiplier = EMPTY_FLOAT
    #         self.sellMultiplier = EMPTY_FLOAT

    def calculateMarketDetailList(self, price, qty, tradeID):
        if self.tradeID < tradeID:
            if len(self.marketDetailQtyList) > 9:
                self.marketDetailPriceList = self.marketDetailPriceList[:-1]
                self.marketDetailPriceList[-1] = price
                self.marketDetailQtyList = self.marketDetailQtyList[:-1]
                self.marketDetailQtyList[-1] = qty
            else:
                self.marketDetailPriceList.append(price)
                self.marketDetailQtyList.append(qty)

            self.tradeID = tradeID
        else:
            print 'leg calculateMarketDetailList:%s tradeID:%s,%s' % (self.vtSymbol, type(tradeID), tradeID)

########################################################################
class TabPair(object):
    """"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.name = EMPTY_UNICODE       # 名称
        self.symbol = EMPTY_STRING      # 代码（基于组成腿计算）
        self.algoName = EMPTY_STRING
        
        self.activeLeg = None           # 主动腿
        self.passiveLegs = []           # 被动腿（支持多条）
        self.allLegs = []               # 所有腿
        
        self.bidPrice = EMPTY_FLOAT
        self.askPrice = EMPTY_FLOAT
        self.bidVolume = EMPTY_INT
        self.askVolume = EMPTY_INT
        self.time = EMPTY_STRING

        self.buyPrice = EMPTY_FLOAT
        self.sellPrice = EMPTY_FLOAT
        self.maxOrderSize = EMPTY_FLOAT
        self.longPos = EMPTY_INT
        self.shortPos = EMPTY_INT
        self.netPos = EMPTY_INT

        self.legsPos = {}
        self.unifyPos = EMPTY_FLOAT
        self.tradeTurn = False
        
    #----------------------------------------------------------------------
    def initPair(self):
        """初始化价差"""
        # 价差最少要有一条主动腿
        if not self.activeLeg:
            return
        
        # 生成所有腿列表
        self.allLegs.append(self.activeLeg)
        self.allLegs.extend(self.passiveLegs)
        
        # 生成价差代码
        # legSymbolList = []
        
        # for leg in self.allLegs:
        #     if leg.multiplier >= 0:
        #         legSymbol = '+%s*%s' %(leg.multiplier, leg.vtSymbol)
        #     else:
        #         legSymbol = '%s*%s' %(leg.multiplier, leg.vtSymbol)
        #     legSymbolList.append(legSymbol)
        
        # self.symbol = ''.join(legSymbolList)
        
    #----------------------------------------------------------------------
    def calculateLegsTrendFarPriceLargeVol(self):
        print 'TabPair judge bull bear farPrice largeVol'
        for n, leg in enumerate(self.allLegs):
            l = copy.copy(leg.marketDetailPriceList)
            l.append((leg.bidPriceList[0]+leg.askPriceList[0])/2.0*0.7+(leg.bidPriceList[1]+leg.askPriceList[1])/2.0*0.2+(leg.bidPriceList[3]+leg.askPriceList[3])/2.0*0.1)
            print 'calculateLegsTrendFarPriceLargeVol: l=%s' % l
            # 判断此leg是否是牛熊市
            # if l[-1] > max(l[:-1])+l[-1]*0.0005 or (l[-1]>max(l[:-2])+l[-1]*0.0005 and l[-1]>l[-2]):
            #     leg.isBullTrend = True
            #     self.tradeTurn = False
            #     print '%s:bull trend' % leg.vtSymbol
            #     return
            # else:
            #     leg.isBullTrend = False
            # if l[-1] > min(l[:-1])-l[-1]*0.0005 or (l[-1]>min(l[:-2])-l[-1]*0.0005 and l[-1]<l[-2]):
            #     leg.isBearTrend = True
            #     self.tradeTurn = False
            #     print '%s:bear trend' % leg.vtSymbol
            #     return
            # else:
            #     leg.isBearTrend = False
            # 判断此leg是否有大量挂单
            # if max(leg.bidVolList) > leg.maxQuote or max(leg.askVolList) > leg.maxQuote:
            #     leg.hasLargeVolTrade = True
            #     self.tradeTurn = False
            #     print '%s:largeVol' % leg.vtSymbol
            #     return
            # else:
            #     leg.hasLargeVolTrade = False
            # 判断此leg是否最新价偏离最近价格太远
            if abs(l[-1]-l[-2]*0.7-l[-3]*0.2-l[-4]*0.1)>l[-1]*0.002:
                leg.lastPriceTooFarFromLatest = True
                self.tradeTurn = False
                print '%s:far from latest price' % leg.vtSymbol
                return
            else:
                leg.lastPriceTooFarFromLatest = False

        self.tradeTurn = True
        pass
    #----------------------------------------------------------------------
    def calculatePrice(self):
        """计算价格"""
        # 清空价格和委托量数据
        self.bidPrice = EMPTY_FLOAT
        self.askPrice = EMPTY_FLOAT
        self.askVolume = EMPTY_INT
        self.bidVolume = EMPTY_INT
        # 遍历价差腿列表
        for n, leg in enumerate(self.allLegs):
            # 过滤有某条腿尚未初始化的情况（无挂单量）
            if not leg.bidVolume1 or not leg.askVolume1:
                self.bidPrice = EMPTY_FLOAT
                self.askPrice = EMPTY_FLOAT
                self.askVolume = EMPTY_INT
                self.bidVolume = EMPTY_INT      
                print 'TabPair leg not init!!!'          
                return
                
            # 计算价格
            if n == 0:
                self.bidPrice = leg.bidPrice1
                self.askPrice = leg.askPrice1
            else:
                self.bidPrice /= leg.askPrice1
                self.askPrice /= leg.bidPrice1
                
            # 计算报单倍数
            if n == 2:
                leg.ratio = self.allLegs[1].bidPrice1

            # if leg.ratio > 0:
            #     legAdjustedBidVolume = leg.bidVolume1 / leg.ratio
            #     legAdjustedAskVolume = leg.askVolume1 / leg.ratio
            # else:
            #     legAdjustedBidVolume = leg.askVolume1 / abs(leg.ratio)
            #     legAdjustedAskVolume = leg.bidVolume1 / abs(leg.ratio)
            
            # if n == 0:
            #     self.bidVolume = legAdjustedBidVolume                           # 对于第一条腿，直接初始化
            #     self.askVolume = legAdjustedAskVolume
            # else:
            #     self.bidVolume = min(self.bidVolume, legAdjustedBidVolume)      # 对于后续的腿，价差可交易报单量取较小值
            #     self.askVolume = min(self.askVolume, legAdjustedAskVolume)

            # if n == 2:
            #     leg.ratio = self.allLegs[1].bidPrice1
        # print 'TabPair calculatePrice bidPrice:%s, askPrice:%s' % (self.bidPrice, self.askPrice)
        # 更新时间
        self.time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

    #----------------------------------------------------------------------
    def calculateLegPos(self, symbol, position):
        """计算持仓"""
        # print 'TabPair calculateLegPos!!!!!'
        if symbol == self.allLegs[1].baseSymbol:
            r = self.allLegs[1].bidPrice1
        elif symbol == self.allLegs[2].quoteSymbol:
            if not self.allLegs[2].bidPrice1:
                r = 0
            else:
                r = 1.0/self.allLegs[2].bidPrice1
        else:
            r = 1.0
        self.legsPos[symbol] = [position, position*r]


        self.unifyPos = 0
        for l in self.legsPos.values():
            self.unifyPos += l[1]
        # if self.allLegs[0].holdVol > 0:
        #     if self.allLegs[1].holdVol < 0 and self.allLegs[2].holdVol < 0:
        #         x = min(self.allLegs[0].holdVol, abs(self.allLegs[1].holdVol), abs(self.allLegs[2].holdVol)/self.allLegs[2].ratio)
        #         self.allLegs[0].holdVol -= x
        #         self.allLegs[1].holdVol += x
        #         self.allLegs[2].holdVol += x*self.allLegs[2].ratio

        # else:
        #     if self.allLegs[1].holdVol > 0 and self.allLegs[2].holdVol > 0:
        #         x = min(abs(self.allLegs[0].holdVol), self.allLegs[1].holdVol, self.allLegs[2].holdVol/self.allLegs[2].ratio)
        #         self.allLegs[0].holdVol += x
        #         self.allLegs[1].holdVol -= x
        #         self.allLegs[2].holdVol -= x*self.allLegs[2].ratio
    
    #----------------------------------------------------------------------
    def addActiveLeg(self, leg):
        """添加主动腿"""
        self.activeLeg = leg
    
    #----------------------------------------------------------------------
    def addPassiveLeg(self, leg):
        """添加被动腿"""
        self.passiveLegs.append(leg)




