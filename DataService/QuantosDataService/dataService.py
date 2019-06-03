# encoding: UTF-8

import sys
import json
from datetime import datetime, timedelta
from time import time, sleep

from pymongo import MongoClient, ASCENDING

from vnpy.trader.vtObject import VtBarData
from vnpy.trader.app.ctaStrategy.ctaBase import MINUTE_DB_NAME
from vnpy.trader.gateway.tkproGateway.DataApi import DataApi


# 交易所类型映射
exchangeMap = {}
exchangeMap['CFFEX'] = 'CFE'
exchangeMap['SHFE'] = 'SHF'
exchangeMap['CZCE'] = 'CZC'
exchangeMap['DCE'] = 'DCE'
exchangeMap['SSE'] = 'SH'
exchangeMap['SZSE'] = 'SZ'
exchangeMapReverse = {v:k for k,v in exchangeMap.items()}

# 加载配置
config = open('config.json')
setting = json.load(config)
config.close()



MONGO_HOST = setting['MONGO_HOST']
MONGO_PORT = setting['MONGO_PORT']
SYMBOLS = setting['SYMBOLS']
USERNAME = setting['USERNAME']
TOKEN = setting['TOKEN']
DATA_SERVER = setting['DATA_SERVER']

# 创建API对象
mc = MongoClient(MONGO_HOST, MONGO_PORT)        # Mongo连接
db = mc[MINUTE_DB_NAME]                         # 数据库


#----------------------------------------------------------------------
def generateVtBar(row):
    """生成K线"""
    bar = VtBarData()
    
    symbol, exchange = row['symbol'].split('.')
    
    bar.symbol = symbol
    bar.exchange = exchangeMapReverse[exchange]
    bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
    bar.open = row['open']
    bar.high = row['high']
    bar.low = row['low']
    bar.close = row['close']
    bar.volume = row['volume']
    
    bar.date = str(row['date'])
    bar.time = str(row['time']).rjust(6, '0')
   
    #将bar的时间改成提前一分钟
    hour=bar.time[0:2]
    minute=bar.time[2:4]
    sec=bar.time[4:6]
    if minute=="00":
        minute="59"
        h = int(hour)
        if h ==0:
            h = 24
        hour=str(h-1).rjust(2,'0')
    else:
        minute=str(int(minute)-1).rjust(2,'0')
    bar.time=hour+minute+sec
   
    bar.datetime = datetime.strptime(' '.join([bar.date, bar.time]), '%Y%m%d %H%M%S')
    
    return bar

#----------------------------------------------------------------------
def getLocalDBStartDate(collection):
    l = collection.find().sort('datetime')
    count = l.count()
    if count:
        return l[0]['datetime'], l[count-1]['datetime'], count
    else:
        return 0, 0, 0
#----------------------------------------------------------------------
def downMinuteBarBySymbol(api, vtSymbol, startDate, endDate=''):
    """下载某一合约的分钟线数据"""
    start = time()

    code, exchange = vtSymbol.split('.')
    symbol = '.'.join([code, exchangeMap[exchange]]) 

    cl = db[code]
    cl.ensure_index([('datetime', ASCENDING)], unique=True)         # 添加索引
    
    # 查询数据库已有文档的起始日期、结束日期及分钟线数据
    lstart, lend, lcount = getLocalDBStartDate(cl)

    if lcount:
        dt = lend
        print 'Local Data is from %s to %s !' % (lstart, lend)
    else:
        print 'Local No Data!'
        dt = datetime.strptime(startDate, '%Y%m%d')
    
    if endDate:
        end = datetime.strptime(endDate, '%Y%m%d')
    else:
        end = datetime.now()
    delta = timedelta(1)
    
    while dt <= end:
        d = int(dt.strftime('%Y%m%d'))
        df, msg = api.bar(symbol, freq='1M', trade_date=d)
        dt += delta
        
        if df is None:
            continue
        try:
            for ix, row in df.iterrows():
                bar = generateVtBar(row)
                d = bar.__dict__
                if d['low'] == 0 or d['high'] == 0 or d['volume']==0:
                # if d['low'] == 0 or d['high'] == 0 or d['openInterest']==0:
                    print d
                else:
                    flt = {'datetime': bar.datetime}
                    cl.replace_one(flt, d, True)    
        except:
            print df

    lstart, lend, lcount = getLocalDBStartDate(cl)
    e = time()
    cost = e - start

    print u'合约%s数据下载完成%s - %s，耗时%s秒' %(vtSymbol, lstart, lend, cost)

    
#----------------------------------------------------------------------
def downloadAllMinuteBar(api, days=10):
    """下载所有配置中的合约的分钟线数据"""
    print '-' * 50
    print u'开始下载合约分钟线数据'
    print '-' * 50
    
    startDt = datetime.today() - days * timedelta(1)
    startDate = startDt.strftime('%Y%m%d')
    
    # 添加下载任务
    for symbol in SYMBOLS:
        downMinuteBarBySymbol(api, str(symbol), startDate)
    
    print '-' * 50
    print u'合约分钟线数据下载完成'
    print '-' * 50
    
