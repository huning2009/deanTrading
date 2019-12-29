from pymongo import MongoClient
from collections import OrderedDict, deque
import pandas as pd

# client = MongoClient()
# db = client['C_DCE']
# col = db['C1601']
# l = col.find()
# for i in list(l):
# 	print i

# contract = 'C1901.XDCE'

# date = '20%s-%s-01' % (int(contract.split('.')[0][1:3])-1, contract.split('.')[0][3:5])
# # date = int(contract.split('.')[0][1:3])-1
# print(date,11,'asd')

s = pd.Series([1,2,3,4,5,6,7,8,9,10])
print s.quantile(0.9, interpolation='midpoint')