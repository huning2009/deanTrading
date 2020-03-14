import pathlib, sys
path = pathlib.Path.cwd()
sys.path.append(str(path))

import talib
from playhouse.shortcuts import model_to_dict
import pandas as pd
import numpy as np
import datetime as dtt
import statsmodels.api as sm
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox as lb_test

from DatabaseManage.init_sqlite import get_sqlite, init_models

db = get_sqlite('info.db')
DbContractData, DbAccountData, DbBarData = init_models(db)

symbol='ETHUSDT'
buy = -0.4
short = 0.4
exchange='BINANCE'
futures_exchange='BINANCEFUTURES'
start_time = dtt.datetime.now() - dtt.timedelta(days=60)

print(dtt.datetime.now())
data = DbBarData.select().where((DbBarData.symbol==symbol) & (DbBarData.exchange==exchange) & (DbBarData.datetime>start_time))
print(dtt.datetime.now())
# df = pd.DataFrame([model_to_dict(bar) for bar in data])
df = pd.DataFrame([bar.to_dict() for bar in data])
print(dtt.datetime.now())
btc_binance_df = df[['datetime', 'close_price']]
btc_binance_df.set_index(['datetime'],inplace=True)

print(dtt.datetime.now())
data = DbBarData.select().where((DbBarData.symbol==symbol) & (DbBarData.exchange==futures_exchange) & (DbBarData.datetime>start_time))
print(dtt.datetime.now())
df = pd.DataFrame([bar.to_dict() for bar in data])
# df = pd.DataFrame([model_to_dict(bar) for bar in data])
print(dtt.datetime.now())
btc_binancefutures_df = df[['datetime', 'close_price']]
btc_binancefutures_df.set_index(['datetime'],inplace=True)

df = pd.concat([btc_binance_df, btc_binancefutures_df], axis=1, join='inner')
print(df.columns)
df.columns = ['spot', 'futures']
df['diff'] = df['spot'] - df['futures']
df['buy'] = buy
df['short'] = short
df.dropna(inplace=True)
df.sort_index(inplace=True)
# print(df['diff'])
# print(type(df['diff']))
# df['sma'] = talib.SMA(df['diff'])
# df['u'], df['m'], df['d'] = talib.BBANDS(df['diff'], 20,2,2,0)
# df['u'] = df[(df['u']-df['d'])/df['m']<0.0003]['u']*1.3
# df['d'] = df[(df['u']-df['d'])/df['m']<0.0003]['d']*1.3
# df['u1'] = df['u']
# df['d1'] = df['d']
# df.loc[(df['u']-df['d'])/df['m']<0.0003, 'u1'] = df.loc[(df['u']-df['d'])/df['m']<0.0003, 'u']*1.3
# df.loc[(df['u']-df['d'])/df['m']<0.0003, 'd1'] = df.loc[(df['u']-df['d'])/df['m']<0.0003, 'd']*1.3
df['diff'].plot()
df['buy'].plot()
df['short'].plot()
# df['u'].plot()
# df['u1'].plot()
# df['m'].plot()
# df['d'].plot()
# df['d1'].plot()
# df['sma'].plot()
plt.legend(loc="best")
plt.show()

# res = stats.shapiro(df['diff'])
# print(res)

# plt.plot(lb_test(df['diff'])[1])
# plt.show()