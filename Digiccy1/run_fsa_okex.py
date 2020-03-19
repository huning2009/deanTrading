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
# from Digiccy1.binance_gateway_local import BinanceGateway, BinanceFuturesGateway
from Digiccy1.okex_gateway_local import OkexGateway, OkexfGateway
from Digiccy1.futures_spot_arbitrage import SpreadEngine


def main():
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    gateway_setting = load_json("connect_okex.json")
    setting_filename = "fsa_setting_test_okex.json"
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

    event_engine = EventEngine()
    log_engine = LogEngine(event_engine, log_level=DEBUG, log_name='fsa1')

    fsa_engine = SpreadEngine(event_engine, setting_filename)

    fsa_engine.add_gateway(OkexGateway)
    fsa_engine.add_gateway(OkexfGateway)
    fsa_engine.write_log('Add gateway finished!')

    fsa_engine.start()

    fsa_engine.connect(gateway_setting, 'OKEX')
    # fsa_engine.connect(gateway_setting, 'OKEX')
    fsa_engine.write_log('Gateways is connecting, and sleep 20 seconds!')
    sleep(15)

    while True:
        # print('sleep')
        sleep(10)
        # print('sleep')
        # cmd = input()
        # if cmd == "exit":
        #     break

if __name__ == "__main__" :
    # for i in range(10000):
    main()