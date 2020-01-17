from typing import Any, Sequence, Type

from vnpy.event import Event, EventEngine
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION
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


class FSAEngine(object):
	""""""
	setting_filename = "fsa_setting.json"

	def __init__(self, event_engine: EventEngine):
		self.event_engine = event_engine
		self.gateways = {}
		self.exchanges = []
		pass

	def init_engine(self):
		"""
		load futures_spot_arbitrage_portfolio and 		contract subscribe
		"""
		pass

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
		for gateway_name, gateway in self.gateways.items():
			setting_filename = "connect_"+gateway_name.lower()+".json"
			setting = load_json(setting_filename)
			gateway.connect(setting)

	def close(self):
		pass

	def register_event(self):
		self.event_engine.register(EVENT_TICK, self.process_tick_event)
		self.event_engine.register(EVENT_ORDER, self.process_order_event)
		self.event_engine.register(EVENT_TRADE, self.process_trade_event)
		self.event_engine.register(EVENT_POSITION, self.process_position_event)
		

	def process_tick_event(self, event: Event):
		print("tick evnet:%s"%event.data)

	def process_order_event(self, event: Event):
		print("order evnet:%s"%event.data)

	def process_trade_event(self, event: Event):
		print("trade evnet:%s"%event.data)

	def process_position_event(self, event: Event):
		print("position evnet:%s"%event.data)

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

	def write_log(self):
		pass
