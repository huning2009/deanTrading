import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from datetime import datetime, timedelta
from time import sleep
from Digiccy1.huobi_gateway_local import HbdmGateway
from myUtility import load_json
from myEvent import (
    Event, 
    EventEngine,
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
    EVENT_ACCOUNT,
    EVENT_CONTRACT,
    EVENT_LOG,
)    

from myObject import (
    TickData,
    OrderData,
    TradeData,
    AccountData,
    ContractData,
    OrderRequest,
    CancelRequest,
    SubscribeRequest,
    HistoryRequest
)
from myConstant import (
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval
)

setting = load_json("connect_huobi.json")

def process_event(event:Event):
    print('event type:%s' % event.type)
    print("event data:%s" % event.data)

event_engine = EventEngine()
event_engine.register(EVENT_TICK, process_event)
event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_POSITION, process_event)
# event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.start()

gateway = HbdmGateway(event_engine)

gateway.connect(setting)

req = SubscribeRequest("ethusdt", Exchange.HUOBI)

# gateway.subscribe(req)
# endtime = datetime.now()
# starttime = endtime - timedelta(days=1)
# historyReq = HistoryRequest('ethusdt', Exchange.HUOBI, starttime, endtime, Interval.MINUTE)
# df = gateway.query_history(historyReq)
# print(df)

while True:
    sleep(5)