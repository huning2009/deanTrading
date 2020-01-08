from pathlib import Path

from vnpy.trader.app import BaseApp

from .engine import RecorderEngine, APP_NAME


class DataRecorderApp(BaseApp):
    """"""
    app_name = APP_NAME
    app_module = __module__
    app_path = Path(__file__).parent
    display_name = "交易信息记录"
    engine_class = RecorderEngine
    widget_name = "RecorderManager"
    icon_name = "recorder.ico"
