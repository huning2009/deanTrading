import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from time import sleep
from datetime import datetime, timedelta
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
    EVENT_LOG
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
    Interval,
    Exchange, EVENT_ACCOUNT_MARGIN,EVENT_BORROW_MONEY,EVENT_REPAY_MONEY
)
# from DatabaseManage.init_sqlite import get_sqlite, init_models
from Digiccy1.okex_gateway_local import OkexGateway, OkexfGateway, OkexsGateway



setting = load_json("connect_okex.json")
# db = get_sqlite('info.db')
# DbContractData, DbAccountData, DbBarData = init_models(db)

def process_event(event:Event):
    print(event.type+ "*"*30)
    if isinstance(event.data, dict):
        print(event.data)
    else:
        print(event.data.__dict__)

event_engine = EventEngine()
event_engine.register(EVENT_TICK, process_event)
# event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_ACCOUNT_MARGIN, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.register(EVENT_BORROW_MONEY, process_event)
event_engine.register(EVENT_REPAY_MONEY, process_event)
event_engine.start()

gateway1 = OkexGateway(event_engine)
# gateway2 = OkexsGateway(event_engine)
gateway1.connect(setting)
# gateway2.connect(setting)

# gateway_futures = BinanceFuturesGateway(event_engine)
# gateway_futures.connect(setting)
sleep(5)
# gateway.repay_money("LINK", 1)

req = SubscribeRequest("BTC-USDT", Exchange.OKEX)
req1 = SubscribeRequest("LINK-USDT", Exchange.OKEX)
gateway1.subscribe(req)
gateway1.subscribe(req1)
# req3 = SubscribeRequest("BTC-USDT-SWAP", Exchange.OKEX)
# gateway2.subscribe(req3)
# endtime = datetime.now()
# starttime = endtime - timedelta(days=150)

# for symbol in ['ETHUSDT', 'BTCUSDT']:
#     historyReq = HistoryRequest(symbol, Exchange.BINANCE, starttime, endtime, Interval.MINUTE)
#     data_spot = gateway.query_history(historyReq)
#     db_data_spot = [DbBarData.from_bar(bar) for bar in data_spot]
#     DbBarData.save_all(db_data_spot)
# print('db_data_spot saved')
# for symbol in ['ETHUSDT', 'BTCUSDT']:
#     historyReq_futures = HistoryRequest(symbol, Exchange.BINANCEFUTURES, starttime, endtime, Interval.MINUTE)
#     data_futures = gateway_futures.query_history(historyReq_futures)
#     db_data_futures = [DbBarData.from_bar(bar) for bar in data_futures]
#     DbBarData.save_all(db_data_futures)
# print('db_data_futures saved')
# print('*'*50)
# print(len(data))

while True:
    sleep(5)