# encoding: UTF-8
import datetime as dtt
from dataclasses import dataclass
from myConstant import Exchange
########################################################################
# 数据库名称
SETTING_DB_NAME = 'VnTrader_Setting_Db'
TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE1_DB_NAME = 'VnTrader_1Min_Db'
MINUTE3_DB_NAME = 'VnTrader_3Min_Db'
MINUTE5_DB_NAME = 'VnTrader_5Min_Db'
MINUTE15_DB_NAME = 'VnTrader_15Min_Db'
MINUTE30_DB_NAME = 'VnTrader_30Min_Db'
STRATEGY_DB_WEB = 'Strategy_Var_Param_WEBDB'
STRATEGY_DETAILLOG = 'Strategy_DetailLog'
STRATEGY_TRADELOG = 'Strategy_TradeLog'

time1510 = dtt.datetime.strptime("1520", "%H%M").time()
time2050 = dtt.datetime.strptime("2050", "%H%M").time()
time0850 = dtt.datetime.strptime("0850", "%H%M").time()

########################################################################
@dataclass
class BaseData:
    """
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str

########################################################################
@dataclass
class MarginAccountData(BaseData):
    """
    digiccy Account data contains information about balance, frozen and
    available.
    """

    accountid: str
    borrowed: float = 0
    interest: float = 0
    free: float = 0
    locked: float = 0
    netAsset: float = 0

    def __post_init__(self):
        """"""
        self.vt_accountid = f"{self.gateway_name}.{self.accountid}"

@dataclass
class FuturesAccountData(BaseData):
    """
    digiccy Account data contains information about balance, frozen and
    available.
    """

    accountid: str
    initialMargin: float = 0
    maintMargin: float = 0
    marginBalance: float = 0
    maxWithdrawAmount: float = 0
    openOrderInitialMargin: float = 0
    positionInitialMargin: float = 0
    unrealizedProfit: float = 0
    walletBalance: float = 0

    def __post_init__(self):
        """"""
        self.vt_accountid = f"{self.gateway_name}.{self.accountid}"

@dataclass
class FuturesPositionData(BaseData):
    """
    digiccy Account data contains information about balance, frozen and
    available.
    """

    symbol: str
    exchange: Exchange
    entryPrice: float = 0
    leverage: float = 0
    positionAmt: float = 0
    unRealizedProfit: float = 0
    markPrice: float = 0
    liquidationPrice: float = 0

    def __post_init__(self):
        """"""
        self.vt_accountid = f"{self.gateway_name}.{self.symbol}"












