# encoding: utf-8
import time
from binanceApi import TradeApi

#----------------------------------------------------------------------
def testTrade():
    """测试交易"""

    accessKey = 'Cc930lEZ8ito3V8kzfPp3xEMtu2iYvd3WZOLz4QtbYu0bxCsWkE4iotURzJ4I8Zj'
    secretKey = 'tn5JhGSXabQ3F44uIkVxPy5ZSpAcSY8CNPdfuJUm033kQLdrCJ1fn7iH9lVUFdqF'
    
    # 创建API对象并初始化
    api = TradeApi()
    
    api.init(accessKey, secretKey)
    api.start()
    
    # 查询
    api.getListenKey()
    # res = api.getSymbols()
    # api.getTimestamp()
    # api.placeTestOrder('ETHUSDT', 'BUY', 1, 200)
    # res = api.getAccount()
    # res = api.getMyTrades('ETHUSDT')
    # for i in range(50000):
    #     # res = api.getCurrentOpenOrders()
    #     res = api.getOrder('ETHUSDT', origClientOrderId='BINANCE_152528_200067')
    #     time.sleep(5)
    
    
    # accountid = ''
    # symbol = 'aaceth'
    
    api.getSymbols()
    # api.getAccounts()
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