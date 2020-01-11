import os
from jqdatasdk import *
import json
import datetime as dtt
import sqlite3
import re
import pathlib

from vnpy.trader.setting import get_settings, SETTINGS
from vnpy.trader.database.initialize import init
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType


#---------------------------------------------------------------------------------------------------------
def login_joinquant():
	config_path = pathlib.Path(__file__).resolve().parent.parent.joinpath("joinquant_config.json")
	config = open(config_path)
	setting = json.load(config)
	auth(setting["USERNAME"],setting["PASSWORD"])

# # all_securities = get_all_securities(types=[], date=None)
# # print(all_securities)
#---------------------------------------------------------------------------------------------------------
def get_database_manager():
	# print("SRTTING")
	# print(SETTINGS)
	settings = get_settings("database.")
	# print(settings)
	database_manager: "BaseDatabaseManager" = init(settings=settings)
	# print(database_manager.class_bar.__dict__)
	return database_manager
#---------------------------------------------------------------------------------------------------------

def download_contract_ochl(jqsymbol, start_date="", end_date="",frequency='d'):
	if frequency=='d':
		frequency='daily'

	if not start_date:
		start_date = '20%s-%s-01' % (int(re.findall(r"\d+", jqsymbol)[0][:2])-1, int(re.findall(r"\d+", jqsymbol)[0][-2:]))
	if not end_date:
		end_date = dtt.datetime.now().strftime("%Y-%m-%d")
	print(jqsymbol,start_date,end_date)
	price = get_price(jqsymbol, start_date=start_date, end_date=end_date, frequency=frequency, fields=['open', 'close', 'high', 'low', 'volume'], skip_paused=False, fq='pre')
	price.dropna(axis=0, how='all', inplace=True)
	return price, jqsymbol

# #---------------------------------------------------------------------------------------------------------
# def df_to_BarDataList(ohlc_df, symbol):
# 	if symbol.split('.')[1][1:] == "ZCE":
# 		exchange = Exchange("CZCE")
# 	else:
# 		exchange = Exchange(symbol.split('.')[1][1:])
		
# 	barDataList = []
# 	for index, value in ohlc_df.iterrows():
# 		index = index.strftime("%Y-%m-%d %H:%M:%S")
# 		datetime = dtt.datetime.strptime(index, "%Y-%m-%d %H:%M:%S")
# 		barData = BarData(None, symbol.split('.')[0], exchange, datetime)
# 		barData.volume = value["volume"]
# 		barData.open_price = value["open"]
# 		barData.high_price = value["high"]
# 		barData.low_price = value["low"]
# 		barData.close_price = value["close"]
# 		barData.interval = Interval('d')

# 		barDataList.append(barData)

# 	return barDataList
# #---------------------------------------------------------------------------------------------------------

# def insertToMongoDB(df, dbName, collectionName):
# 	client = MongoClient('localhost', 27017)
# 	db = client[dbName]
# 	col = db[collectionName]
# 	for i in range(0, len(df)):
# 		d = dict(date=df.index[i], open=df.iloc[i,0], close=df.iloc[i,1], high=df.iloc[i,2], low=df.iloc[i,3], vol=df.iloc[i,4])
# 		col.insert_one(d)

#---------------------------------------------------------------------------------------------------------
def insert_to_vnpydb(db_manager, price_df, jqsymbol, frequency='d'):
	bar_seq = []
	symbol = jqsymbol.split('.')[0]
	if frequency=='d':
		# datetimestr = "%Y/%m/%d"
		interval=Interval.DAILY
	else:
		# datetimestr = "%Y/%m/%d %H:%M:%S"
		interval=Interval[frequency]

	if "DCE" in jqsymbol:
		exchange = Exchange.DCE
	elif "ZCE" in jqsymbol:
		exchange = Exchange.CZCE
	elif "XSGE" in jqsymbol:
		exchange = Exchange.SHFE
	elif "INE" in jqsymbol:
		exchange = Exchange.INE
	elif "XSHG" in jqsymbol:
		exchange = Exchange.SSE
	elif "XSHE" in jqsymbol:
		exchange = Exchange.SZSE
	else:
		exchange = Exchange.LOCAL

	for i in range(len(price_df)):
		# print(price_df.index[i])
		mydatetime = price_df.index[i].to_pydatetime()
		volume = price_df.iloc[i,4]
		open_price = price_df.iloc[i,0]
		high_price = price_df.iloc[i,2]
		low_price = price_df.iloc[i,3]
		close_price = price_df.iloc[i,1]
		barData = BarData(symbol=symbol, datetime=mydatetime, volume=volume, open_price=open_price, high_price=high_price, low_price=low_price, close_price=close_price, gateway_name='jq', exchange=exchange, interval=interval)
		# print(barData)
		bar_seq.append(barData)

	db_manager.save_bar_data(bar_seq)
	print("%s bardata insert to db, counts:%s" % (jqsymbol, len(bar_seq)))
#---------------------------------------------------------------------------------------------------------
def first_download_all_contract(db_manager, l, frequency="d"):
	for jqsymbol in l:
		price_df, jqsymbol = download_contract_ochl(jqsymbol, frequency=frequency)
		# print(price_df)
		insert_to_vnpydb(db_manager, price_df, jqsymbol, frequency=frequency)
		

#---------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------
def start_get_data():
	# jqsymbol list
	l = ['I1601.XDCE', 'I1701.XDCE', 'I1801.XDCE', 'I1901.XDCE', 'I2001.XDCE', 'I1605.XDCE', 'I1705.XDCE', 'I1805.XDCE', 'I1905.XDCE', 'I2005.XDCE', 'I1609.XDCE', 'I1709.XDCE', 'I1809.XDCE', 'I1909.XDCE', 'I2009.XDCE']
	l2 = ['M1601.XDCE', 'M1701.XDCE', 'M1801.XDCE', 'M1901.XDCE', 'M2001.XDCE', 'M1605.XDCE', 'M1705.XDCE', 'M1805.XDCE', 'M1905.XDCE', 'M1609.XDCE', 'M1709.XDCE', 'M1809.XDCE', 'M1909.XDCE', ]
	frequency="d"

	login_joinquant()
	database_manager = get_database_manager()

	# end_date = "2018-09-30"
	# end_date = dtt.datetime.now().strftime("%Y-%m-%d")
	# XSGE	XINE	XZCE	XDCE
	first_download_all_contract(database_manager, l, frequency=frequency)



if __name__ == '__main__':
	start_get_data()
# first_download_all_contract()
#
# price,contract = download_contract_ochl("C1909.XDCE", end_date=end_date, frequency="1m")
# print(contract)
# print(price)

# login_joinquant()
# ohlc_df, symbol = download_contract_ochl("RB1909.XSGE", frequency="d")
# print(ohlc_df)