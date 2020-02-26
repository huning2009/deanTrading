from time import sleep

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
	EVENT_ACCOUNT,
	EVENT_CONTRACT,
	EVENT_LOG,
)
from vnpy.trader.utility import load_json

from Digiccy1.binance_gateway_local import BinanceGateway, BinanceFuturesGateway
from Digiccy1.futures_spot_arbitrage import FSASpreadTradingApp, EVENT_SPREAD_LOG


def process_event(event:Event):
    print("* "*30 + event.type)
    if isinstance(event.data, dict):
        print(event.data)
    else:
        print(event.data.__dict__)

binance_setting = load_json("connect_binance.json")

event_engine = EventEngine()
event_engine.register(EVENT_LOG, process_event)
event_engine.register(EVENT_SPREAD_LOG, process_event)
event_engine.register(EVENT_ORDER, process_event)
main_engine = MainEngine(event_engine)

main_engine.add_gateway(BinanceGateway)
main_engine.add_gateway(BinanceFuturesGateway)
print('add gateway finished')



fsa_engine = main_engine.add_app(FSASpreadTradingApp)
fsa_engine.start()
print('add fsa_engine and start it')

main_engine.connect(binance_setting, 'BINANCE')
main_engine.connect(binance_setting, 'BINANCEFUTURES')
print('gateways is connecting')
sleep(20)
fsa_engine.strategy_engine.init_all_strategies()
fsa_engine.strategy_engine.start_all_strategies()
print('everythins is OK!')

while True:
    sleep(10)
    # print('sleep')
    # cmd = input()
    # if cmd == "exit":
    #     break