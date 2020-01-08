import pandas as pd
import datetime as dtt

from vnpy.trader.database import database_manager
from vnpy.trader.object import OrderData, TradeData, BarData, TickData, Exchange, Interval

df = pd.read_csv("000905.csv")
s = []
for i in range(df.shape[0]):
	datetime = dtt.datetime.strptime(df.iloc[i,0], "%Y/%m/%d")
	volume = df.iloc[i,5]
	open_price = df.iloc[i,4]
	high_price = df.iloc[i,2]
	low_price = df.iloc[i,3]
	close_price = df.iloc[i,1]
	barData = BarData(symbol='000905', datetime=datetime, volume=volume, open_price=open_price, high_price=high_price, low_price=low_price, close_price=close_price, gateway_name='csv', exchange=Exchange.CFFEX, interval=Interval.DAILY)
	print(barData)
	s.append(barData)

database_manager.save_bar_data(s)
