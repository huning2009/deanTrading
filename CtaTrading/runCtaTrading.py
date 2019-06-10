# encoding: UTF-8

import multiprocessing
from time import sleep
from datetime import datetime, time

from vnpy.event import EventEngine
from vnpy.trader.event import EVENT_TIMER, EVENT_LOG
from vnpy.trader.engine import MainEngine, LogEngine
from vnpy.gateway.ctp import CtpGateway
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.cta_strategy.base import EVENT_CTA_LOG

#----------------------------------------------------------------------
def runChildProcess():
    """子进程运行函数"""
    print('-'*20)
    
    # 创建日志引擎
    ee = EventEngine()
    me = MainEngine(ee)

    le = LogEngine(me, ee)
    le.add_console_handler()
    le.add_file_handler()
    

    me.add_gateway(CtpGateway)

    ee.register(EVENT_LOG, le.process_log_event)
    ee.register(EVENT_CTA_LOG, le.process_log_event)
    
    
    sleep(20)    # 等待CTP接口初始化

    me.add_app(CtaStrategyApp)

    cta = me.apps[CtaStrategyApp.app_name]
        
    cta.init_all_strategies()
    
    cta.start_all_strategies()
    
    # me.connect('CTP')

    while True:
        sleep(1)
        cmd = raw_input()
        if cmd == "exit":
            me.exit()
            print('me.exit & exit!')
            exit()
        elif cmd == "stopAll":
            cta.stopAll()
            print('CTA stopAll completed!')

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
    currentWeekday = datetime.now().weekday()
    if currentWeekday < 5:
        runChildProcess()
    
    # 尽管同样实现了无人值守，但强烈建议每天启动时人工检查，为自己的PNL负责
    #runParentProcess()