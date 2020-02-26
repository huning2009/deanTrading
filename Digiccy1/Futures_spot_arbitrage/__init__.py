from pathlib import Path

from vnpy.trader.app import BaseApp
from vnpy.trader.object import (
    OrderData,
    TradeData,
    TickData,
    BarData
)

from .engine import (
    SpreadEngine,
    APP_NAME,
    SpreadData,
    LegData,
    SpreadStrategyTemplate,
    SpreadAlgoTemplate
)
from .base import EVENT_SPREAD_LOG

class FSASpreadTradingApp(BaseApp):
    """"""

    app_name = APP_NAME
    app_module = __module__
    app_path = Path(__file__).parent
    display_name = "价差交易"
    engine_class = SpreadEngine
    widget_name = "FSASpreadManager"
    icon_name = "spread.ico"
