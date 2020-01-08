""""""

from threading import Thread
from queue import Queue, Empty
from copy import copy

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.constant import Exchange
from vnpy.trader.object import (
    SubscribeRequest,
    TickData,
    BarData,
    ContractData
)
from vnpy.trader.event import EVENT_TICK, EVENT_CONTRACT
from vnpy.trader.utility import load_json, save_json, BarGenerator
from vnpy.app.spread_trading.base import EVENT_SPREAD_DATA, SpreadData
from .infoObject import recorder_db_manager
APP_NAME = "TradeInfoRecorder"

EVENT_RECORDER_CTA_INFO = "eRecorderCtaInfo"


class RecorderEngine(BaseEngine):
    """"""
    # setting_filename = "trade_recorder_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.queue = Queue()
        self.thread = Thread(target=self.run)
        self.active = False

        self.db = get_db()

        # self.load_setting()
        self.register_event()
        self.start()

    def run(self):
        """"""
        while self.active:
            try:
                task = self.queue.get(timeout=1)
                task_type, data = task

                if task_type == "cta_info":
                    recorder_db_manager.insert(data)
                # elif task_type == "bar":
                #     database_manager.save_bar_data([data])

            except Empty:
                continue

    def close(self):
        """"""
        self.active = False

        if self.thread.isAlive():
            self.thread.join()

    def start(self):
        """"""
        self.active = True
        self.thread.start()

    def register_event(self):
        """"""
        self.event_engine.register(
            EVENT_RECORDER_CTA_INFO, self.reorder_cta_info)

    def write_log(self, msg: str):
        """"""
        event = Event(
            EVENT_RECORDER_TRADE,
            msg
        )
        self.event_engine.put(event)

    def reorder_cta_info(self, event: Event):
        """"""
        task = ("cta_info", copy(event.data))
        self.queue.put(task)
