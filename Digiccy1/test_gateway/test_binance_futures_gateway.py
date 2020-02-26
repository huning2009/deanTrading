from time import sleep
from datetime import datetime, timedelta
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
    SubscribeRequest,
    HistoryRequest
)
from vnpy.trader.constant import (
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval
)
from DatabaseManage.init_sqlite import get_sqlite, init_models
from Digiccy1.binance_gateway_local import BinanceGateway, BinanceFuturesGateway
from myConstant import Exchange


setting = load_json("connect_binance.json")
db = get_sqlite('info.db')
DbContractData, DbAccountData, DbBarData = init_models(db)

def process_event(event:Event):
    print(event.type+ "*"*30)
    if isinstance(event.data, dict):
        print(event.data)
    else:
        print(event.data.__dict__)

event_engine = EventEngine()
event_engine.register(EVENT_TICK, process_event)
event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_ORDER, process_event)
event_engine.register(EVENT_TRADE, process_event)
event_engine.register(EVENT_POSITION, process_event)
event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.start()

# gateway = BinanceGateway(event_engine)
# gateway.connect(setting)

gateway_futures = BinanceFuturesGateway(event_engine)
gateway_futures.connect(setting)

sleep(5)
req = SubscribeRequest("ETHUSDT", Exchange.BINANCEFUTURES)
gateway_futures.subscribe(req)

while True:
    sleep(5)