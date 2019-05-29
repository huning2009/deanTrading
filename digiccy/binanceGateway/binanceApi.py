# encoding: utf-8

import time
import urllib
import ssl
import hmac
import base64
import hashlib
import requests 
import traceback
from copy import copy
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
from operator import itemgetter
from multiprocessing.dummy import Pool
from ast import literal_eval as eval

import json
import zlib
from websocket import create_connection, _exceptions
from vnpy.trader.vtGateway import *


# 常量定义
TIMEOUT = 5
TIME_IN_FORCE_GTC = 'GTC'  # Good till cancelled
TIME_IN_FORCE_IOC = 'IOC'  # Immediate or cancel
TIME_IN_FORCE_FOK = 'FOK'  # Fill or kill

SIDE_BUY = 'BUY'
SIDE_SELL = 'SELL'

ORDER_TYPE_LIMIT = 'LIMIT'
ORDER_TYPE_MARKET = 'MARKET'
ORDER_TYPE_STOP_LOSS = 'STOP_LOSS'
ORDER_TYPE_STOP_LOSS_LIMIT = 'STOP_LOSS_LIMIT'
ORDER_TYPE_TAKE_PROFIT = 'TAKE_PROFIT'
ORDER_TYPE_TAKE_PROFIT_LIMIT = 'TAKE_PROFIT_LIMIT'
ORDER_TYPE_LIMIT_MAKER = 'LIMIT_MAKER'

ORDER_STATUS_NEW = 'NEW'
ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
ORDER_STATUS_FILLED = 'FILLED'
ORDER_STATUS_CANCELED = 'CANCELED'
ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
ORDER_STATUS_REJECTED = 'REJECTED'
ORDER_STATUS_EXPIRED = 'EXPIRED'

#----------------------------------------------------------------------
def order_params(data):
    """Convert params to list with signature as last element

    :param data:
    :return:

    """
    has_signature = False
    params = []
    for key, value in data.items():
        if key == 'signature':
            has_signature = True
        else:
            params.append((key, value))
    # sort parameters by key
    params.sort(key=itemgetter(0))
    if has_signature:
        params.append(('signature', data['signature']))
    return params
#----------------------------------------------------------------------

#----------------------------------------------------------------------
def createSign(params, method, host, path, secretKey):
    """创建签名"""
    sortedParams = sorted(params.items(), key=lambda d: d[0], reverse=False)
    encodeParams = urllib.urlencode(sortedParams)
    
    payload = [method, host, path, encodeParams]
    payload = '\n'.join(payload)
    payload = payload.encode(encoding='UTF8')

    secretKey = secretKey.encode(encoding='UTF8')

    digest = hmac.new(secretKey, payload, digestmod=hashlib.sha256).digest()

    signature = base64.b64encode(digest)
    signature = signature.decode()
    return signature    


########################################################################
class TradeApi(object):
    """交易API"""    
    SYNC_MODE = 'sync'
    ASYNC_MODE = 'async'

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.accessKey = ''
        self.secretKey = ''
    
        self.mode = self.ASYNC_MODE
        self.active = False         # API工作状态   
        self.reqid = 0              # 请求编号
        self.queue = Queue()        # 请求队列
        self.pool = None            # 线程池
        
    #----------------------------------------------------------------------
    def init(self, accessKey, secretKey, mode=None):
        """初始化"""
        self.hostname = "api.binance.com"
        self.hosturl = "https://api.binance.com"
            
        self.accessKey = accessKey
        self.secretKey = secretKey

        self.session = requests.session()
        self.session.headers.update({'Accept': 'application/json',
                                'User-Agent': 'binance/python',
                                'X-MBX-APIKEY': self.accessKey})

        if mode:
            self.mode = mode
            
        self.proxies = {}
        
        return True
        
    #----------------------------------------------------------------------
    def start(self, n=3):
        """启动"""
        self.active = True
        
        if self.mode == self.ASYNC_MODE:
            self.pool = Pool(n)
            self.pool.map_async(self.run, range(n))
        
    #----------------------------------------------------------------------
    def stop(self):
        """停止"""
        self.active = False
        self.pool.close()
        self.pool.join()
        
    #----------------------------------------------------------------------
    def close(self):
        """停止"""
        self.active = False
        self.pool.close()
        self.pool.join()
 
    #----------------------------------------------------------------------
    def generate_signature(self, data):

        ordered_data = order_params(data)
        query_string = '&'.join(["{}={}".format(d[0], d[1]) for d in ordered_data])
        m = hmac.new(self.secretKey.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        return m.hexdigest()
    #----------------------------------------------------------------------
    def httpRequest(self, method, url, signed, params, **kwargs):
        """HTTP POST"""       
        # set default requests timeout
        # print 'httpRequest-url:%s, signed:%s, params:%s' % (url, signed, params)

        kwargs['timeout'] = TIMEOUT

        # add our global requests params
        # if self._requests_params:
        #     kwargs.update(self._requests_params)

        if params:
            data = params
        else:
            data = None
        if data and isinstance(data, dict):
            kwargs['data'] = data
        else:
            kwargs['data'] = {}
        if signed:
            # generate signature
            kwargs['data']['timestamp'] = int(time.time() * 1000)
            kwargs['data']['signature'] = self.generate_signature(kwargs['data'])
        data = kwargs['data']
        # sort get and post params to match signature order
        if data:
            # find any requests params passed and apply them
            # if 'requests_params' in kwargs['data']:
            #     # merge requests params into kwargs
            #     kwargs.update(kwargs['data']['requests_params'])
            #     del(kwargs['data']['requests_params'])

            # sort post params
            kwargs['data'] = order_params(kwargs['data'])
        # if get request assign data array to params value for requests lib
        if data and method == 'get':
            kwargs['params'] = kwargs['data']
            del(kwargs['data'])
        try:
            # print 'getattr method:%s, kwargs:%s' % (method, kwargs)
            response = getattr(self.session, method)(url, **kwargs)
            # print response, response.status_code
            if response.status_code == 200:
                return True, response.json()
            else:
                # if 'Order does not exist' in response.json()['msg']:
                #     d1 = response.json().copy()
                #     d1.update(params)
                #     print 'http d1:%s' % d1
                #     return True, d1
                # else:
                return False, u'POST request failed，response：%s, url:%s, params:%s, method:%s' % (response.json(), url, params, method)
        except Exception as e:
            return False, u'POST request unusually，reason：%s' %e
    #----------------------------------------------------------------------
    def apiGet(self, path, signed, params):
        """API GET"""
        url = self.hosturl + path
        method = 'get'
        return self.httpRequest(method, url, signed, params)
    
    #----------------------------------------------------------------------
    def apiPost(self, path, signed, params):
        """API POST"""
        url = self.hosturl + path
        method = 'post'
        return self.httpRequest(method, url, signed, params)
    
    #----------------------------------------------------------------------
    def apiDel(self, path, signed, params):
        """API POST"""
        url = self.hosturl + path
        method = 'delete'
        return self.httpRequest(method, url, signed, params)
    #----------------------------------------------------------------------
    def addReq(self, path, params, func, callback, signed=False):
        """添加请求"""       
        # 异步模式
        if self.mode == self.ASYNC_MODE:
            self.reqid += 1
            req = (path, signed, params, func, callback, self.reqid)
            self.queue.put(req)
            return self.reqid
        # 同步模式
        else:
            return func(path, signed, params)
    
    #----------------------------------------------------------------------
    def processReq(self, req):
        """处理请求"""
        path, signed, params, func, callback, reqid = req
        result, data = func(path, signed, params)
        

        if result:
            if 'lastUpdateId' in data:
                data['symbol'] = params['symbol']
                data['datetime'] = datetime.now()
            # print 'rest api callback data is here'
            callback(data, reqid)
            # else:
            #     msg = u'error code：%s，error info：%s' %(data['err-code'], data['err-msg'])
            #     self.onError(msg, reqid)
        else:
            if 'Order does not exist' in data:
                print 'Order does not exist:%s' % data
            else:
                self.onError(data, reqid)
    
    #----------------------------------------------------------------------
    def run(self, n):
        """连续运行"""
        while self.active:    
            try:
                req = self.queue.get(timeout=1)
                self.processReq(req)
            except Empty:
                pass
    
    #----------------------------------------------------------------------
    def getListenKey(self):
        """查询合约代码"""
        path = '/api/v1/userDataStream'

        params = {}
        func = self.apiPost
        callback = self.onGetListenKey
        
        return self.addReq(path, params, func, callback, False)
    #----------------------------------------------------------------------
    def getSymbols(self):
        """查询合约代码"""
        path = '/api/v1/exchangeInfo'

        params = {}
        func = self.apiGet
        callback = self.onGetSymbols
        
        return self.addReq(path, params, func, callback, False)
    
    #----------------------------------------------------------------------
    # def getCurrencys(self):
    #     """查询支持货币"""
    #     path = '/v1/hadax/common/currencys'

    #     params = {}
    #     func = self.apiGet
    #     callback = self.onGetCurrencys
        
    #     return self.addReq(path, params, func, callback)   
    
    #----------------------------------------------------------------------
    def getTimestamp(self):
        """查询系统时间"""
        path = '/api/v1/time'
        params = {}
        func = self.apiGet
        callback = self.onGetTimestamp
        
        return self.addReq(path, params, func, callback, False)
    
    #----------------------------------------------------------------------
    def getMarketDepth(self, symbol, limit=None):
        """查询系统时间"""
        path = '/api/v1/depth'
        params = {
            'symbol': symbol
        }

        if limit:
            params['limit'] = limit

        func = self.apiGet
        callback = self.onGetMarketDepth
        
        return self.addReq(path, params, func, callback, False)
    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#account-information-user_data
        """
        path = '/api/v3/account'
        params = {}
        func = self.apiGet
        callback = self.onGetAccount
    
        return self.addReq(path, params, func, callback, True)        
    
    #----------------------------------------------------------------------
    def getAccountBalance(self):
        """查询余额"""
        # print '--------------------restful api getAccountBalance'
        path = '/api/v3/account'
        params = {}
        func = self.apiGet
        callback = self.onGetAccountBalance
    
        return self.addReq(path, params, func, callback, True)  
    
    #----------------------------------------------------------------------
    def getOrders(self, symbol, orderId=None, limit=None):
        """查询所有委托active, canceled, or filled.
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#all-orders-user_data
        """
        path = '/api/v3/allOrders'
        
        params = {
            'symbol': symbol
        }
        
        if orderId:
            params['orderId'] = orderId
        if limit:
            params['limit'] = limit     
    
        func = self.apiGet
        callback = self.onGetOrders
    
        return self.addReq(path, params, func, callback, True)   
    
    #----------------------------------------------------------------------
    def getMyTrades(self, symbol, limit=None, fromId=None):
        """查询成交
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#account-trade-list-user_data
        """
        path = '/api/v3/myTrades'

        params = {
            'symbol': symbol
        }

        if limit:
            params['limit'] = limit
        if fromId:
            params['fromId'] = fromId      

        func = self.apiGet
        callback = self.onGetMyTrades

        return self.addReq(path, params, func, callback, True)  
    
    #----------------------------------------------------------------------
    def getOrder(self, symbol, orderId=None, origClientOrderId=None):
        """查询某一委托
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#query-order-user_data
        """
        path = '/api/v3/order'
    
        params = {
            'symbol': symbol
        }

        if orderId:
            params['orderId'] = orderId
        else:
            params['origClientOrderId'] = origClientOrderId
        print 'api getOrder params:%s' % params
        func = self.apiGet
        callback = self.onGetOrder
    
        return self.addReq(path, params, func, callback, True)           
    
    #----------------------------------------------------------------------
    def getCurrentOpenOrders(self, symbol=None):
        """查询所有挂单
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#current-open-orders-user_data
        """
        path = '/api/v3/openOrders'
    
        params = {}

        if symbol:
            params['symbol'] = symbol
    
        func = self.apiGet
        callback = self.onGetCurrentOpenOrders
    
        return self.addReq(path, params, func, callback, True)  

    #----------------------------------------------------------------------
    # def getMatchResult(self, orderid):
    #     """查询某一委托"""
    #     path = '/v1/order/orders/%s/matchresults' %orderid
    
    #     params = {}
    
    #     func = self.apiGet
    #     callback = self.onGetMatchResult
    
    #     return self.addReq(path, params, func, callback, False)     
    
    #----------------------------------------------------------------------
    def placeTestOrder(self, symbol, side, quantity, price=None, type_=ORDER_TYPE_LIMIT, timeInForce=TIME_IN_FORCE_GTC):
        """下测试单   
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#test-new-order-trade
        """
        path = '/api/v3/order/test'
        
        params = {
            'quantity': quantity,
            'side': side,
            'symbol': symbol,
            'type': type_
        }
        
        if price:
            params['price'] = price
        if type_ == ORDER_TYPE_LIMIT:
            params['timeInForce'] = TIME_IN_FORCE_GTC     

        func = self.apiPost
        callback = self.onPlaceOrder
        # print 'binanceApi has placeOrdered'       
        return self.addReq(path, params, func, callback, True)   
    #----------------------------------------------------------------------
    def placeOrder(self, symbol, side, quantity, price=None, type_=ORDER_TYPE_LIMIT, timeInForce=TIME_IN_FORCE_GTC, stopPrice=None, icebergQty=None, newClientOrderId= None):
        """下单
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#new-order--trade
        timeInForce: required if limit order
        """
        path = '/api/v3/order'
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': type_,
            'quantity': quantity
        }
        
        if price:
            params['price'] = price
        if timeInForce:
            params['timeInForce'] = timeInForce     
        if stopPrice:
            params['stopPrice'] = stopPrice   
        if newClientOrderId:
            params['newClientOrderId'] = newClientOrderId 
        if icebergQty:
            params['icebergQty'] = icebergQty   

        func = self.apiPost
        callback = self.onPlaceOrder
        # print 'binanceApi has placeOrdered'       
        return self.addReq(path, params, func, callback, True)    
    
    #----------------------------------------------------------------------
    #----------------------------------------------------------------------
    def cancelOrder(self, symbol, orderId=None, origClientOrderId=None, newClientOrderId=None):
        """撤单
        https://github.com/binance-exchange/binance-official-api-docs/blob/master/rest-api.md#cancel-order-trade
        """
        path = '/api/v3/order'
        
        params = {
            'symbol': symbol
                }
        if orderId:
            params['orderId'] = orderId
        else:
            params['newClientOrderId'] = newClientOrderId
        
        func = self.apiDel
        callback = self.onCancelOrder

        print 'binanceApi cancelOrder:%s' % orderId
        return self.addReq(path, params, func, callback, True)         
    
    #----------------------------------------------------------------------
    # def batchCancel(self, orderids):
    #     """批量撤单"""
    #     path = '/v1/order/orders/batchcancel'
    
    #     params = {
    #         'order-ids': orderids
    #     }
    
    #     func = self.apiPost
    #     callback = self.onBatchCancel
    
    #     return self.addReq(path, params, func, callback, False)     
        
    #----------------------------------------------------------------------
    def onGetListenKey(self, msg, reqid):
        """错误回调"""
        self.listenKey = msg['listenKey']
        print msg, reqid
    #----------------------------------------------------------------------
    def onError(self, msg, reqid):
        """错误回调"""
        print 'Order does not exist' in msg
        print msg, reqid
        
    #----------------------------------------------------------------------
    def onGetSymbols(self, data, reqid):
        """查询代码回调"""
        print reqid, data 
        for d in data:
            print d
        print data['symbols'][0]

    
    #----------------------------------------------------------------------
    def onGetCurrencys(self, data, reqid):
        """查询货币回调"""
        print reqid, data        
    
    #----------------------------------------------------------------------
    def onGetTimestamp(self, data, reqid):
        """查询时间回调"""
        print reqid, data    
        
    #----------------------------------------------------------------------
    def onGetMarketDepth(self, data, reqid):
        """查询时间回调"""
        print reqid, data  
    #----------------------------------------------------------------------
    def onGetAccount(self, data, reqid):
        """查询账户回调"""
        print data
        # print u'commission and balance query successfully, taker:%s, maker:"%s' % (data['takerCommission'], data['takerCommission'])
        # self.onGetAccountBalance(data, reqid) 
    
    #----------------------------------------------------------------------
    def onGetAccountBalance(self, data, reqid):
        """查询余额回调"""
        print data
        
    #----------------------------------------------------------------------
    def onGetOrders(self, data, reqid):
        """查询委托回调"""
        print reqid, data    
        
    #----------------------------------------------------------------------
    def onGetCurrentOpenOrders(self, data, reqid):
        """查询委托回调"""
        print reqid, data
    #----------------------------------------------------------------------
    def onGetMyTrades(self, data, reqid):
        """查询成交回调"""
        print reqid, data      
        
    #----------------------------------------------------------------------
    def onGetOrder(self, data, reqid):
        """查询单一委托回调"""
        print reqid, data    
        
    #----------------------------------------------------------------------
    def onGetMatchResult(self, data, reqid):
        """查询单一成交回调"""
        print reqid, data    
        
    #----------------------------------------------------------------------
    def onPlaceOrder(self, data, reqid):
        """委托回调"""
        print reqid, data
    
    #----------------------------------------------------------------------
    def onCancelOrder(self, data, reqid):
        """撤单回调"""
        print reqid, data          
        
    #----------------------------------------------------------------------
    def onBatchCancel(self, data, reqid):
        """批量撤单回调"""
        print reqid, data      


########################################################################
class DataApi(object):
    """行情接口"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.ws = None
        self.url = ''

        self.reqid = 0
        self.active = False
        self.thread = Thread(target=self.run)
        
        self.subDict = {}

        self.endpoint = "wss://stream.binance.com:9443"
        self.listenKey = None
        self.proxyHost = None
        self.proxyPort = None
        self.proxyPort = True
        self.tradeID = 0
        
    #----------------------------------------------------------------------
    def run(self):
        """执行连接"""
        while self.active:
            try:
                if self.ws:
                    stream = self.ws.recv()
                    # result = zlib.decompress(stream, 47).decode('utf-8')
                    # data = json.loads(result)
                    data = json.loads(stream)
                    self.onData(data)
            # except zlib.error:
            #     self.onError(u'data decompress failed：%s' % stream)
            except _exceptions.WebSocketConnectionClosedException:
                self.onError(u'data server connect breaked off：%s' % stream)
                break
        
    #----------------------------------------------------------------------
    def connect(self, listenKey, proxyHost, proxyPort, isSubUserData):
        """连接"""
        self.listenKey = listenKey
        self.proxyHost = proxyHost
        self.proxyPort = proxyPort
        self.isSubUserData = isSubUserData
        
        if self.listenKey:

            # url = self.endpoint + '/ws/%s' % self.listenKey
            # if proxyHost:
            #     self.ws = create_connection(url, http_proxy_host=proxyHost, http_proxy_port=proxyPort, sslopt={"cert_reqs":ssl.CERT_NONE})
            # else:
            #     self.ws = create_connection(url, sslopt={"cert_reqs":ssl.CERT_NONE})
            #     print 'create_connection with listen'

            if not self.active:
                self.active = True
                self.thread.start()
            
            return True
        else:
            self.onError(u'data server connect failed, no listenKey!')
            return False
        
    #----------------------------------------------------------------------
    def connectUrl(self, url):
        if self.proxyHost:
            # self.ws.connect(url, http_proxy_host=proxyHost, http_proxy_port=proxyPort, sslopt={"cert_reqs":ssl.CERT_NONE})
            self.ws = create_connection(url, http_proxy_host=proxyHost, http_proxy_port=proxyPort, sslopt={"cert_reqs":ssl.CERT_NONE})
        else:
            # print 'connectUrl no proxy,url:%s' % url
            self.ws = create_connection(url, sslopt={"cert_reqs":ssl.CERT_NONE})

    #----------------------------------------------------------------------
    def close(self):
        """停止"""
        if self.active:
            self.active = False
            self.thread.join()
            self.ws.close()
        
    #----------------------------------------------------------------------
    def pong(self, data):
        """响应心跳"""
        req = {'pong': data['ping']}
        self.sendReq(req)
    
    #----------------------------------------------------------------------
    def subscribeSymbolTicker(self, symbol):
        """订阅行情深度"""
        if self.isSubUserData:
            url = self.endpoint + '/stream?streams=%s/%s@ticker' % (self.listenKey, symbol.lower())
        else:
            url = self.endpoint + '/ws/%s@ticker' % symbol.lower()
        print 'subscribeSymbolTicker:%s' % url
        self.connectUrl(url)
    #----------------------------------------------------------------------
    def subscribeMarketDepth(self, symbol):
        """订阅行情深度"""
        topic = 'market.%s.depth.step0' %symbol
        self.subTopic(topic)
        
    #----------------------------------------------------------------------
    def subscribeTradeDetail(self, symbol):
        """订阅成交细节"""
        topic = 'market.%s.trade.detail' %symbol
        self.subTopic(topic)
        
    #----------------------------------------------------------------------
    def subscribeMarketDetail(self, symbol):
        """订阅市场细节"""
        topic = 'market.%s.detail' %symbol
        self.subTopic(topic)
        
    #----------------------------------------------------------------------
    def onError(self, msg):
        """错误推送"""
        print msg
        
    #----------------------------------------------------------------------
    def onData(self, data):
        """数据推送"""
        # print 'websocket onData data:%s' % data
        try:
            if 'ticker' in data['stream']:
                data1 = data['data']
                if 'e' in data1:
                    if 'ping' == data1['e']:
                        self.pong(data1)
                    elif '24hrTicker' == data1['e']:
                        self.onSymbolTicker(data1)
                    elif 'trade' == data1['e']:
                        self.onTrade(data1)
                    # elif 'depthUpdate' == data1['e']:
                    #     self.onMarketDepth(data1)
                    # elif 'err-code' in data1['e']:
                    #     self.onError(u'error code：%s, error info：%s' %(data1['err-code'], data1['err-msg']))
                elif isinstance(data1, list):
                    if isinstance(data1[0], dict):
                        if '24hrTicker' == data1[0]['e']:
                            for i in range(len(data1)):
                                self.onSymbolTicker(data1[i])
            elif self.listenKey == data['stream']:
                if data['data']['e'] == 'executionReport':
                    # 委托单推送
                    if data['data']['x'] == 'TRADE':
                        # 成交
                        self.onMyTrade(data['data'])
                    else:
                        # 挂单或撤单, NEW/CANCELED/REJECTED/TRADE/EXPIRED
                        self.onMyOrder(data['data'])

                elif data['data']['e'] == 'outboundAccountInfo':
                    # 持仓推送
                    print 'outboundAccountInfo!!!!!!!!!!!'
                    self.onAccountBalance(data['data'])
                else:
                    print 'listenKey new stream:%s' % data
            # 深度行情
            elif 'depth' in data['stream']:
                data1 = data['data']
                data1['symbol'] = data['stream'].split('@')[0].upper()
                data1['datetime'] = datetime.now()
                self.onMarketDepth(data1)
            # 市场成交细节
            elif 'trade' in data['stream']:
                data1 = data['data']
                data1['symbol'] = data['stream'].split('@')[0].upper()
                data1['datetime'] = datetime.now()
                self.onMarketDetail(data1)
            elif 'aggTrade' in data['stream']:
                data1 = data['data']
                data1['symbol'] = data['stream'].split('@')[0].upper()
                data1['datetime'] = datetime.now()
                data1['t'] = data1['a']
                self.onMarketDetail(data1)
            # 其他频道
            else:
                print 'ondata new stream:%s' % data
        except Exception as e:
            print 'onData error:%s, data:%s' % (e, data)
            print traceback.format_exc()

    #----------------------------------------------------------------------
    def onMyOrder(self, data):
        """symbol tick推送 """
        print 'onMyOrder'
        print data
    #----------------------------------------------------------------------
    def onSymbolTicker(self, data):
        """symbol tick推送 """
        print 'onSymbolTicker'
        print data
    #----------------------------------------------------------------------
    def onMarketTrade(self, data):
        """onMarketTrade """
        print 'on MarketTrade'
        print data
    #----------------------------------------------------------------------
    def onMarketDepth(self, data):
        """行情深度推送 """
        print 'onMarketDepth'
        print data
    
    #----------------------------------------------------------------------
    def onMyTrade(self, data):
        """成交细节推送"""
        print data
    
    #----------------------------------------------------------------------
    def onAccountBalance(self, data):
        print data
    #----------------------------------------------------------------------
    def onMarketDetail(self, data):
        """市场细节推送"""
        if data['t'] > self.tradeID:
            print data['t']
        else:
            print 'tradeID:%s, dataID:%s' % (self.tradeID, data['t'])

        self.tradeID = data['t']