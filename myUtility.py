from vnpy.trader.setting import get_settings
from vnpy.trader.database.initialize import init

def get_database_manager():
	# print(SETTINGS)
	settings = get_settings("database.")
	# print(settings)
	database_manager: "BaseDatabaseManager" = init(settings=settings)
	# print(database_manager.class_bar.__dict__)
	return database_manager