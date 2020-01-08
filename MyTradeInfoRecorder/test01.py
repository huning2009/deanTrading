from datetime import datetime
from vnpy.trader.constant import Direction, Offset

from infoObject import CtaTrade, CtaSignal, CtaPosition, CtaParams, init

strategyName = 'turtlestrategy'
tradeid = '001'
datetime = datetime.now()
symbol = 'c1909'
direction = Direction.LONG
offset = Offset.OPEN
price = 1891
volume = 10

signalcontent = u'突破20日高点'

yd_volume = 1

params = 'params'

ctatrader = CtaTrade(strategyName, tradeid, datetime,
                     symbol, direction, offset, price, volume)
ctasignal = CtaSignal(strategyName, datetime, symbol, signalcontent)
ctaposition = CtaPosition(strategyName, symbol,
                          direction, volume, price, yd_volume)
ctaparams = CtaParams(strategyName, symbol, params)

recorder_db_manager = init()

recorder_db_manager.save_ctatrade(ctatrader)
recorder_db_manager.save_ctasignal(ctasignal)
recorder_db_manager.save_ctaposition(ctaposition)
recorder_db_manager.save_ctaparams(ctaparams)
