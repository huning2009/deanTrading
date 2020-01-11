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
from vnpy.app.cta_strategy.base import StopOrderStatus



########################################################################
class BollingerBotStrategy(CtaTemplate):
    """基于布林通道的交易策略"""
    className = 'BollingerBotStrategy'
    author = u'ForwardCapital'

    # 策略参数
    bollWindow = 28         # 通道窗口数
    entryDev = 3.2          # 开仓偏差
    exitDev = 1.2           # 平仓偏差
    trailingPrcnt = 0.4     # 移动止损百分比
    maWindow = 10           # 过滤用均线窗口
    initDays = 10           # 初始化数据所用的天数
    fixedSize = 1           # 每次交易的数量

    # 策略变量    
    bollMid = 0                         # 布林带中轨
    bollStd = 0                         # 布林带宽度
    entryUp = 0                         # 开仓上轨
    exitUp = 0                          # 平仓上轨    
    
    maFilter = 0                        # 均线过滤
    maFilter1 = 0                       # 上一期均线                   
    
    intraTradeHigh = 0                  # 持仓期内的最高点  
    longEntry = 0                       # 多头开仓
    longExit = 0                        # 多头平仓    
    
    orderList = []                      # 保存委托代码的列表
    buyOrderID = None
    sellOrderID = None

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'bollWindow',
                 'entryDev',
                 'exitDev',
                 'trailingPrcnt',
                 'maWindow',
                 'initDays',
                 'fixedSize']    

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'bollMid',
               'bollStd',
               'entryUp',
               'exitUp',
               'intraTradeHigh',
               'longEntry',
               'longExit']
    
    # 同步列表
    syncList = ['pos',
                'intraTradeHigh']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(BollingerBotStrategy, self).__init__(ctaEngine, setting)
        
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
    def onFiveBar(self, bar):
        """收到5分钟K线"""        
        # 保存K线数据
        self.am.update_bar(bar)
        if not self.am.inited or not self.trading:
            return        

        # 撤销之前发出的尚未成交的委托（包括限价单和停止单）
        # 计算指标数值
        self.bollMid = self.am.sma(self.bollWindow)
        self.bollStd = self.am.std(self.bollWindow)
        self.entryUp = self.bollMid + self.bollStd * self.entryDev
        self.exitUp = self.bollMid + self.bollStd * self.exitDev
        
        maArray = self.am.sma(self.maWindow, True)
        self.maFilter = maArray[-1]
        self.maFilter1 = maArray[-2]
        
        # 判断是否要进行交易
        if not self.buyOrderID:
            if self.pos == 0:
                self.intraTradeHigh = bar.high
                # 下开仓单
                if bar.close > self.maFilter and self.maFilter > self.maFilter1:
                    self.longEntry = self.entryUp
                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, True)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    print('order None!!!buyOrderID is : %s ' % self.buyOrderID)
                    self.orderList.append(self.buyOrderID)
                    # 下平仓单
                    self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt/100)
                    self.longExit = min(self.longExit, self.exitUp)
                    
                    self.sellOrderID = self.sell(self.longExit, abs(self.pos), True)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                    print('order None!!!ellOrderID is : %s ' % self.sellOrderID)
                    self.orderList.append(self.sellOrderID)
            elif self.pos > 0:
                self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
                # 下平仓单
                self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt/100)
                self.longExit = min(self.longExit, self.exitUp)
                
                self.sellOrderID = self.sell(self.longExit, abs(self.pos), True)
                self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                print('order None!!!sellOrderID is : %s ' % self.sellOrderID)
                self.orderList.append(self.sellOrderID)

        else:
            if self.buyOrderID in self.orderList:
                self.intraTradeHigh = bar.high
                self.cancel_all()
                # 下开仓单
                if bar.close > self.maFilter and self.maFilter > self.maFilter1:
                    self.longEntry = self.entryUp
                    self.buyOrderID = self.buy(self.longEntry, self.fixedSize, True)
                    print('buyOrderID is : %s ' % self.buyOrderID)
                    self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                    self.orderList.append(self.buyOrderID)
                    # 下平仓单
                    self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt/100)
                    self.longExit = min(self.longExit, self.exitUp)
                    
                    self.sellOrderID = self.sell(self.longExit, abs(self.pos), True)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                    print('sellOrderID is : %s ' % self.sellOrderID)
                    self.orderList.append(self.sellOrderID)
            else:
                if self.sellOrderID in self.orderList:                    
                    self.intraTradeHigh = max(self.intraTradeHigh, bar.high)
                    self.cancel_order(self.sellOrderID)
                    # 下平仓单
                    self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt/100)
                    self.longExit = min(self.longExit, self.exitUp)
                    
                    self.sellOrderID = self.sell(self.longExit, abs(self.pos), True)
                    self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                    print('sellOrderID is : %s ' % self.sellOrderID)
                    self.orderList.append(self.sellOrderID)
                else:
                    self.intraTradeHigh = bar.high
                    # 下开仓单
                    if bar.close > self.maFilter and self.maFilter > self.maFilter1:
                        self.longEntry = self.entryUp
                        self.buyOrderID = self.buy(self.longEntry, self.fixedSize, True)
                        self.buyOrderID = self.orderIDConvert(self.buyOrderID)
                        print('buyOrderID is : %s ' %self. buyOrderID)
                        self.orderList.append(self.buyOrderID)
                        # 下平仓单
                        self.longExit = self.intraTradeHigh * (1 - self.trailingPrcnt/100)
                        self.longExit = min(self.longExit, self.exitUp)
                        
                        self.sellOrderID = self.sell(self.longExit, abs(self.pos), True)
                        self.sellOrderID = self.orderIDConvert(self.sellOrderID)
                        print('sellOrderID is : %s ' % self.sellOrderID)
                        self.orderList.append(self.sellOrderID)

        # 发出状态更新事件
        # self.putEvent()        

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    #----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        self.put_event()

    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        print(u'StopOrder回报,stopOrderID:%s, status:%s' % (so.stopOrderID, so.status))
        if so.status == StopOrderStatus.CANCELLED or so.status == StopOrderStatus.TRIGGERED:
            self.orderList.remove(so.stopOrderID)
        pass