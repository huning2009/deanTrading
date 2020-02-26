""""""
from datetime import datetime
from typing import List, Optional, Sequence, Type

from peewee import (
    AutoField,
    CharField,
    BooleanField,
    Database,
    DateTimeField,
    FloatField,
    Model,
    MySQLDatabase,
    PostgresqlDatabase,
    SqliteDatabase,
    chunked,
)

from vnpy.trader.constant import Exchange, Interval, Product, OptionType
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import get_file_path

def get_sqlite(dbName):
    path = str(get_file_path(dbName))
    db = SqliteDatabase(path)
    return db

class ModelBase(Model):
    gateway_name: str = CharField()
    def to_dict(self):
        return self.__data__

def init_models(db):
    # ----------------------------------------------------------------
    class DbContractData(ModelBase):
        id = AutoField()
        symbol: str = CharField()
        exchange: str = CharField()
        name: str = CharField()
        size: float = FloatField()
        pricetick: float = FloatField()

        min_volume: float = FloatField(default=1)          # minimum trading volume of the contract
        stop_supported: bool = BooleanField(default=False)    # whether server supports stop order
        net_position: bool = BooleanField(default=False)      # whether gateway uses net position volume
        history_data: bool = BooleanField(default=False)      # whether gateway provides bar history data

        # option_strike: float = FloatField()
        # option_underlying: float = FloatField()     # vt_symbol of underlying contract
        
        class Meta:
            database = db
    # ----------------------------------------------------------------
    class DbAccountData(ModelBase):
        accountid: str = CharField()

        balance: float = FloatField()
        frozen: float = FloatField()

        class Meta:
            database = db
    # ----------------------------------------------------------------
    class DbBarData(ModelBase):
        """
        Candlestick bar data for database storage.

        Index is defined unique with datetime, interval, symbol
        """

        id = AutoField()
        symbol: str = CharField()
        exchange: str = CharField()
        datetime: datetime = DateTimeField()
        interval: str = CharField()

        volume: float = FloatField()
        open_interest: float = FloatField()
        open_price: float = FloatField()
        high_price: float = FloatField()
        low_price: float = FloatField()
        close_price: float = FloatField()

        class Meta:
            database = db
            indexes = ((("symbol", "exchange", "interval",  "close_price", "datetime"), True),)

        @staticmethod
        def from_bar(bar: BarData):
            """
            Generate DbBarData object from BarData.
            """
            db_bar = DbBarData()

            db_bar.symbol = bar.symbol
            db_bar.exchange = bar.exchange.value
            db_bar.datetime = bar.datetime
            db_bar.interval = bar.interval.value
            db_bar.volume = bar.volume
            db_bar.open_interest = bar.open_interest
            db_bar.open_price = bar.open_price
            db_bar.high_price = bar.high_price
            db_bar.low_price = bar.low_price
            db_bar.close_price = bar.close_price

            db_bar.gateway_name = 'DB'

            return db_bar

        def to_bar(self):
            """
            Generate BarData object from DbBarData.
            """
            bar = BarData(
                symbol=self.symbol,
                exchange=Exchange(self.exchange),
                datetime=self.datetime,
                interval=Interval(self.interval),
                volume=self.volume,
                open_price=self.open_price,
                high_price=self.high_price,
                open_interest=self.open_interest,
                low_price=self.low_price,
                close_price=self.close_price,
                gateway_name="DB",
            )
            return bar

        @staticmethod
        def save_all(objs: List["DbBarData"]):
            """
            save a list of objects, update if exists.
            """
            dicts = [i.to_dict() for i in objs]
            with db.atomic():
                for c in chunked(dicts, 60):
                    DbBarData.insert_many(
                        c).on_conflict_replace().execute()

    # ----------------------------------------------------------------
    # ----------------------------------------------------------------
    # ----------------------------------------------------------------

    db.connect()
    db.create_tables([DbContractData])
    db.create_tables([DbAccountData])
    db.create_tables([DbBarData])
    return DbContractData, DbAccountData, DbBarData
