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
from .infoObject import init, EVENT_CTA_TRADE, EVENT_CTA_SIGNAL, EVENT_CTA_POSITION, EVENT_CTA_PARAMS

APP_NAME = "TradeInfoRecorder"

class RecorderEngine(BaseEngine):
    """"""
    # setting_filename = "trade_recorder_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine):
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.queue = Queue()
        self.thread = Thread(target=self.run)
        self.active = False

        self.recorder_db_manager = init()

        # self.load_setting()
        self.register_event()
        self.start()

    def run(self):
        """"""
        while self.active:
            try:
                event = self.queue.get(timeout=1)

                if event.type == EVENT_CTA_TRADE:
                    self.recorder_db_manager.save_ctatrade(event.data)
                elif event.type == EVENT_CTA_SIGNAL:
                    self.recorder_db_manager.save_ctasignal(event.data)
                elif event.type == EVENT_CTA_POSITION:
                    self.recorder_db_manager.save_ctaposition(event.data)
                elif event.type == EVENT_CTA_PARAMS:
                    self.recorder_db_manager.save_ctaparams(event.data)
                else:
                    print("recorder_db_manager no type")
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
        self.event_engine.register(EVENT_CTA_TRADE, self.recorder_cta_info)
        self.event_engine.register(EVENT_CTA_SIGNAL, self.recorder_cta_info)
        self.event_engine.register(EVENT_CTA_POSITION, self.recorder_cta_info)
        self.event_engine.register(EVENT_CTA_PARAMS, self.recorder_cta_info)

    def write_log(self, msg: str):
        """"""
        event = Event(
            EVENT_RECORDER_TRADE,
            msg
        )
        self.event_engine.put(event)

    def recorder_cta_info(self, event: Event):
        """"""
        self.queue.put(event)
