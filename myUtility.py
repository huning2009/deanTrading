import json
from logging import CRITICAL
import logging
import sys
from pathlib import Path
from typing import Callable, Dict, Tuple, Union, Any
from decimal import Decimal
from math import floor, ceil

import numpy as np
from myConstant import Exchange

# from vnpy.trader.database.initialize import init

#--------------------------------------------------------------------
def _get_trader_dir(temp_name: str) -> Tuple[Path, Path]:
    """
    Get path where trader is running in.
    """
    cwd = Path.cwd()
    temp_path = cwd.joinpath(temp_name)

    # If .vntrader folder exists in current working directory,
    # then use it as trader running path.
    if temp_path.exists():
        return cwd, temp_path

    # Otherwise use home path of system.
    home_path = Path.home()
    temp_path = home_path.joinpath(temp_name)

    # Create .vntrader folder under home path if not exist.
    if not temp_path.exists():
        temp_path.mkdir()

    return home_path, temp_path


TRADER_DIR, TEMP_DIR = _get_trader_dir(".vntrader")
sys.path.append(str(TRADER_DIR))

#--------------------------------------------------------------------
def get_settings(prefix: str = "") -> Dict[str, Any]:
    prefix_length = len(prefix)
    return {k[prefix_length:]: v for k, v in SETTINGS.items() if k.startswith(prefix)}
#--------------------------------------------------------------------
# def get_database_manager():
# 	# print(SETTINGS)
# 	settings = get_settings("database.")
# 	# print(settings)
# 	database_manager: "BaseDatabaseManager" = init(settings=settings)
# 	# print(database_manager.class_bar.__dict__)
# 	return database_manager
#--------------------------------------------------------------------
def save_json(filename: str, data: dict) -> None:
    """
    Save data into json file in temp path.
    """
    filepath = get_file_path(filename)
    with open(filepath, mode="w+", encoding="UTF-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )
#--------------------------------------------------------------------
def get_file_path(filename: str) -> Path:
    """
    Get path for temp file with filename.
    """
    return TEMP_DIR.joinpath(filename)
#--------------------------------------------------------------------
def load_json(filename: str) -> dict:
    """
    Load data from json file in temp path.
    """
    filepath = get_file_path(filename)

    if filepath.exists():
        with open(filepath, mode="r", encoding="UTF-8") as f:
            data = json.load(f)
        return data
    else:
        save_json(filename, {})
        return {}
#--------------------------------------------------------------------
SETTINGS: Dict[str, Any] = {
    "font.family": "Arial",
    "font.size": 12,

    "log.active": True,
    "log.level": CRITICAL,
    "log.console": True,
    "log.file": True,

    "email.server": "smtp.qq.com",
    "email.port": 465,
    "email.username": "",
    "email.password": "",
    "email.sender": "",
    "email.receiver": "",

    "rqdata.username": "",
    "rqdata.password": "",

    "database.driver": "sqlite",  # see database.Driver
    "database.database": "database.db",  # for sqlite, use this as filepath
    "database.host": "localhost",
    "database.port": 3306,
    "database.user": "root",
    "database.password": "",
    "database.authentication_source": "admin",  # for mongodb
}

# Load global setting from json file.
SETTING_FILENAME: str = "vt_setting.json"
SETTINGS.update(load_json(SETTING_FILENAME))

#--------------------------------------------------------------------
def round_to(value: float, target: float) -> float:
    """
    Round price to price tick value.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    rounded = float(int(round(value / target)) * target)
    return rounded

#--------------------------------------------------------------------
def floor_to(value: float, target: float) -> float:
    """
    Similar to math.floor function, but to target float number.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    result = float(int(floor(value / target)) * target)
    return result

#--------------------------------------------------------------------
def ceil_to(value: float, target: float) -> float:
    """
    Similar to math.ceil function, but to target float number.
    """
    value = Decimal(str(value))
    target = Decimal(str(target))
    result = float(int(ceil(value / target)) * target)
    return result
#--------------------------------------------------------------------
def extract_vt_symbol(vt_symbol: str) -> Tuple[str, Exchange]:
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_str = vt_symbol.split(".")
    return symbol, Exchange(exchange_str)
#--------------------------------------------------------------------
def virtual(func: Callable) -> Callable:
    """
    mark a function as "virtual", which means that this function can be override.
    any base class should use this or @abstractmethod to decorate all functions
    that can be (re)implemented by subclasses.
    """
    return func
#--------------------------------------------------------------------
file_handlers: Dict[str, logging.FileHandler] = {}
log_formatter = logging.Formatter('[%(asctime)s] %(message)s')

def _get_file_logger_handler(filename: str) -> logging.FileHandler:
    handler = file_handlers.get(filename, None)
    if handler is None:
        handler = logging.FileHandler(filename)
        file_handlers[filename] = handler  # Am i need a lock?
    return handler


def get_file_logger(filename: str) -> logging.Logger:
    """
    return a logger that writes records into a file.
    """
    logger = logging.getLogger(filename)
    handler = _get_file_logger_handler(filename)  # get singleton handler.
    handler.setFormatter(log_formatter)
    logger.addHandler(handler)  # each handler will be added only once.
    return logger
#--------------------------------------------------------------------
