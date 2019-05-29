# encoding: UTF-8

import os,sys
myStrategyPath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'mmkStrategy_binance/strategy')
# print 'myStrategyPath:%s' % myStrategyPath
sys.path.append(myStrategyPath)

import multiprocessing
from time import sleep
from datetime import datetime, time

from vnpy.event import EventEngine2
from vnpy.trader.vtEvent import EVENT_LOG, EVENT_ERROR
from vnpy.trader.vtObject import VtSubscribeReq
from vnpy.trader.vtEngine import MainEngine, LogEngine
from mmkStrategy_binance.mmkBase import EVENT_MMK_LOG, EVENT_MMK_STRATEGY

# import okexGateway
import binanceGateway
import mmkStrategy_binance
 
#----------------------------------------------------------------------
def processError(event):
    error = event.dict_['data']
    try:
        print u'######error gatewayName:%s' % error.gatewayName
        print u'######error errorID:%s' % error.errorID
        print u'######error errorMsg:%s' % error.errorMsg
    except:
        print '###### print error failed!'
#----------------------------------------------------------------------
def runChildProcess():
    """子进程运行函数"""
    print '*'*50
    
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    le.addConsoleHandler()
    le.addFileHandler()
    
    le.info(u'marketMaker childProcess is working')
    
    ee = EventEngine2()
    
    me = MainEngine(ee)
    le.info(u'MainEngine has been established')
    me.addGateway(binanceGateway)
    le.info(u'binanceGateway has been established')
    
    ee.register(EVENT_LOG, le.processLogEvent)
    ee.register(EVENT_MMK_LOG, le.processLogEvent)
    ee.register(EVENT_ERROR, processError)
    le.info(u'register log event monitor')
    
    me.connect('BINANCE')
    le.info(u'connect binanceGateway completed!')

    sleep(5)    # 等待CTP接口初始化

    # for k,v in me.dataEngine.contractDict.items():
    #     print '%s:%s' % (k,v.__dict__)

    me.addApp(mmkStrategy_binance)

    mmk = me.getApp(mmkStrategy_binance.appName)

    mmk.loadSetting()
    # le.info(u'MMK策略载入成功')
    
    mmk.initAll()
    # le.info(u'MMK策略初始化成功')
    
    mmk.startAll()
    # le.info(u'MMK策略启动成功')
    
    while True:
        sleep(10)
        # cmd = raw_input()
        # if cmd == "exit":
        #     me.exit()
        #     print 'me.exit & exit!'
        #     exit()
        # elif cmd == "stopAll":
        #     cta.stopAll()
        #     print 'CTA stopAll completed!'

#----------------------------------------------------------------------
def runParentProcess():
    """父进程运行函数"""
    # 创建日志引擎
    le = LogEngine()
    le.setLogLevel(le.LEVEL_INFO)
    le.addConsoleHandler()
    
    le.info(u'启动CTA策略守护父进程')
    
    DAY_START = time(8, 45)         # 日盘启动和停止时间
    DAY_END = time(15, 30)
    
    NIGHT_START = time(20, 45)      # 夜盘启动和停止时间
    NIGHT_END = time(2, 45)
    
    p = None        # 子进程句柄
    
    while True:
        currentTime = datetime.now().time()
        recording = False
        
        # 判断当前处于的时间段
        if ((currentTime >= DAY_START and currentTime <= DAY_END) or
            (currentTime >= NIGHT_START) or
            (currentTime <= NIGHT_END)):
            recording = True
        
        # 记录时间则需要启动子进程
        if recording and p is None:
            le.info(u'启动子进程')
            p = multiprocessing.Process(target=runChildProcess)
            p.start()
            le.info(u'子进程启动成功')
            
        # 非记录时间则退出子进程
        if not recording and p is not None:
            le.info(u'关闭子进程')
            p.terminate()
            p.join()
            p = None
            le.info(u'子进程关闭成功')
            
        sleep(5)


if __name__ == '__main__':
    runChildProcess()
    # currentWeekday = datetime.now().weekday()
    # if currentWeekday < 5:
    #     runChildProcess()
    
    # 尽管同样实现了无人值守，但强烈建议每天启动时人工检查，为自己的PNL负责
    #runParentProcess()