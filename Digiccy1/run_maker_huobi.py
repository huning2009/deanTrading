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
from Digiccy1.huobi_gateway_local import HuobiGateway, HbdmSwapGateway
from Digiccy1.maker_arb import SpreadEngine

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
account_setting = load_json("connect_huobi.json")
setting_filename = "maker_setting1_huobi.json"
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

event_engine = EventEngine()
log_engine = LogEngine(event_engine, log_level=DEBUG, log_name='fsa_huobi')

fsa_engine = SpreadEngine(event_engine, setting_filename)

fsa_engine.add_gateway(HuobiGateway)
fsa_engine.add_gateway(HbdmSwapGateway)
fsa_engine.write_log('Add gateway finished!')

fsa_engine.start()

fsa_engine.connect(account_setting, 'HUOBI')
fsa_engine.connect(account_setting, 'HBDMS')
fsa_engine.write_log('Gateways is connecting, and sleep 20 seconds!', level=CRITICAL)
print('Gateways is connecting, and sleep 20 seconds!')
sleep(30)

fsa_engine.init()

while True:
    # print('sleep')
    sleep(10)
    # print('sleep')
    # cmd = input()
    # if cmd == "exit":
    #     break