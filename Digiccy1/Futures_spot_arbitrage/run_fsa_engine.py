from time import sleep

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
from vnpy.gateway.huobi import HuobiGateway
from vnpy.gateway.binance import BinanceGateway

from engine import FSAEngine

event_engine = EventEngine()
fsa_engine = FSAEngine(event_engine)
fsa_engine.init_engine()

fsa_engine.add_gateway(BinanceGateway)
# fsa_engine.add_gateway(HuobiGateway)
fsa_engine.gateways_connect()

while True:
    sleep(5)
    print('sleep')
    cmd = input()
    if cmd == "exit":
        break