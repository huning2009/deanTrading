# encoding: UTF-8

#from websocket import create_connection
#import gzip
#import zlib
import time
from binanceApi import *
from vnpy.trader.vtFunction import getJsonPath, getTempPath


#if __name__ == '__main__':
    #while(1):
        #try:
            #ws = create_connection("wss://api.binancepro.com/ws", "127.0.0.1", "1080")
            #break
        #except:
            #print('connect ws error,retry...')
            #time.sleep(5)

    ## 订阅 KLine 数据
    ##tradeStr="""{"sub": "market.ethusdt.kline.1min","id": "id10"}"""

    ## 请求 KLine 数据
    ## tradeStr="""{"req": "market.ethusdt.kline.1min","id": "id10", "from": 1513391453, "to": 1513392453}"""

    ##订阅 Market Depth 数据
    #tradeStr="""{"sub": "market.ethusdt.depth.step5", "id": "id10"}"""

    ##请求 Market Depth 数据
    ## tradeStr="""{"req": "market.ethusdt.depth.step5", "id": "id10"}"""

    ##订阅 Trade Detail 数据
    ## tradeStr="""{"sub": "market.ethusdt.trade.detail", "id": "id10"}"""

    ##请求 Trade Detail 数据
    ## tradeStr="""{"req": "market.ethusdt.trade.detail", "id": "id10"}"""

    ##请求 Market Detail 数据
    ## tradeStr="""{"req": "market.ethusdt.detail", "id": "id12"}"""

    #ws.send(tradeStr)
    #while(1):
        #compressData=ws.recv()
        ##print compressData
        #result=zlib.decompress(compressData, 15+32).decode('utf-8')
        #if result[:7] == '{"ping"':
            #ts=result[8:21]
            #pong='{"pong":'+ts+'}'
            #ws.send(pong)
            #ws.send(tradeStr)
        #else:
            #print(result)
def testTrade():
    """测试交易"""
    filePath = getJsonPath('BINANCE_connect.json', __file__)
    f = file(filePath)
    setting = json.load(f)


    accessKey = str(setting['accessKey'])
    secretKey = str(setting['secretKey'])
    
    # 创建API对象并初始化
    api = TradeApi()
    
    api.init(accessKey, secretKey)
    api.start()
    
    # 查询
    keyd = api.getListenKey()
    time.sleep(2)


    api2 = DataApi()
    api2.connect(api.listenKey, '', 0, False)
    # url = "wss://stream.binance.com:9443/stream?streams=%s/bnbbtc@trade" % api.listenKey
    url = "wss://stream.binance.com:9443/stream?streams=%s/ethbtc@aggTrade" % api.listenKey
    # api2.connectUrl("wss://stream.binance.com:9443/ws/%s" % api.listenKey)
    # api2.connectUrl("wss://stream.binance.com:9443/ws/bnbbtc@depth")   #return str
    # api2.connectUrl("wss://stream.binance.com:9443/ws/bnbbtc@depth5")   #return str
    # api2.connectUrl("wss://stream.binance.com:9443/stream?streams=ethusdt@depth5/ethusdt@ticker")   #u'stream': u'ethusdt@depth5'
    # api2.connectUrl("wss://stream.binance.com:9443/stream?streams=%s/bnbbtc@ticker" % api.listenKey)    #return str
    # api2.connectUrl("wss://stream.binance.com:9443/ws/bnbbtc@ticker")    #return str
    api2.connectUrl(url)    #return str
    # api2.connectUrl("wss://stream.binance.com:9443/ws/!ticker@arr")   #return str
    #api.subscribeMarketDepth('ethusdt')
    #api.subscribeTradeDetail('ethusdt')
    # api.subscribeMarketDetail('ethusdt')
    input()

if __name__ == '__main__':
    testTrade()