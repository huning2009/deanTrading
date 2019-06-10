import os
from pymongo import MongoClient
from jqdatasdk import *
import json
import datetime as dtt
import sqlite3
import re

from vnpy.trader.setting import get_settings, SETTINGS
from vnpy.trader.database.initialize import init
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Direction, Exchange, Interval, Offset, Status, Product, OptionType, OrderType


#---------------------------------------------------------------------------------------------------------
def login_joinquant():
	config = open("joinquant_config.json")
	setting = json.load(config)
	login = auth(setting["USERNAME"],setting["PASSWORD"])
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

def download_contract_ochl(contract, start_date="", end_date="",frequency='daily'):

	if not start_date:
		start_date = '20%s-%s-01' % (int(re.findall(r"\d+", contract)[0][:2])-1, int(re.findall(r"\d+", contract)[0][-2:]))
	if not end_date:
		end_date = dtt.datetime.now().strftime("%Y-%m-%d")
	print(contract,start_date,end_date)
	price = get_price(contract, start_date=start_date, end_date=end_date, frequency=frequency, fields=['open', 'close', 'high', 'low', 'volume'], skip_paused=False, fq='pre')
	price.dropna(axis=0, how='all', inplace=True)
	return price, contract

#---------------------------------------------------------------------------------------------------------
def df_to_BarDataList(ohlc_df, symbol):
	if symbol.split('.')[1][1:] == "ZCE":
		exchange = Exchange("CZCE")
	else:
		exchange = Exchange(symbol.split('.')[1][1:])
		
	barDataList = []
	for index, value in ohlc_df.iterrows():
		index = index.strftime("%Y-%m-%d %H:%M:%S")
		datetime = dtt.datetime.strptime(index, "%Y-%m-%d %H:%M:%S")
		barData = BarData(None, symbol.split('.')[0], exchange, datetime)
		barData.volume = value["volume"]
		barData.open_price = value["open"]
		barData.high_price = value["high"]
		barData.low_price = value["low"]
		barData.close_price = value["close"]
		barData.interval = Interval('1m')

		barDataList.append(barData)

	return barDataList
#---------------------------------------------------------------------------------------------------------

def insertToMongoDB(df, dbName, collectionName):
	client = MongoClient('localhost', 27017)
	db = client[dbName]
	col = db[collectionName]
	for i in range(0, len(df)):
		d = dict(date=df.index[i], open=df.iloc[i,0], close=df.iloc[i,1], high=df.iloc[i,2], low=df.iloc[i,3], vol=df.iloc[i,4])
		col.insert_one(d)

#---------------------------------------------------------------------------------------------------------

def first_download_all_contract():
	l = ['C1601.XDCE', 'C1701.XDCE', 'C1801.XDCE', 'C1901.XDCE', 'C2001.XDCE', 'C1605.XDCE', 'C1705.XDCE', 'C1805.XDCE', 'C1905.XDCE', 'C1609.XDCE', 'C1709.XDCE', 'C1809.XDCE', 'C1909.XDCE', ]
	l2 = ['M1601.XDCE', 'M1701.XDCE', 'M1801.XDCE', 'M1901.XDCE', 'M2001.XDCE', 'M1605.XDCE', 'M1705.XDCE', 'M1805.XDCE', 'M1905.XDCE', 'M1609.XDCE', 'M1709.XDCE', 'M1809.XDCE', 'M1909.XDCE', ]
	for contract in l2:
		price_df, contractName = download_contract_ochl(contract)
		insertToMongoDB(price_df, 'C_DCE', contractName)

#---------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------------------------
def main():
	login_joinquant()
	database_manager = get_database_manager()

	# end_date = "2018-09-30"
	# end_date = dtt.datetime.now().strftime("%Y-%m-%d")
	# XSGE	XINE	XZCE	XDCE
	ohlc_df, symbol = download_contract_ochl("SR1909.XZCE", frequency="1m")
	datas = df_to_BarDataList(ohlc_df, symbol)
	database_manager.save_bar_data(datas)

# main()
if __name__ == '__main__':
	main()
# first_download_all_contract()
# 
# price,contract = download_contract_ochl("C1909.XDCE", end_date=end_date, frequency="1m")
# print(contract)
# print(price)
