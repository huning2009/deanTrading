from pymongo import MongoClient, ASCENDING
import datetime as dtt
import pandas as pd
import numpy as np
from collections import OrderedDict, deque
import matplotlib.pyplot as plt

client = MongoClient()
db = client['C_DCE']

def contractVolatilityCone(contractName):
	end_date_str = '20%s-%s-01' % (contractName[1:3], contractName[3:])
	end_date = dtt.datetime.strptime(end_date_str, '%Y-%m-%d')
	print('contract:%s, end_date:%s' % (contractName, end_date_str))
	# mongo to pandas
	collection = db[contractName]
	l = collection.find({"date": {"$lt": end_date}}).sort('date', ASCENDING)
	price_df = pd.DataFrame(list(l))
	price_df.drop('_id', axis=1, inplace=True)
	# print(price_df)

	close_series = price_df[['close']]
	rr_series = close_series.pct_change(fill_method='bfill')
	# rr_std = rr_series.std()*pow(243, 0.5)

	# calculate history volatility
	rr_d = OrderedDict()
	rr_d['rr_21'] = [deque(maxlen=21), []]
	rr_d['rr_42'] = [deque(maxlen=42), []]
	rr_d['rr_63'] = [deque(maxlen=63), []]
	rr_d['rr_84'] = [deque(maxlen=84), []]
	rr_d['rr_105'] = [deque(maxlen=105), []]
	rr_d['rr_126'] = [deque(maxlen=126), []]
	rr_d['rr_147'] = [deque(maxlen=147), []]
	rr_d['rr_168'] = [deque(maxlen=168), []]
	rr_d['rr_189'] = [deque(maxlen=189), []]
	rr_d['rr_210'] = [deque(maxlen=210), []]

	for r in rr_series[1:].values:
		for v in rr_d.values():
			v[0].append(r[0])
			if len(v[0]) >= v[0].maxlen:
				std = pd.Series(v[0]).std()
				v[1].append(std*pow(244, 0.5))
	# calculate volatility quantile
	quantile_d = OrderedDict()
	quantile_l = [10,25,50,75,90]
	for q in quantile_l:
		d = OrderedDict()
		for v in rr_d.values():
			d['vol_%s' % v[0].maxlen] = pd.Series(v[1]).quantile(q/100.0, interpolation='midpoint')
		quantile_d['quantile_%s'% q] = d

	df = pd.DataFrame.from_dict(quantile_d, orient='index')
	print(df)
	df = df.T
	# ax = df.plot(kind='line')
	# ax.set_xticks((21,42,63,84,105,126,147,168,189,210))
	# ax.set_xticklabels(('21','42','63','84','105','126','147','168','189','210'))
	plt.plot(df)
	plt.title(contractName)
	plt.legend(df.columns)
	plt.show()
	return contractName, quantile_d
contractVolatilityCone('C1901')