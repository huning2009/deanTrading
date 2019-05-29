# encoding: UTF-8

'''
vn.sec的gateway接入
'''

import os
import json
import time
from datetime import datetime
from copy import copy
from math import pow
from threading import Thread

from binanceApi import TradeApi, DataApi
from vnpy.trader.vtGateway import *
from vnpy.trader.vtFunction import getJsonPath, getTempPath


# 方向类型映射
directionMap = {}
directionMap[DIRECTION_LONG] = 'BUY'
directionMap[DIRECTION_SHORT] = 'SELL'
directionMapReverse = {v: k for k, v in directionMap.items()}

# 委托状态映射
statusMap = {}
statusMap[STATUS_ALLTRADED] = 'FILLED'
statusMap[STATUS_PARTTRADED] = 'PARTIALLY_FILLED'
statusMap[STATUS_NOTTRADED] = 'NEW'
statusMap[STATUS_CANCELLED] = 'CANCELED'
statusMapReverse = {v:k for k,v in statusMap.items()}

EXCHANGE_BINANCE = 'BINANCE'         # 币安比特币交易所
EVENT_ORDERSTATUS = 'eOrderStatus.'
EVENT_DEPTH = 'eDepth.'
EVENT_DETAIL = 'eDetail.'
#----------------------------------------------------------------------
def print_dict(d):
    """"""
    print '-' * 30
    l = d.keys()
    l.sort()
    for k in l:
        print '%s:%s' %(k, d[k])
    

########################################################################
class BinanceGateway(VtGateway):
    """火币接口"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, gatewayName='BINANCE'):
        """Constructor"""
        super(BinanceGateway, self).__init__(eventEngine, gatewayName)
        
        self.dataApi = BinanceDataApi(self)       # 行情API
        self.tradeApi = BinanceTradeApi(self, self.dataApi)     # 交易API
        
        self.mdConnected = False        # 行情API连接状态，登录完成后为True
        self.tdConnected = False        # 交易API连接状态
        
        self.qryEnabled = False         # 是否要启动循环查询
        self.listenKey = None
        
        self.fileName = self.gatewayName + '_connect.json'
        self.filePath = getJsonPath(self.fileName, __file__)             
        
    #----------------------------------------------------------------------
    def connect(self):
        """连接"""       
        try:
            f = file(self.filePath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'get connect setting failed，please check json'
            self.onLog(log)
            return
        
        # 解析json文件
        setting = json.load(f)
        try:
            isSubUserData = setting['isSubUserData']
            accessKey = str(setting['accessKey'])
            secretKey = str(setting['secretKey'])
            proxyHost = str(setting['proxyHost'])
            proxyPort = int(setting['proxyPort'])
        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'connect setting lack field，please check json'
            self.onLog(log)
            return            
        
        # 创建行情和交易接口对象
        self.tradeApi.connect(accessKey, secretKey)
        time.sleep(1)
        self.dataApi.connect(self.tradeApi.listenKey, proxyHost, proxyPort, isSubUserData)
        
        # 初始化并启动查询
        self.initQuery()
    
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        self.dataApi.subscribe(subscribeReq)
        
    #----------------------------------------------------------------------
    # def creatConnection(self):
    #     self.dataApi.creatConnection()
    #----------------------------------------------------------------------
    def creatConnection(self):
        # self.dataApi.creatTickDepthConnection()
        self.dataApi.creatUserDepthConnection()
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        return self.tradeApi.sendOrder(orderReq)
        
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.tradeApi.cancelOrder(cancelOrderReq)
        
    #----------------------------------------------------------------------
    def qryInfo(self):
        """查询委托、成交、持仓"""
        # self.tradeApi.qryOrder()
        # self.tradeApi.qryTrade()
        self.tradeApi.qryPosition()
            
    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        if self.mdConnected:
            self.dataApi.close()
        if self.tdConnected:
            self.tradeApi.close()
        
    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryInfo]
            
            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 1         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引
            
            self.startQuery()
    
    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1
        
        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0
            
            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()
            
            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
    
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)
    
    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled

    #----------------------------------------------------------------------
    def onDepth(self, tick):
        """市场行情推送"""
        # 通用事件
        event1 = Event(type_=EVENT_DEPTH)
        event1.dict_['data'] = tick
        self.eventEngine.put(event1)
        
        # 特定合约代码的事件
        event2 = Event(type_=EVENT_DEPTH+tick.vtSymbol)
        event2.dict_['data'] = tick
        self.eventEngine.put(event2)

    #----------------------------------------------------------------------
    def onDetail(self, datail):
        """市场成交推送"""
        # 通用事件
        event1 = Event(type_=EVENT_DETAIL)
        event1.dict_['data'] = datail
        self.eventEngine.put(event1)
        
        # 特定合约代码的事件
        event2 = Event(type_=EVENT_DETAIL+datail.vtSymbol)
        event2.dict_['data'] = datail
        self.eventEngine.put(event2)

    #----------------------------------------------------------------------
    def onOrderStatus(self, orderStatusDict):
        """挂单list推送"""
        # 通用事件
        event1 = Event(type_=EVENT_ORDERSTATUS)
        event1.dict_['data'] = orderStatusDict
        self.eventEngine.put(event1)
        
        # 特定合约代码的事件
        event2 = Event(type_=EVENT_ORDERSTATUS+datail.vtSymbol)
        event2.dict_['data'] = orderStatusDict
        self.eventEngine.put(event2)
    #----------------------------------------------------------------------


########################################################################
class BinanceDataApi(DataApi):
    """行情API实现"""

    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        super(BinanceDataApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.gatewayName = gateway.gatewayName  # gateway对象名称

        self.connectionStatus = False       # 连接状态
        
        self.tickDict = {}
        self.detailDict = {}
        self.depthDict = {}
        self.posDict = {}

        self.subscribeDict = {}
        
    #----------------------------------------------------------------------
    def connect(self, listenKey, proxyHost=None, proxyPort=None, isSubUserData=True):
        """连接服务器"""
        # url = 'wss://stream.binance.com:9443'
        
        self.connectionStatus = super(BinanceDataApi, self).connect(listenKey, proxyHost, proxyPort, isSubUserData)
        self.gateway.mdConnected = True
        
        if self.connectionStatus:
            self.writeLog(u'data server connect successfully')
            
            # 订阅所有之前订阅过的行情
            for req in self.subscribeDict.values():
                self.subscribe(req)
        else:
            self.writeLog(u'data server connect failed!')
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅合约"""
        self.subscribeDict[subscribeReq.symbol] = subscribeReq
        
        if not self.connectionStatus:
            return
        
        symbol = subscribeReq.symbol
        if symbol in self.tickDict:
            return
        
        tick = VtTickData()
        tick.gatewayName = self.gatewayName
        tick.symbol = symbol
        tick.exchange = EXCHANGE_BINANCE
        tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
        self.tickDict[symbol] = tick

        detail = MarketDetail()
        detail.symbol = symbol
        detail.exchange = EXCHANGE_BINANCE
        detail.vtSymbol = '.'.join([detail.symbol, detail.exchange])
        self.detailDict[symbol] = detail

        depth = VtTickData()
        depth.symbol = symbol
        depth.exchange = EXCHANGE_BINANCE
        depth.vtSymbol = '.'.join([depth.symbol, depth.exchange])
        self.depthDict[symbol] = depth
        
        # self.subscribeMarketDepth(symbol)
        # self.subscribeMarketDetail(symbol)
        # self.subscribeSymbolTicker(symbol)
        
    #----------------------------------------------------------------------
    def creatUserDepthConnection(self):
        url = self.endpoint + '/stream?streams=%s' % self.listenKey
        for symbol in self.subscribeDict:
            url += '/%s@depth5/%s@aggTrade' % (symbol.lower(), symbol.lower())

        print 'creatUserDepthConnection:%s' % url
        self.connectUrl(url)
    #----------------------------------------------------------------------
    def creatTickDepthConnection(self):
        if self.isSubUserData:
            url = self.endpoint + '/stream?streams=%s' % self.listenKey
            for symbol in self.subscribeDict:
                url += '/%s@ticker/%s@depth5' % (symbol.lower(), symbol.lower())
        else:
            url = self.endpoint + '/stream?streams='
            for symbol in self.subscribeDict:
                url += '/%s@ticker/%s@depth5' % (symbol.lower(), symbol.lower())


        print 'creatTickDepthConnection:%s' % url
        self.connectUrl(url)
    #----------------------------------------------------------------------
    def writeLog(self, content):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)
        
    #----------------------------------------------------------------------
    def onError(self, msg):
        """错误推送"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = 'DataEngine'
        err.errorMsg = msg
        self.gateway.onError(err)
        
    #----------------------------------------------------------------------
    def onSymbolTicker(self, data):
        """symbol tick推送 """
        # print 'onSymbolTicker:%s' % data
        symbol = data['s']
        
        tick = self.tickDict.get(symbol, None)
        if not tick:
            return
        
        tick.datetime = datetime.fromtimestamp(data['E']/1000)
        # tick.date = tick.datetime.strftime('%Y%m%d')
        # tick.time = tick.datetime.strftime('%H:%M:%S.%f')
        
        tick.lastPrice = float(data['c'])
        tick.lastVolume = float(data['Q'])
        tick.volume = float(data['v'])
        tick.openPrice = float(data['o'])
        tick.highPrice = float(data['h'])
        tick.lowPrice = float(data['l'])
        tick.preClosePrice = float(data['x'])
        tick.bidPrice1 = float(data['b'])
        tick.bidVolume1 = float(data['B'])
        tick.askPrice1 = float(data['a'])
        tick.askVolume1 = float(data['A'])
            
        #print '-' * 50    
        #print 'ask5', tick.askPrice5, tick.askVolume5
        #print 'ask4', tick.askPrice4, tick.askVolume4
        #print 'ask3', tick.askPrice3, tick.askVolume3
        #print 'ask2', tick.askPrice2, tick.askVolume2
        #print 'ask1', tick.askPrice1, tick.askVolume1
        
        #print 'bid1', tick.bidPrice1, tick.bidVolume1        
        #print 'bid2', tick.bidPrice2, tick.bidVolume2
        #print 'bid3', tick.bidPrice3, tick.bidVolume3
        #print 'bid4', tick.bidPrice4, tick.bidVolume4
        #print 'bid5', tick.bidPrice5, tick.bidVolume5
        
        if tick.lastPrice:
            newtick = copy(tick)
            self.gateway.onTick(newtick)
    #----------------------------------------------------------------------
    def onMarketDepth(self, data):
        """行情深度推送 """
        symbol = data['symbol']
        
        depth = self.depthDict.get(symbol, None)
        if not depth:
            return

        depth.datetime = data['datetime']
        depth.lastUpdateId = data['lastUpdateId']
        bids = data['bids']
        for n in range(5):
            l = bids[n]
            depth.__setattr__('bidPrice' + str(n+1), float(l[0]))
            depth.__setattr__('bidVolume' + str(n+1), float(l[1]))
        
        asks = data['asks']    
        for n in range(5):
            l = asks[n]    
            depth.__setattr__('askPrice' + str(n+1), float(l[0]))
            depth.__setattr__('askVolume' + str(n+1), float(l[1]))
        
        #print '-' * 50    
        #for d in data['tick']['asks']:
            #print 'ask', d
            
        #for d in data['tick']['bids']:
            #print 'bid', d
            
        #print '-' * 50    
        #print 'ask5', tick.askPrice5, tick.askVolume5
        #print 'ask4', tick.askPrice4, tick.askVolume4
        #print 'ask3', tick.askPrice3, tick.askVolume3
        #print 'ask2', tick.askPrice2, tick.askVolume2
        #print 'ask1', tick.askPrice1, tick.askVolume1
        
        #print 'bid1', tick.bidPrice1, tick.bidVolume1        
        #print 'bid2', tick.bidPrice2, tick.bidVolume2
        #print 'bid3', tick.bidPrice3, tick.bidVolume3
        #print 'bid4', tick.bidPrice4, tick.bidVolume4
        #print 'bid5', tick.bidPrice5, tick.bidVolume5
        
        if depth.bidPrice2:
            newdepth = copy(depth)
            self.gateway.onDepth(newdepth)
            # if symbol == "ETHUSDT":
            #     print 'dataApi onMarketDepth:%s' % tick.__dict__
    
    #----------------------------------------------------------------------
    def onMyOrder(self, data):
        """symbol tick推送 """
        print 'binanceGateway onMyOrder=%s' % data
        order = VtOrderData()
        order.gatewayName = self.gatewayName
        order.symbol = data['s']
        order.exchange = EXCHANGE_BINANCE
        order.vtSymbol = '.'.join([order.symbol, order.exchange])
        order.orderID = data['i']
        # order.vtOrderID = '.'.join([self.gatewayName, order.orderID])   
        order.direction = directionMapReverse.get(data['S'], '')
        order.status = statusMapReverse.get(data['X'], '')

        if order.status == STATUS_CANCELLED:
            order.vtOrderID = data['C']
            order.volume = float(data['q']) - float(data['z'])

        elif order.status == STATUS_NOTTRADED:
            order.vtOrderID = data['c']
            order.volume = float(data['q'])
        
        else:
            order.vtOrderID = data['c']
            order.volume = float(data['l'])

        order.price = float(data['p'])
        self.gateway.onOrder(order)

        # if order.status == STATUS_CANCELLED:
        #     print 'onMyOrder cancel:%s' % data
    #----------------------------------------------------------------------
    def onMyTrade(self, data):
        """成交细节推送"""
        print 'binanceGateway onMyTrade:%s' % data
        trade = VtTradeData()
        trade.gatewayName = self.gatewayName
        
        # 保存代码和报单号
        trade.symbol = data['s']
        trade.exchange = EXCHANGE_BINANCE
        trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
        
        trade.status = statusMapReverse.get(data['X'], '')
        trade.tradeID = data['t']
        trade.vtTradeID = '_'.join([self.gatewayName, str(trade.tradeID)])
        
        trade.vtOrderID = data['c']         # Client order ID

        trade.orderID = data['i']
        # trade.vtOrderID = '.'.join([self.gatewayName, trade.orderID])
        
        # 方向
        trade.direction = directionMapReverse.get(data['S'], '')
                        
        # 价格、报单量等数值
        trade.price = float(data['p'])
        trade.volume = float(data['l'])
        trade.tradeTime = data['T']
        
        # 推送
        self.gateway.onTrade(trade)
    
    #----------------------------------------------------------------------
    def onAccountBalance(self, data):
        for d in data['B']:
            symbol = d['a']
            pos = self.posDict.get(symbol, None)

            if not pos:
                pos = VtPositionData()
                pos.gatewayName = self.gatewayName
                pos.symbol = d['a']
                pos.exchange = EXCHANGE_BINANCE
                pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
                pos.direction = DIRECTION_LONG
                pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])
                self.posDict[symbol] = pos
            
            pos.frozen = float(d['l'])
            pos.free = float(d['f'])
            pos.position = pos.free + pos.frozen
        
        for pos in self.posDict.values():
            if pos.position:
                # print pos.__dict__
                self.gateway.onPosition(pos)

    #----------------------------------------------------------------------
    def onMarketDetail(self, data):
        """市场细节推送"""
        symbol = data['symbol']
        detail = self.detailDict.get(symbol, None)
        if detail:
            detail.detailID = data['t']
            detail.detailPrice = float(data['p'])
            detail.detailVol = float(data['q'])
            
            if detail.detailVol:
                newDetail = copy(detail)
                self.gateway.onDetail(newDetail)

    
########################################################################
class MarketDetail(object):
    """市场成交细节数据"""
    def __init__(self):
        self.symbol = EMPTY_STRING
        self.vtSymbol = EMPTY_STRING
        self.exchange = EMPTY_STRING
        self.detailID = EMPTY_STRING
        self.detailPrice = EMPTY_STRING
        self.detailVol = EMPTY_STRING

class OrderBook(object):
    """订单簿"""
    def __init__(self):
        self.bidPriceList = []
        self.askPriceList = []
        self.bidVolList = []
        self.askVolList = []


########################################################################
class BinanceTradeApi(TradeApi):
    """交易API实现"""
    
    #----------------------------------------------------------------------
    def __init__(self, gateway, dataApi):
        """API对象的初始化函数"""
        super(BinanceTradeApi, self).__init__()
        
        self.gateway = gateway                  # gateway对象
        self.dataApi = dataApi
        self.__thread = Thread(target = self.__run)
        self.gatewayName = gateway.gatewayName  # gateway对象名称
        
        self.connectionStatus = False       # 连接状态
        self.accountid = ''
        self.listenKey = None
        
        self.todayDate = datetime.now().strftime('%Y-%m-%d')
        
        self.orderDict = {}                 # 缓存委托数据的字典
        self.posDict = {}             
        self.symbols = []                   # 所有交易代码的字符串集合
        
        self.qryTradeID = None  # 查询起始成交编号
        self.tradeIDs = set()   # 成交编号集合
        
        self.qryOrderID = None  # 查询起始委托编号
        
        self.localid = 200000       # 订单编号，10000为起始
        self.reqLocalDict = {}      # 请求编号和本地委托编号映射
        self.localOrderDict = {}    # 本地委托编号和交易所委托编号映射
        self.orderLocalDict = {}    # 交易所委托编号和本地委托编号映射
        self.cancelReqDict = {}     # 撤单请求字典
        
    #----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                for symbol in self.dataApi.tickDict:
                    self.getMarketDepth(symbol, 10)
                time.sleep(0.5)
            except:
                pass
    #----------------------------------------------------------------------
    def connect(self, accessKey, secretKey):
        """初始化连接"""
        if not self.connectionStatus:
            
            self.connectionStatus = self.init(accessKey, secretKey)
            self.gateway.tdConnected = True
            self.start()
            self.writeLog(u'trade server connect successfully')

            self.getListenKey()
            self.getTimestamp()
            self.getSymbols()

            self.__active = True
            self.__thread.start()

    #----------------------------------------------------------------------
    def qryPosition(self):
        """查询持仓"""
        self.getAccountBalance()
            
    #----------------------------------------------------------------------
    def qryOrder(self):
        """查询委托"""
        self.getCurrentOpenOrders()
    
    #----------------------------------------------------------------------
    def qryTrade(self):
        """查询成交"""
        if not self.accountid:
            return
        
        for symbol in self.symbols:
            self.getMatchResults(symbol, startDate=self.todayDate)
            #self.getMatchResults(symbol, startDate=self.todayDate, from_=self.qryTradeID)    
    
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        self.localid += 1
        localid = str(self.localid)
        vtOrderID = '_'.join([self.gatewayName, datetime.now().strftime("%H%M%S"), localid])
        
        if orderReq.direction == DIRECTION_LONG:
            side = 'BUY'
        else:
            side = 'SELL'

        if orderReq.price:
            type_= 'LIMIT'
        else:
            type_= 'MARKET'
        
        reqid = self.placeOrder(orderReq.symbol, side, str(orderReq.volume), str(orderReq.price), type_, newClientOrderId= vtOrderID)
        
        self.reqLocalDict[reqid] = localid
        # print 'gateway sendOrder:%s %s@%s' % (self.accountid, orderReq.volume, orderReq.price)
        # 返回订单号
        return vtOrderID
    
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        orderID = cancelOrderReq.orderID
        print 'BinanceGateway cancelOrder:%s' % (orderID)
        # orderID = self.localOrderDict.get(localid, None)
        
        if orderID:
            super(BinanceTradeApi, self).cancelOrder(cancelOrderReq.symbol, orderId=orderID)
            # if localid in self.cancelReqDict:
            #     del self.cancelReqDict[localid]
            # print 'BinanceGateway cancelOrder localid:%s' % orderID
        # else:
        #     self.cancelReqDict[localid] = cancelOrderReq
        
    #----------------------------------------------------------------------
    def writeLog(self, content):
        """发出日志"""
        log = VtLogData()
        log.gatewayName = self.gatewayName
        log.logContent = content
        self.gateway.onLog(log)

    #----------------------------------------------------------------------
    def onError(self, msg, reqid):
        """错误回调"""
        err = VtErrorData()
        err.gatewayName = self.gatewayName
        err.errorID = 'TradeEngine'
        err.errorMsg = msg
        self.gateway.onError(err)        
        
    #----------------------------------------------------------------------
    def onGetSymbols(self, data, reqid):
        """查询代码回调"""
        # print '*' * 50
        # print data.keys()
        # print data['symbols']
        # if data['symbols']['symbol'] == 'ETHUSDT':
        #     print 'onGetSymbols:' % data['symbols']
        for d in data['symbols']:
            if d['symbol'] == 'ETHUSDT':
                print '^' * 50
                print d
                print '^' * 50
                
            contract = VtContractData()
            contract.gatewayName = self.gatewayName
            
            contract.symbol = d['symbol']
            contract.exchange = EXCHANGE_BINANCE
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])
            
            contract.name = '_'.join([d['baseAsset'].upper(), d['quoteAsset'].upper()])
            contract.priceTick = float(d['filters'][0]['tickSize'])
            contract.size = float(d['filters'][1]['minQty'])
            contract.productClass = PRODUCT_SPOT
            contract.minNotional = float(d['filters'][2]['minNotional'])
            
            self.gateway.onContract(contract)
            # print '*' *30
            # print d
        self.writeLog(u'contract code query successfully')
        self.getAccount()
    
    #----------------------------------------------------------------------
    def onGetListenKey(self, data, reqid):
        """错误回调"""
        self.listenKey = data['listenKey']
    #----------------------------------------------------------------------
    def onGetCurrencys(self, data, reqid):
        """查询货币回调"""
        pass
    
    #----------------------------------------------------------------------
    def onGetTimestamp(self, data, reqid):
        """查询时间回调"""
        data = data['serverTime']
        # print 'onGetTimestamp!data:%s, type:%s' % (data, type(data))
        event = Event(EVENT_LOG+'Time')
        event.dict_['data'] = datetime.fromtimestamp(data/1000)
        self.gateway.eventEngine.put(event)
        print 'server time:%s, local time:%s' % (datetime.fromtimestamp(data/1000), datetime.now())
        
    #----------------------------------------------------------------------
    def onGetMarketDepth(self, data, reqid):
        """行情深度推送 """
        self.dataApi.onMarketDepth(data)
    #----------------------------------------------------------------------
    def onGetAccount(self, data, reqid):
        """查询账户回调"""

        self.writeLog(u'commission and balance query successfully, taker:%s, maker:%s' % (data['takerCommission'], data['takerCommission']))
        self.onGetAccountBalance(data, reqid)
    #----------------------------------------------------------------------
    def onGetAccountBalance(self, data, reqid):
        """查询余额回调"""
        # print 'onGetAccountBalance data:' + '^' * 30
        # print data
        for d in data['balances']:
            symbol = d['asset']
            pos = self.posDict.get(symbol, None)

            if not pos:
                pos = VtPositionData()
                pos.gatewayName = self.gatewayName
                pos.symbol = d['asset']
                pos.exchange = EXCHANGE_BINANCE
                pos.vtSymbol = '.'.join([pos.symbol, pos.exchange])
                pos.direction = DIRECTION_LONG
                pos.vtPositionName = '.'.join([pos.vtSymbol, pos.direction])
                self.posDict[symbol] = pos
            
            pos.frozen = float(d['locked'])
            pos.free = float(d['free'])            
            pos.position = pos.free + pos.frozen
                
        
        for pos in self.posDict.values():
            if pos.position:
                self.gateway.onPosition(pos)
                # print '*' *30
                # print 'gateway onPosition:%s' % pos.__dict__
    #----------------------------------------------------------------------
    def onGetOrders(self, data, reqid):
        """查询委托回调"""
        qryOrderID = None
        
        data.reverse()
        
        for d in data:
            orderID = d['id']
            strOrderID = str(orderID)
            updated = False
            
            if strOrderID in self.orderLocalDict:
                localid = self.orderLocalDict[strOrderID]
            else:
                self.localid += 1
                localid = str(self.localid)
                
                self.orderLocalDict[strOrderID] = localid
                self.localOrderDict[localid] = strOrderID
            
            order = self.orderDict.get(orderID, None)
            if not order:
                updated = True
                
                order = VtOrderData()
                order.gatewayName = self.gatewayName
                
                order.orderID = localid
                order.vtOrderID = '.'.join([order.gatewayName, order.orderID])
            
                order.symbol = d['symbol']
                order.exchange = EXCHANGE_BINANCE
                order.vtSymbol = '.'.join([order.symbol, order.exchange])
            
                order.price = float(d['price'])
                order.totalVolume = float(d['amount'])
                order.orderTime = datetime.fromtimestamp(d['created-at']/1000).strftime('%H:%M:%S')
                
                if 'buy' in d['type']:
                    order.direction = DIRECTION_LONG
                else:
                    order.direction = DIRECTION_SHORT
                order.offset = OFFSET_NONE  
                
                self.orderDict[orderID] = order
            
            # 数据更新，只有当成交数量或者委托状态变化时，才执行推送
            if d['canceled-at']:
                order.cancelTime = datetime.fromtimestamp(d['canceled-at']/1000).strftime('%H:%M:%S')
            
            newTradedVolume = d['field-amount']
            newStatus = statusMapReverse.get(d['state'], STATUS_UNKNOWN)
            
            if newTradedVolume != order.tradedVolume or newStatus != order.status:
                updated = True
                order.tradedVolume = float(newTradedVolume)
                order.status = newStatus
            
            # 只推送有更新的数据
            if updated:
                self.gateway.onOrder(order)
                # print 'gateway onOrder:%s' % order.__dict__
                
            # 计算查询下标（即最早的未全成或撤委托）
            if order.status not in [STATUS_ALLTRADED, STATUS_CANCELLED]:
                if not qryOrderID:
                    qryOrderID = orderID
                else:
                    qryOrderID = min(qryOrderID, orderID)
            
        # 更新查询下标        
        if qryOrderID:
            self.qryOrderID = qryOrderID
        
    #----------------------------------------------------------------------
    def onGetCurrentOpenOrders(self, data, reqid):
        """查询委托回调"""
        clientOrderID = []
        for order in data:
            clientOrderID.append(order.clientOrderId)

        if clientOrderID:
            self.gateway.onOpenOrderID(clientOrderID)
        
    #----------------------------------------------------------------------
    def onGetMatchResults(self, data, reqid):
        """查询成交回调"""
        # print 'gateway onGetMatchResults!data:%s' %data
        data.reverse()
        
        for d in data:
            tradeID = d['match-id']
            
            # 成交仅需要推送一次，去重判断
            if tradeID in self.tradeIDs:
                continue
            self.tradeIDs.add(tradeID)
            
            # 查询起始编号更新
            self.qryTradeID = max(tradeID, self.qryTradeID)
            
            # 推送数据            
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
            
            trade.tradeID = str(tradeID)
            trade.vtTradeID = '.'.join([trade.tradeID, trade.gatewayName])
            
            trade.symbol = d['symbol']
            trade.exchange = EXCHANGE_BINANCE
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
            
            if 'buy' in d['type']:
                trade.direction = DIRECTION_LONG
            else:
                trade.direction = DIRECTION_SHORT
            trade.offset = OFFSET_NONE
            
            strOrderID = str(d['order-id'])
            localid = self.orderLocalDict.get(strOrderID, '')
            trade.orderID = localid
            trade.vtOrderID = '.'.join([trade.gatewayName, trade.orderID])
            
            trade.tradeID = str(tradeID)
            trade.vtTradeID = '.'.join([trade.gatewayName, trade.tradeID])
            
            trade.price = float(d['price'])
            trade.volume = float(d['filled-amount'])
            
            dt = datetime.fromtimestamp(d['created-at']/1000)
            trade.tradeTime = dt.strftime('%H:%M:%S')
            
            self.gateway.onTrade(trade)
            # print 'gateway onTrade:%s' % trade.__dict__
        
    #----------------------------------------------------------------------
    def onGetOrder(self, data, reqid):
        """查询单一委托回调"""
        print 'binanceGateway:%s' % data
        if 'msg' in data:
            if 'Order does not exist' in data['msg']:
                vtSymbol = '.'.join([data['symbol'], self.gatewayName])
                clientOrderID = data['origClientOrderId']
                status = {'vtSymbol':vtSymbol, 'clientOrderID':clientOrderID}
                self.gateway.onOrderStatus(status)
        elif data['status'] == 'FILLED' or data['status'] == 'CANCELED':
            vtSymbol = '.'.join([data['symbol'], self.gatewayName])
            clientOrderID = data['origClientOrderId']
            status = {'vtSymbol':vtSymbol, 'clientOrderID':clientOrderID}
            self.gateway.onOrderStatus(status)
        # print reqid, data    
        
    #----------------------------------------------------------------------
    def onGetMatchResult(self, data, reqid):
        """查询单一成交回调"""
        print reqid, data    
        
    #----------------------------------------------------------------------
    def onPlaceOrder(self, data, reqid):
        """委托回调"""
        # print 'gateway onPlaceOrder callback:%s,data:%s' % (reqid,data)
        # localid = self.reqLocalDict[reqid]
        
        # self.localOrderDict[localid] = data
        # self.orderLocalDict[data] = localid
        
        # if localid in self.cancelReqDict:
        #     req = self.cancelReqDict[localid]
        #     self.cancelOrder(req)
        pass
    
    #----------------------------------------------------------------------
    def onCancelOrder(self, data, reqid):
        """撤单回调"""
        self.writeLog(u'cancel order successfully：%s' %data)      
        
    #----------------------------------------------------------------------
    def onBatchCancel(self, data, reqid):
        """批量撤单回调"""
        print reqid, data      
