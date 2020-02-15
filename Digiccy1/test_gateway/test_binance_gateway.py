from time import sleep
from vnpy.gateway.binance import BinanceGateway
from vnpy.trader.utility import load_json
from vnpy.event import Event, EventEngine
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

setting = load_json("connect_binance.json")

def process_event(event:Event):
    print('event type:%s' % event.type)
    print("event data:%s" % event.data)

event_engine = EventEngine()
event_engine.register(EVENT_TICK, process_event)
event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_POSITION, process_event)
event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.start()

gateway = BinanceGateway(event_engine)
gateway.connect(setting)

req = SubscribeRequest("ETHUSDT", Exchange.HUOBI)
gateway.subscribe(req)

while True:
    sleep(5)