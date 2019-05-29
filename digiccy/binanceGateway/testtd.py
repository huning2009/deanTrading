# encoding: utf-8
import time
from binanceApi import *
from vnpy.trader.vtFunction import getJsonPath, getTempPath

#----------------------------------------------------------------------
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
    # api.getListenKey()
    # res = api.getSymbols()
    # api.getTimestamp()
    # api.placeTestOrder('ETHUSDT', 'BUY', 1, 200)
    # res = api.getAccount()
    # res = api.getMyTrades('ETHUSDT')
    for i in range(50000):
        # res = api.getCurrentOpenOrders()
        res = api.getOrder('ETHUSDT', origClientOrderId='BINANCE_152528_200067')
        time.sleep(5)
    
    
    # accountid = ''
    # symbol = 'aaceth'
    
    #api.getAccounts()
    #api.getAccountBalance(accountid)
    #api.getOrders(symbol, 'pre-submitted,submitted,partial-filled,partial-canceled,filled,canceled')
    #api.getOrders(symbol, 'filled')
    #api.getMatchResults(symbol)
    
    # api.getOrder('2440401255')
    # api.getMatchResult('2440401255')
    
    #api.placeOrder(accountid, '2', symbol, 'sell-market', source='api')
    #api.cancelOrder('2440451757')
    #api.batchCancel(['2440538580', '2440537853', '2440536765'])
    # print 'res:%s' % res
    input()    


    
    
if __name__ == '__main__':
    testTrade()