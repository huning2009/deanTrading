import matplotlib.pyplot as plt
from matplotlib.pylab import date2num
import mpl_finance as mpf
import datetime as dtt
import numpy as np
import talib

import JoinQuantData
from vnpy.trader.constant import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType


def getDataMatrix(symbol, exchange:Exchange, interval:Interval, start=None, end=None):
	database_manager = JoinQuantData.get_database_manager()
	dataSuq = database_manager.load_bar_data(symbol, exchange, interval, start, end)

	data_mat = []
	for barData in dataSuq:
		dtt = date2num(barData.datetime)
		openPrice = barData.open_price
		closePrice = barData.close_price
		highPrice = barData.high_price
		lowPrice = barData.low_price
		vol = barData.volume
		data_mat.append([dtt, openPrice, closePrice, highPrice, lowPrice, vol])
	return np.array(data_mat)

def show():
	data_mat = getDataMatrix("C1909", Exchange("DCE"), Interval("d"), dtt.datetime(2018,6,1), dtt.datetime.now())
	
	x_list = data_mat[:,0]
	y_list = talib.EMA(data_mat[:,2], 20)
	yy_list = talib.EMA(y_list, 20)
	print(len(x_list))
	print(len(y_list))

	fig, ax = plt.subplots()
	mpf.candlestick_ochl(ax,data_mat,colordown='#53c156', colorup='#ff1717',width=0.5,alpha=1)
	ax.plot(x_list, yy_list, 'r--')
	ax.plot(x_list, y_list, '-')
	ax.xaxis_date()
	# mpf.candlestick_ochl(ax,data_mat,colordown='#53c156', colorup='#ff1717',width=0.3,alpha=1)

	plt.show()

show()