import pathlib, sys
path = pathlib.Path.cwd()
sys.path.append(str(path))

import sqlite3
import pandas as pd
import numpy as np
import datetime as dtt
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.graphics.api import qqplot

from myConstant import Exchange


conn = sqlite3.connect("E:\\Desktop\\deanTrading\\.vntrader\\info.db")
# cursor = conn.cursor()

# cursor.execute("select * from dbbardata")
# val = cursor.fetchone()
symbol = 'BTCUSDT'
spotexchange = Exchange.BINANCE.value
futuresexchange = Exchange.BINANCEFUTURES.value
sql = f"select * from dbbardata where symbol='{symbol}' and exchange='{spotexchange}' and interval='1m' order by datetime DESC"
sql2 = f"select * from dbbardata where symbol='{symbol}' and exchange='{futuresexchange}' and interval='1m' order by datetime DESC"

df1 = pd.read_sql(sql, conn)
df1.set_index('datetime', inplace=True)
df11 = df1.loc[df1.index.drop_duplicates(keep=False), 'close_price']

df2 = pd.read_sql(sql2, conn)
df2.set_index('datetime', inplace=True)
df22 = df2.loc[df2.index.drop_duplicates(keep=False), 'close_price']


data = pd.concat((df11, df22), axis=1, join='inner')
data.sort_index(inplace=True)
data.columns = ['spot', 'futures']
data['spread'] = data.iloc[:,0] - data.iloc[:,1]
data.iloc[:,0] = data.iloc[:,0].diff() / data.iloc[:,0]
data.iloc[:,1] = data.iloc[:,1].diff() / data.iloc[:,1]

# print(data[-20:].std())

# data.iloc[:, [0,1]].plot()
fig = sm.graphics.tsa.plot_acf(data.iloc[:,0], lags=40)
fig1 = sm.graphics.tsa.plot_pacf(data.iloc[:,0], lags=40)

plt.show()