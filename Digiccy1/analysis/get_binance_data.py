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
    EVENT_ACCOUNT_MARGIN,
    EVENT_BORROW_MONEY,
    EVENT_REPAY_MONEY,
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

from DatabaseManage.init_sqlite import get_sqlite, init_models
from myConstant import (
    Exchange, 
    Direction,
    Exchange,
    Product,
    Status,
    OrderType,
    Interval
)
from Digiccy1.binance_gateway_local import BinanceDepthGateway, BinanceFuturesDepthGateway
from Digiccy1.huobi_gateway_local import HuobiGateway, HbdmGateway



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

binance_setting = load_json("connect_binance.json")
gateway = BinanceDepthGateway(event_engine)
gateway.connect(binance_setting)
gateway_futures = BinanceFuturesDepthGateway(event_engine)
gateway_futures.connect(binance_setting)

# huobi_setting = load_json("connect_huobi.json")
# gateway = HuobiGateway(event_engine)
# gateway.connect(huobi_setting)
# gateway_futures = HbdmGateway(event_engine)
# gateway_futures.connect(huobi_setting)

sleep(5)

endtime = datetime.now()
starttime = endtime - timedelta(days=12)

symbol_l1 = ['BTCUSDT', 'EOSUSDT', 'BCHUSDT', 'XRPUSDT', 'LTCUSDT', 'BNBUSDT', 'LINKUSDT', 'XTZUSDT', 'ETHUSDT', 'ETCUSDT']
# symbol_l1 = ['BNBUSDT', 'LINKUSDT', 'XTZUSDT', 'ETHUSDT', 'ETCUSDT']
symbol_l = ['TRXUSDT', 'ADAUSDT', 'ATOMUSDT', 'XMRUSDT', 'DASHUSDT', 'ZECUSDT', 'NEOUSDT', 'XLMUSDT', 'VETUSDT', 'IOSTUSDT']
symbol_2 = []
l = ['BSV200327', 'BSV200626']
l1 = ['bsvusdt']
Interval = Interval.MINUTE
for symbol in symbol_2:
    historyReq = HistoryRequest(symbol, Exchange.BINANCE, starttime, endtime, Interval)
    data_spot = gateway.query_history(historyReq)
    db_data_spot = [DbBarData.from_bar(bar) for bar in data_spot]
    DbBarData.save_all(db_data_spot)
    
    print('%s_spot saved:%s' % (symbol, datetime.now()))
    
# for symbol in l:
    historyReq_futures = HistoryRequest(symbol, Exchange.BINANCEFUTURES, starttime, endtime, Interval)
    data_futures = gateway_futures.query_history(historyReq_futures)
    db_data_futures = [DbBarData.from_bar(bar) for bar in data_futures]
    DbBarData.save_all(db_data_futures)
    print('%s_futures saved:%s' % (symbol, datetime.now()))

print('*'*50)
# print(len(data))

# while True:
#     sleep(5)