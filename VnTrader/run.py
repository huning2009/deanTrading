# encoding: UTF-8
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
# from vnpy.gateway.ctp import CtpGateway
from vnpy.gateway.ctptest import CtptestGateway
from vnpy.app.cta_strategy import CtaStrategyApp
from vnpy.app.cta_backtester import CtaBacktesterApp

from vnpy.rpc import RpcServer
from vnpy.trader.event import (
    EVENT_TICK, 
    EVENT_ORDER, 
    EVENT_TRADE,
    EVENT_POSITION
)


class MyRpcServer(RpcServer):
    """
    Test RpcServer
    """

    def __init__(self, rep_address, pub_address):
        """
        Constructor
        """
        super(MyRpcServer, self).__init__(rep_address, pub_address)

        self.register(self.add)

    def add(self, a, b):
        """
        Test function
        """
        print('receiving: %s, %s' % (a, b))
        return a + b

def main():
    """Start VN Trader"""
    # rep_address = 'tcp://*:2014'
    # pub_address = 'tcp://*:0602'

    # ts = TestServer(rep_address, pub_address)
    # ts.start()

    qapp = create_qapp()

    event_engine = EventEngine()
    # event_engine.register(EVENT_TRADE, ts.publish)

    main_engine = MainEngine(event_engine)
    
    main_engine.add_gateway(CtptestGateway)
    main_engine.add_app(CtaStrategyApp)
    main_engine.add_app(CtaBacktesterApp)

    main_window = MainWindow(main_engine, event_engine)
    main_window.showMaximized()

    qapp.exec()

if __name__ == "__main__":
    main()