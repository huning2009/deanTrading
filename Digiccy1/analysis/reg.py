import pathlib, sys
path = pathlib.Path.cwd()
sys.path.append(str(path))

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

symbol='LINKUSDT'
exchange='BINANCE'
futures_exchange='BINANCEFUTURES'

print(dtt.datetime.now())
data = DbBarData.select().where((DbBarData.symbol==symbol) & (DbBarData.exchange==exchange))
print(dtt.datetime.now())
# df = pd.DataFrame([model_to_dict(bar) for bar in data])
df = pd.DataFrame([bar.to_dict() for bar in data])
print(dtt.datetime.now())
btc_binance_df = df[['datetime', 'close_price']]
btc_binance_df.set_index(['datetime'],inplace=True)

print(dtt.datetime.now())
data = DbBarData.select().where((DbBarData.symbol==symbol) & (DbBarData.exchange==futures_exchange))
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
df.dropna(inplace=True)
df.sort_index(inplace=True)
df['diff'].plot()
plt.show()

# res = stats.shapiro(df['diff'])
# print(res)

# plt.plot(lb_test(df['diff'])[1])
# plt.show()