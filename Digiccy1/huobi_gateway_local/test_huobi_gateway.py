import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from datetime import datetime, timedelta
from time import sleep
from Digiccy1.huobi_gateway_local import HuobiGateway
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
    EVENT_ACCOUNT_MARGIN
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
    Offset,
    Product,
    Status,
    OrderType,
    Interval
)

setting = load_json("connect_huobi.json")

def process_event(event:Event):
    print('event type:%s' % event.type)
    print("event data:%s" % event.data)

def process_tick_event(event:Event):
    print('event type:%s' % event.type)
    print("event data:%s" % event.data.bids)

event_engine = EventEngine()
# event_engine.register(EVENT_TICK, process_event)
# event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_POSITION, process_event)
# event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.register(EVENT_ORDER, process_event)
event_engine.register(EVENT_TRADE, process_event)
# event_engine.register(EVENT_ACCOUNT_MARGIN, process_event)
event_engine.start()

gateway = HuobiGateway(event_engine)

gateway.connect(setting)
sleep(3)
req = SubscribeRequest("ethusdt", Exchange.HUOBI)
gateway.subscribe(req)

order_req = OrderRequest(
            symbol="ethusdt",
            exchange=Exchange.HUOBI,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            type=OrderType.LIMIT,
            price=120,
            volume=0.1,
            borrowmoney=False
)
order_id = gateway.send_order(order_req)
print(order_id)


# endtime = datetime.now()
# starttime = endtime - timedelta(days=1)
# historyReq = HistoryRequest('ethusdt', Exchange.HUOBI, starttime, endtime, Interval.MINUTE)
# df = gateway.query_history(historyReq)
# print(df)

while True:
    sleep(5)