import pathlib, sys
path = pathlib.Path.cwd()
sys.path.append(str(path))

import talib as ta
import sqlite3
import pandas as pd
import numpy as np
import datetime as dtt
import matplotlib.pyplot as plt
from statsmodels.api import Poisson
from statsmodels.graphics.api import qqplot
from sklearn.naive_bayes import GaussianNB
# from scipy.stats import poisson

from myConstant import Exchange

def rolling_window(a, window):
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    print(shape)
    strides = a.strides + (a.strides[-1],)
    print(strides)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)

conn = sqlite3.connect("E:\\Desktop\\deanTrading\\.vntrader\\info.db")
# cursor = conn.cursor()

# cursor.execute("select * from dbbardata")
# val = cursor.fetchone()
symbol = 'BTCUSDT'
spotexchange = Exchange.BINANCE.value
futuresexchange = Exchange.BINANCEFUTURES.value
sql = f"select * from dbbardata where symbol='{symbol}' and exchange='{spotexchange}' and interval='1m' order by datetime DESC limit 10000"
sql2 = f"select * from dbbardata where symbol='{symbol}' and exchange='{futuresexchange}' and interval='1m' order by datetime DESC limit 10000"

df1 = pd.read_sql(sql, conn)
df1.set_index('datetime', inplace=True)
df11 = df1.loc[df1.index.drop_duplicates(keep=False), 'close_price']

df2 = pd.read_sql(sql2, conn)
df2.set_index('datetime', inplace=True)
df22 = df2.loc[df2.index.drop_duplicates(keep=False), 'close_price']


data = pd.concat((df11, df22), axis=1, join='inner')
data.sort_index(inplace=True)
data.index = np.linspace(1,len(data.index), num=len(data.index))
data.columns = ['spot', 'futures']
data['spread'] = data.iloc[:,0] - data.iloc[:,1]
data['spread_diff'] = data['spread'].diff().rolling(20).std()
data['spread_diff60'] = data['spread'].diff().rolling(60).std()
data['q80'] = data['spread_diff60'].quantile(0.8)
data['q99'] = data['spread_diff60'].quantile(0.95)
print(data['spread_diff60'].quantile(0.9))

fig, ax = plt.subplots(1,1)
ax.plot(data['spread_diff60'], color='g', label='prob')
ax2 = ax.twinx()
ax2.plot(data['spread'], color='r')

ax.plot(data['q80'], color='b')
ax.plot(data['q99'], color='b')
# ax4 = ax.twinx()
# ax4.plot(data['prob'], color='r')
# ax.hist(data['spread_diff'], bins='auto', density=True, cumulative=True)
# plt.ylim([1,5])
plt.show()

