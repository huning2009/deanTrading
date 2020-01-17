from pathlib import Path
import sys
sys.path.append(str(Path.cwd()))

from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType
from vnpy.gateway.huobi import HuobiGateway
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.utility import load_json

from myUtility import get_database_manager

huobi_setting = load_json('connect_huobi.json')

db_manager = get_database_manager()
event_engine = EventEngine()

huobigateway = HuobiGateway(event_engine)
huobigateway.connect(huobi_setting)
huobigateway.query_account()
huobigateway.query_position()