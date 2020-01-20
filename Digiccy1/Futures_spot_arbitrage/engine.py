from typing import Any, Sequence, Type

from vnpy.event import Event, EventEngine
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
	EVENT_ACCOUNT,
	EVENT_CONTRACT,
	EVENT_LOG,
)
from vnpy.trader.constant import (
    Direction,
    OrderType,
    Interval,
    Exchange,
    Offset,
    Status
)
from vnpy.trader.utility import load_json

from base import FSAPortfolio


class FSAEngine(object):
	""""""
	setting_filename = "fsa_setting.json"

	def __init__(self, event_engine: EventEngine):
		self.event_engine = event_engine
		self.gateways = {}
		self.exchanges = []
		self.portfolio = None

		self.register_event()
	def init_engine(self):
		"""
		load futures_spot_arbitrage_portfolio and 		contract subscribe
		"""
		self.event_engine.start()

		self.init_portfolio()

	def init_portfolio(self):
		fsa_setting = load_json(self.setting_filename)
		self.portfolio = FSAPortfolio(self)
		self.portfolio.init_portfolio(fsa_setting)


	def add_gateway(self, gateway_class: Type[BaseGateway]):
		"""
		Add gateway.
		"""
		gateway = gateway_class(self.event_engine)
		self.gateways[gateway.gateway_name] = gateway

		# Add gateway supported exchanges into engine
		for exchange in gateway.exchanges:
			if exchange not in self.exchanges:
				self.exchanges.append(exchange)

		return gateway

	def gateways_connect(self):
		event = Event(EVENT_LOG, "gateways start connect")
		self.event_engine.put(event)

		for gateway_name, gateway in self.gateways.items():
			setting_filename = "connect_"+gateway_name.lower()+".json"
			setting = load_json(setting_filename)
			gateway.connect(setting)

		event = Event(EVENT_LOG, "gateways connected!")
		self.event_engine.put(event)

	def close(self):
		pass

	def register_event(self):
		self.event_engine.register(EVENT_TICK, self.process_tick_event)
		self.event_engine.register(EVENT_ORDER, self.process_order_event)
		self.event_engine.register(EVENT_TRADE, self.process_trade_event)
		self.event_engine.register(EVENT_POSITION, self.process_position_event)
		self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
		self.event_engine.register(EVENT_LOG, self.write_log)
		

	def process_tick_event(self, event: Event):
		print("tick evnet:%s"%event.data)


	def process_order_event(self, event: Event):
		print("order evnet:%s"%event.data)

	def process_trade_event(self, event: Event):
		print("trade evnet:%s"%event.data)

	def process_position_event(self, event: Event):
		print("position evnet:%s"%event.data)

	def process_contract_event(self, event: Event):
		print("contract evnet:%s"%event.data)
		
	def send_order(self):
		pass

	def cancel_order(self):
		pass

	def cancel_all(self):
		pass

	def load_bar(self):
		pass

	def load_tick(self):
		pass

	def init_strategy(self):
		pass

	def start_strategy(self):
		pass

	def stop_strategy(self):
		pass

	def write_log(self, event):
		print(event.data)
