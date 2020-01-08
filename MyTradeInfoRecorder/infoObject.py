from datetime import datetime
from peewee import (
	AutoField,
	CharField,
	Database,
	DateTimeField,
	FloatField,
	Model,
	MySQLDatabase,
	PostgresqlDatabase,
	SqliteDatabase,
	chunked,
)
from vnpy.trader.setting import get_settings
from vnpy.trader.utility import get_file_path

EVENT_CTA_TRADE = "eCtaTrade."
EVENT_CTA_SIGNAL = "eCtaSignal."
EVENT_CTA_POSITION = "eCtaPosition."
EVENT_CTA_PARAMS = "eCtaParams."


def init():
	settings = get_settings("database.")
	database = settings["database"]
	path = str(get_file_path(database))
	db = SqliteDatabase(path)
	DbCtaTrade, DbCtaSignal, DbCtaPosition, DbCtaParams = init_models(db)

	return RecorderDbManager(DbCtaTrade, DbCtaSignal, DbCtaPosition, DbCtaParams)
# -----------------------------------------------------------------------------


def init_models(db):
	class DbCtaTrade(Model):
		"""docstring for CtaTrade"""
		id = AutoField()

		strategyName: str = CharField()
		tradeid: str = CharField()
		datetime: datetime = DateTimeField()
		symbol: str = CharField()
		direction: str = CharField()
		offset: str = CharField()
		price: float = FloatField()
		volume: float = FloatField()

		class Meta:
			database = db
			indexes = ((("strategyName", "symbol", "datetime"), True),)

		@staticmethod
		def from_ctatrade(ctatrade: CtaTrade):
			db_ctatrade = DbCtaTrade()

			db_ctatrade.strategyName = ctatrade.strategyName
			db_ctatrade.tradeid = ctatrade.tradeid
			db_ctatrade.datetime = ctatrade.datetime
			db_ctatrade.symbol = ctatrade.symbol
			db_ctatrade.direction = ctatrade.direction
			db_ctatrade.offset = ctatrade.offset
			db_ctatrade.price = ctatrade.price
			db_ctatrade.volume = ctatrade.volume

			return db_ctatrade

		@staticmethod
		def save_data(data):
			with db.atomic():
				DbCtaTrade.insert(data.__data__).on_conflict_replace().execute()
# -----------------------------------------------------------------------------

	class DbCtaSignal(Model):
		"""docstring for CtaSignal"""
		id = AutoField()

		strategyName: str = CharField()
		datetime: datetime = DateTimeField()
		symbol: str = CharField()
		signalcontent: str = CharField()

		class Meta:
			database = db
			indexes = ((("strategyName", "symbol", "datetime"), True),)

		@staticmethod
		def from_ctasignal(ctasignal: CtaSignal):
			db_ctasignal = DbCtaSignal()

			db_ctasignal.strategyName = ctasignal.strategyName
			db_ctasignal.datetime = ctasignal.datetime
			db_ctasignal.symbol = ctasignal.symbol
			db_ctasignal.signalcontent = ctasignal.signalcontent

			return db_ctasignal

		@staticmethod
		def save_data(data):
			with db.atomic():
				DbCtaSignal.insert(data.__data__).on_conflict_replace().execute()
# -----------------------------------------------------------------------------
	class DbCtaPosition(Model):
		"""docstring for CtaPosition"""
		id = AutoField()

		strategyName: str = CharField()
		symbol: str = CharField()
		direction: str = CharField()
		volume: float = FloatField()
		price: float = FloatField()
		yd_volume: float = FloatField()

		class Meta:
			database = db
			indexes = ((("strategyName", "symbol"), True),)

		@staticmethod
		def from_ctaposition(ctaposition: CtaPosition):
			db_ctaposition = DbCtaPosition()

			db_ctaposition.strategyName = ctaposition.strategyName
			db_ctaposition.symbol = ctaposition.symbol
			db_ctaposition.direction = ctaposition.direction
			db_ctaposition.volume = ctaposition.volume
			db_ctaposition.price = ctaposition.price
			db_ctaposition.yd_volume = ctaposition.yd_volume

			return db_ctaposition

		@staticmethod
		def save_data(data):
			with db.atomic():
				DbCtaPosition.insert(data.__data__).on_conflict_replace().execute()
# -----------------------------------------------------------------------------
	class DbCtaParams(Model):
		"""docstring for CtaParams"""
		id = AutoField()
		
		strategyName: str = CharField()
		symbol: str = CharField()
		params: str = CharField()

		class Meta:
			database = db
			indexes = ((("strategyName", "symbol"), True),)

		@staticmethod
		def from_ctaparams(ctaparams: CtaParams):
			db_ctaparams = DbCtaParams()

			db_ctaparams.strategyName = ctaparams.strategyName
			db_ctaparams.symbol = ctaparams.symbol
			db_ctaparams.params = ctaparams.params

			return db_ctaparams

		@staticmethod
		def save_data(data):
			with db.atomic():
				DbCtaParams.insert(data.__data__).on_conflict_replace().execute()

	db.connect()
	db.create_tables([DbCtaTrade, DbCtaSignal, DbCtaPosition, DbCtaParams])
	return DbCtaTrade, DbCtaSignal, DbCtaPosition, DbCtaParams
# -----------------------------------------------------------------------------
class RecorderDbManager(object):
	"""docstring for RecorderDbManager"""
	def __init__(self, DbCtaTrade, DbCtaSignal, DbCtaPosition, DbCtaParams):
		super(RecorderDbManager, self).__init__()
		self.class_dbCtaTrade = DbCtaTrade
		self.class_dbCtaSignal = DbCtaSignal
		self.class_dbCtaPosition = DbCtaPosition
		self.class_dbCtaParams = DbCtaParams

	def save_ctatrade(self, ctatrade):
		dbCtaTrade = self.class_dbCtaTrade.from_ctatrade(ctatrade)
		self.class_dbCtaTrade.save_data(dbCtaTrade)

	def save_ctasignal(self, ctasignal):
		dbCtaSignal = self.class_dbCtaSignal.from_ctasignal(ctasignal)
		self.class_dbCtaSignal.save_data(dbCtaSignal)

	def save_ctaposition(self, ctaposition):
		dbCtaPosition = self.class_dbCtaPosition.from_ctaposition(ctaposition)
		self.class_dbCtaPosition.save_data(dbCtaPosition)

	def save_ctaparams(self, ctaparams):
		dbCtaParams = self.class_dbCtaParams.from_ctaparams(ctaparams)
		self.class_dbCtaParams.save_data(dbCtaParams)

###############################################################################
###############################################################################
# CTA Info class		
class CtaTrade(object):
	"""docstring for CtaTrade"""
	def __init__(self, strategyName, tradeid, datetime, symbol, direction, offset, price, volume):
		super(CtaTrade, self).__init__()
		self.strategyName = strategyName
		self.tradeid = tradeid
		self.datetime = datetime
		self.symbol = symbol
		self.direction = direction
		self.offset = offset
		self.price = price
		self.volume = volume

class CtaSignal(object):
	"""docstring for CtaSignal"""
	def __init__(self, strategyName, datetime, symbol, signalcontent):
		super(CtaSignal, self).__init__()
		self.strategyName = strategyName
		self.datetime = datetime
		self.symbol = symbol
		self.signalcontent = signalcontent

class CtaPosition(object):
	"""docstring for CtaPosition"""
	def __init__(self, strategyName, symbol, direction, volume, price, yd_volume):
		super(CtaPosition, self).__init__()
		self.strategyName = strategyName
		self.symbol = symbol
		self.direction = direction
		self.volume = volume
		self.price = price
		self.yd_volume = yd_volume
		
class CtaParams(object):
	"""docstring for CtaParams"""
	def __init__(self, strategyName, symbol, params):
		super(CtaParams, self).__init__()
		self.strategyName = strategyName
		self.symbol = symbol
		self.params = params
		
		
		
		
