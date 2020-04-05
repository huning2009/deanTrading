import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from datetime import datetime, timedelta
from time import sleep
from Digiccy1.huobi_gateway_local import HbdmSwapGateway
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
event_engine.register(EVENT_CONTRACT, process_event)
event_engine.register(EVENT_POSITION, process_event)
# event_engine.register(EVENT_ACCOUNT, process_event)
event_engine.register(EVENT_LOG, process_event)
event_engine.register(EVENT_ORDER, process_event)
event_engine.start()

gateway = HbdmSwapGateway(event_engine)

gateway.connect(setting)
sleep(2)
req = SubscribeRequest("ETH-USD", Exchange.HUOBI)
gateway.subscribe(req)
sleep(5)

order_req = OrderRequest(
            symbol="ETH-USD",
            exchange=Exchange.HUOBI,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            type=OrderType.LIMIT,
            price=120,
            volume=1,
            borrowmoney=False
)
order_id = gateway.send_order(order_req)
print(order_id)



"""
event data:TickData(gateway_name='HBDMS', symbol='BTC-USD', exchange=<Exchange.HUOBI: 'HUOBI'>, datetime=datetime.datetime(2020, 4, 4, 14, 40, 45, 48000), name='BTC-USD', volume=0, open_interest=0, last_price=0, last_volume=0, limit_up=0, limit_down=0, open_price=0, high_price=0, low_price=0, pre_close=0, bid_price_1=0, bid_price_2=0, bid_price_3=0, bid_price_4=0, bid_price_5=0, ask_price_1=0, ask_price_2=0, ask_price_3=0, ask_price_4=0, ask_price_5=0, bid_volume_1=0, bid_volume_2=0, bid_volume_3=0, bid_volume_4=0, bid_volume_5=0, ask_volume_1=0, ask_volume_2=0, ask_volume_3=0, ask_volume_4=0, ask_volume_5=0)

{'ch': 'market.BTC-USD.depth.step0', 'ts': 1585983195499, 'tick': {'mrid': 71763809, 'id': 1585983195, 'bids': [[6726.6, 149], [6726.1, 19], [6725.7, 20], [6725.2, 27], [6725.1, 166], [6725, 5], [6724.5, 275], [6724.3, 275], [6723.8, 1], [6723.4, 5], [6722.7, 14], [6721.6, 142], [6721.5, 2], [6721.4, 4], [6720.6, 8], [6719.9, 9], [6719, 100], [6718.2, 147], [6718.1, 5], [6716.7, 4], [6716.4, 25], [6716, 12], [6714.4, 700], [6714.3, 1], [6713.1, 18], [6712.8, 5], [6712.5, 5], [6710.8, 22], [6710.7, 31], [6710.3, 94], [6707.7, 800], [6706.9, 33], [6706.7, 5], [6705.4, 12], [6705.2, 12], [6704.4, 5], [6700.9, 5], [6700.3, 12], [6700.1, 92], [6700, 300], [6699, 500], [6696, 9], [6695.6, 16], [6695, 272], [6694.9, 107], [6692.5, 500], [6691.7, 1000], [6689.9, 12], [6684.8, 12], [6680.8, 10], [6680, 268], [6679.7, 12], [6679.6, 10], [6678.4, 10], [6678, 2], [6677.2, 10], [6670, 5], [6666.5, 54], [6661.2, 65], [6659.1, 90], [6654.9, 53], [6652.8, 100], [6651.8, 5], [6650.6, 5], [6650, 101], [6649.4, 5], [6648.6, 100], [6647, 5], [6645.8, 5], [6642.3, 50], [6636, 100], [6634.1, 18], [6631.8, 100], [6626, 1], [6625.5, 12], [6625, 100], [6621.3, 100], [6620, 2], [6619.2, 20], [6618, 100], [6615, 31], [6612, 58], [6611, 1], [6610.8, 100], [6608.7, 100], [6606.6, 100], [6602.4, 100], [6600, 27], [6598.2, 100], [6594, 100], [6591.9, 100], [6587.7, 22], [6585.6, 30], [6578, 100], [6577.9, 6], [6573, 200], [6568.1, 2], [6558, 200], [6550, 10], [6540.5, 3000], [6526, 1], [6500, 16], [6480, 1], [6455, 5], [6450, 1], [6444, 100], [6426, 1], [6410, 200], [6401, 3], [6400, 5], [6380, 300], [6333, 100], [6326, 1], [6301, 4], [6300, 10], [6226, 1], [6222, 100], [6220, 400], [6201, 3], [6200.1, 5], [6200, 8], [6150.1, 5], [6138.1, 61], [6132, 73], [6100.1, 5], [6100, 5], [6090, 100], [6039.6, 1], [6000, 20], [5914.4, 38], [5822, 100], [5800, 1], [5623, 8], [5620, 7], [5555, 1], [5522, 100], [5222, 100], [5022, 100], [4899, 200], [4444, 2], [3929, 20], [3700, 11], [2600, 2], [900, 1], [100, 1]], 'asks': [[6726.7, 543], [6726.8, 17], [6726.9, 268], [6727, 65], [6727.9, 10], [6729.1, 5], [6730, 10], [6730.1, 50], [6730.5, 15], [6730.7, 6], [6731.2, 1], [6732, 160], [6733.8, 147], [6734.2, 100], [6735, 2], [6736.6, 1], [6737.6, 7], [6737.7, 700], [6738.4, 25], [6741.2, 1], [6742.1, 3], [6743.8, 800], [6743.9, 20], [6746.4, 31], [6746.7, 94], [6751.7, 17], [6753.4, 80], [6753.5, 500], [6754.5, 33], [6756.5, 10], [6757.5, 106], [6758, 28], [6758.8, 500], [6760.8, 16], [6762.3, 12], [6762.4, 10], [6764.9, 10], [6765.5, 5], [6766.1, 10], [6767.3, 10], [6767.4, 12], [6767.6, 1000], [6772.5, 12], [6775, 5], [6775.3, 53], [6780, 5], [6785.1, 84], [6787.2, 15], [6791.4, 71], [6793.5, 100], [6797.7, 79], [6799.9, 10], [6800, 7], [6800.1, 17], [6801.9, 23], [6802, 100], [6804, 22], [6805, 200], [6808.2, 100], [6810, 4], [6810.3, 29], [6814.5, 15], [6816.7, 5], [6817.9, 5], [6818.7, 91], [6819.1, 5], [6825, 69], [6826, 1], [6827.1, 100], [6828, 28], [6830, 2], [6835.5, 29], [6837.6, 86], [6840, 50], [6841.8, 89], [6844, 17], [6848.1, 100], [6850, 211], [6855, 10], [6880, 2], [6888, 28], [6900, 51], [6902.8, 3000], [6915, 10], [6917, 15], [6926, 1], [6938.4, 10], [6943, 40], [6978, 30], [6998, 2], [7000, 7], [7005, 20], [7021.7, 10], [7026, 1], [7033, 6], [7049.9, 3], [7050, 22], [7098.6, 46], [7099, 5], [7100, 20], [7105, 10], [7123, 10], [7126, 1], [7149, 5], [7150, 16], [7188.4, 10], [7199, 5], [7200, 46], [7223, 5], [7226, 1], [7244, 8], [7450, 50], [7499.9, 5], [7500, 50], [7600, 4], [7660, 7], [7920, 50], [15999.9, 5], [16999.9, 5], [17999.9, 5], [19999.9, 5], [29999.9, 5], [39999.9, 5], [49999.9, 5], [59999.9, 5], [69999.9, 5], [79999.9, 5], [89999.9, 5], [99999.9, 5]], 'ts': 1585983195486, 'version': 1585983195, 'ch': 'market.BTC-USD.depth.step0'}}
"""

"""
endtime = datetime.now()
starttime = endtime - timedelta(days=1)
historyReq = HistoryRequest('BTC-USD', Exchange.HUOBI, starttime, endtime, Interval.MINUTE)
df = gateway.query_history(historyReq)
print(df)
"""

while True:
    sleep(5)