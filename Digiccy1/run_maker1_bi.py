from time import sleep
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

from logging import DEBUG, INFO, CRITICAL
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
    LogEngine
)
from Digiccy1.binance_gateway_local import BinanceDepthGateway, BinanceFuturesDepthGateway
from Digiccy1.maker_arb import SpreadEngine

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
binance_setting = load_json("connect_binance.json")
setting_filename = "maker_setting1_bi.json"
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

event_engine = EventEngine()
log_engine = LogEngine(event_engine, log_level=CRITICAL, log_name='fsa1')

fsa_engine = SpreadEngine(event_engine, setting_filename)

fsa_engine.add_gateway(BinanceDepthGateway)
fsa_engine.add_gateway(BinanceFuturesDepthGateway)
fsa_engine.write_log('Add gateway finished!')

fsa_engine.start()

fsa_engine.connect(binance_setting, 'BINANCE')
fsa_engine.connect(binance_setting, 'BINANCEFUTURES')
fsa_engine.write_log('Gateways is connecting, and sleep 20 seconds!')
print('Gateways is connecting, and sleep 20 seconds!')
sleep(15)

while True:
    # print('sleep')
    sleep(10)
    # print('sleep')
    # cmd = input()
    # if cmd == "exit":
    #     break