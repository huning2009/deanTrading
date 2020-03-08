from time import sleep
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from myUtility import load_json
from myEvent import (
    Event, 
    EventEngine,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
	EVENT_ACCOUNT,
	EVENT_CONTRACT,
	EVENT_LOG,
)
from Digiccy1.binance_gateway_local import BinanceGateway, BinanceFuturesGateway
from Digiccy1.futures_spot_arbitrage import SpreadEngine


def process_event(event:Event):
    print("* "*30 + event.type)
    if isinstance(event.data, dict):
        print(event.data)
    else:
        print(event.data.__dict__)

def process_log_event(event:Event):
    log = event.data
    print("%s %s" % (log.time.strftime("%Y-%m-%d %H:%M:%S"),log.msg))

binance_setting = load_json("connect_binance.json")

event_engine = EventEngine()
event_engine.register(EVENT_LOG, process_log_event)
# event_engine.register(EVENT_ORDER, process_event)
# event_engine.register(EVENT_TRADE, process_event)

fsa_engine = SpreadEngine(event_engine)

fsa_engine.add_gateway(BinanceGateway)
fsa_engine.add_gateway(BinanceFuturesGateway)
fsa_engine.write_log('Add gateway finished!')

fsa_engine.start()

fsa_engine.connect(binance_setting, 'BINANCE')
fsa_engine.connect(binance_setting, 'BINANCEFUTURES')
fsa_engine.write_log('Gateways is connecting, and sleep 20 seconds!')
sleep(15)

while True:
    # print('sleep')
    sleep(10)
    # print('sleep')
    # cmd = input()
    # if cmd == "exit":
    #     break