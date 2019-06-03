import datetime as dtt

from vnpy.trader.setting import get_settings, SETTINGS
from vnpy.trader.database.initialize import init
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType

def get_database_manager():
	# print("SRTTING")
	# print(SETTINGS)
	settings = get_settings("database.")
	# print(settings)
	database_manager: "BaseDatabaseManager" = init(settings=settings)
	# print(database_manager.class_bar.__dict__)
	return database_manager

database_manager = get_database_manager()

symbol = "C1909"
exchange = Exchange('DCE')
interval = Interval('1m')
start = dtt.datetime(2018,8,1)
end = dtt.datetime.now()
data = database_manager.load_bar_data(symbol, exchange, interval, start, end)
print(data)