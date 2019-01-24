from pymongo import MongoClient
from jqdatasdk import *

login = auth('15542377707','huqinghua129')
print('login')
client = MongoClient('localhost', 27017)
# # all_securities = get_all_securities(types=[], date=None)
# # print(all_securities)
def download_contract_ochl(contract):
	start_date = '20%s-%s-01' % (int(contract.split('.')[0][1:3])-1, contract.split('.')[0][3:5])
	end_date = '20%s-%s-30' % (contract.split('.')[0][1:3], contract.split('.')[0][3:5])
	print(contract,start_date,end_date)
	price = get_price(contract, start_date=start_date, end_date=end_date, frequency='daily', fields=None, skip_paused=False, fq='pre')
	price.dropna(axis=0, how='all', inplace=True)
	return price, contract.split('.')[0]

def insertToMongoDB(df, dbName, collectionName):
	for i in range(0, len(df)):
		d = dict(date=df.index[i], open=df.iloc[i,0], close=df.iloc[i,1], high=df.iloc[i,2], low=df.iloc[i,3], vol=df.iloc[i,4])

		db = client[dbName]
		col = db[collectionName]
		col.insert_one(d)

def first_download_all_contract():
	l = ['C1601.XDCE', 'C1701.XDCE', 'C1801.XDCE', 'C1901.XDCE', 'C2001.XDCE', 'C1605.XDCE', 'C1705.XDCE', 'C1805.XDCE', 'C1905.XDCE', 'C1609.XDCE', 'C1709.XDCE', 'C1809.XDCE', 'C1909.XDCE', ]
	l2 = ['M1601.XDCE', 'M1701.XDCE', 'M1801.XDCE', 'M1901.XDCE', 'M2001.XDCE', 'M1605.XDCE', 'M1705.XDCE', 'M1805.XDCE', 'M1905.XDCE', 'M1609.XDCE', 'M1709.XDCE', 'M1809.XDCE', 'M1909.XDCE', ]
	for contract in l2:
		price_df, contractName = download_contract_ochl(contract)
		insertToMongoDB(price_df, 'C_DCE', contractName)

first_download_all_contract()