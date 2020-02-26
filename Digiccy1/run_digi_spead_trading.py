from time import sleep
from vnpy.gateway.huobi import HuobiGateway
from vnpy.gateway.hbdm import HbdmGateway
from vnpy.trader.utility import load_json
from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine

from vnpy.app.spread_trading import SpreadTradingApp

from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
	EVENT_ACCOUNT,
	EVENT_CONTRACT,
	EVENT_LOG,
)
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    ContractData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest
)
from vnpy.trader.constant import (
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval
)

huobigateway_setting = load_json("connect_huobi.json")
hbdmgateway_setting = load_json("connect_hbdm.json")

def process_event(event:Event):
    print(event.type+ "*"*30)
    if isinstance(event.data, dict):
        print(event.data)
    else:
        print(event.data.__dict__)

event_engine = EventEngine()
main_engine = MainEngine(event_engine)

main_engine.add_gateway(HuobiGateway)
main_engine.add_gateway(HbdmGateway)

spread_engine = main_engine.add_app(SpreadTradingApp)

spread_engine.start()
spread_engine.start()
spread_engine.start()

# event_engine.register(EVENT_TICK, process_event)
# event_engine.register(EVENT_CONTRACT, process_event)
# event_engine.register(EVENT_POSITION, process_event)
# event_engine.register(EVENT_ACCOUNT, process_event)
# event_engine.register(EVENT_LOG, process_event)
# event_engine.start()

# gateway = HuobiGateway(event_engine)

main_engine.connect(huobigateway_setting, "HUOBI")
main_engine.connect(hbdmgateway_setting, "HBDM")

# req = SubscribeRequest("ethusdt", Exchange.HUOBI)
# gateway.subscribe(req)

while True:
    sleep(5)