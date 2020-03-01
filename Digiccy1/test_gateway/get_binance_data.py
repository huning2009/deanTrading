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
from myConstant import Exchange, EVENT_ACCOUNT_MARGIN,EVENT_BORROW_MONEY,EVENT_REPAY_MONEY



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
starttime = endtime - timedelta(days=4)

symbol_l = ['EOSUSDT', 'BCHUSDT', 'XRPUSDT', 'LTCUSDT', 'BNBUSDT', 'LINKUSDT', 'XTZUSDT']

for symbol in symbol_l:
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