# encoding: utf-8

from huobiApi import TradeApi

#----------------------------------------------------------------------
def testTrade():
    """测试交易"""
    accessKey = ''
    secretKey = ''
    
    # 创建API对象并初始化
    api = TradeApi()
    
    api.init(api.HUOBI, accessKey, secretKey)
    api.start()
    
    # 查询
    api.getSymbols()
    #api.getCurrencys()
    #api.getTimestamp()
    
    
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
    
    input()    


    
    
if __name__ == '__main__':
    testTrade()