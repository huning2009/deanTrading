# encoding: UTF-8

'''
本文件包含了MMK引擎中的策略开发用模板，开发策略时需要继承MmkTemplate类。
'''
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
# import talib

from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtBarData

from mmkBase import *


########################################################################
class MmkTemplate(object):
    """MMK策略模板"""
    
    # 策略类的名称和作者
    className = 'MmkTemplate'
    author = EMPTY_UNICODE
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    
    # 策略的基本参数
    name = EMPTY_UNICODE           # 策略实例名称
    productClass = EMPTY_STRING    # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING        # 货币（只有IB接口需要）
    
    # 策略的基本变量，由引擎管理
    inited = False                 # 是否进行了初始化
    trading = False                # 是否启动交易，由引擎管理
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading']
    
    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = []

    #----------------------------------------------------------------------
    def __init__(self, mmkEngine, setting):
        """Constructor"""
        self.mmkEngine = mmkEngine
        self.vtSymbol = []

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    if key == 'vtSymbol':
                        d[key] = setting[key].split(',')
                    else:
                        d[key] = setting[key]

    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onDepth(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        raise NotImplementedError
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStopOrder(self, so):
        """收到停止单推送（必须由用户继承实现）"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def buy(self, vtSymbol, price, volume, stop=False):
        """买开"""
        return self.sendOrder(MMKORDER_BUY, vtSymbol, price, volume, stop)
    
    #----------------------------------------------------------------------
    def sell(self, vtSymbol, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(MMKORDER_SELL, vtSymbol, price, volume, stop)       

    #----------------------------------------------------------------------
    def short(self, vtSymbol, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(MMKORDER_SHORT, vtSymbol, price, volume, stop)          
 
    #----------------------------------------------------------------------
    def cover(self, vtSymbol, price, volume, stop=False):
        """买平"""
        return self.sendOrder(MMKORDER_COVER, vtSymbol, price, volume, stop)
        
    #----------------------------------------------------------------------
    def sendOrder(self, orderType, vtSymbol, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if price*volume < self.contractInfoDict[vtSymbol].minNotional:
                print 'MIN_NOTIONAL error'
                return [[]]
            if stop:
                vtOrderIDList = self.mmkEngine.sendStopOrder(vtSymbol, orderType, price, volume, self)
            else:
                vtOrderIDList = self.mmkEngine.sendOrder(vtSymbol, orderType, price, volume, self) 
            return vtOrderIDList
        else:
            # 交易停止时发单返回空字符串
            return [[]]
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 如果发单号为空字符串，则不进行后续操作
        if not vtOrderID:
            return
        
        if STOPORDERPREFIX in vtOrderID:
            self.mmkEngine.cancelStopOrder(vtOrderID)
        else:
            self.mmkEngine.cancelOrder(vtOrderID)
            
    #----------------------------------------------------------------------
    def cancelAll(self):
        """全部撤单"""
        self.mmkEngine.cancelAll(self.name)
    
    #----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.mmkEngine.insertData(self.tickDbName, self.vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.mmkEngine.insertData(self.barDbName, self.vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.mmkEngine.loadTick(self.tickDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.mmkEngine.loadBar(self.barDbName, self.vtSymbol, days)
    
    #----------------------------------------------------------------------
    def writeMmkLog(self, content):
        """记录MMK日志"""
        content = self.name + ':' + content
        self.mmkEngine.writeMmkLog(content)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.mmkEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """查询当前运行的环境"""
        return self.mmkEngine.engineType
    
    #----------------------------------------------------------------------
    def saveSyncData(self):
        """保存同步数据到数据库"""
        if self.trading:
            self.mmkEngine.saveSyncData(self)
    
   
