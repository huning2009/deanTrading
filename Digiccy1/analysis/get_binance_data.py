import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from time import sleep
from datetime import datetime, timedelta
from myUtility import load_json
from myEvent import Event, EventEngine,EVENT_TICK,EVENT_ORDER,EVENT_TRADE,EVENT_POSITION,EVENT_ACCOUNT,EVENT_CONTRACT,EVENT_LOG

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

from DatabaseManage.init_sqlite import get_sqlite, init_models
from Digiccy1.binance_gateway_local import BinanceGateway, BinanceFuturesGateway
from myConstant import Exchange, EVENT_ACCOUNT_MARGIN,EVENT_BORROW_MONEY,EVENT_REPAY_MONEY,Direction,Exchange,Product,Status,OrderType,Interval



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
event_engine.register(EVENT_LOG, process_event)
event_engine.start()

gateway = BinanceGateway(event_engine)
gateway.connect(setting)

gateway_futures = BinanceFuturesGateway(event_engine)
gateway_futures.connect(setting)
sleep(5)

endtime = datetime.now()
starttime = endtime - timedelta(days=60)

symbol_l1 = ['BTCUSDT', 'EOSUSDT', 'BCHUSDT', 'XRPUSDT', 'LTCUSDT', 'BNBUSDT', 'LINKUSDT', 'XTZUSDT']
symbol_l = ['ETHUSDT', 'ETCUSDT', 'TRXUSDT', 'ADAUSDT', 'ATOMUSDT', 'XMRUSDT', 'DASHUSDT']
l = ['BTCUSDT']
for symbol in l:
    historyReq = HistoryRequest(symbol, Exchange.BINANCE, starttime, endtime, Interval.MINUTE)
    data_spot = gateway.query_history(historyReq)
    db_data_spot = [DbBarData.from_bar(bar) for bar in data_spot]
    DbBarData.save_all(db_data_spot)
    
    print('%s_spot saved:%s' % (symbol, datetime.now()))

    historyReq_futures = HistoryRequest(symbol, Exchange.BINANCEFUTURES, starttime, endtime, Interval.MINUTE)
    data_futures = gateway_futures.query_history(historyReq_futures)
    db_data_futures = [DbBarData.from_bar(bar) for bar in data_futures]
    DbBarData.save_all(db_data_futures)
    print('%s_futures saved:%s' % (symbol, datetime.now()))

print('*'*50)
# print(len(data))

# while True:
#     sleep(5)