from vnpy.trader.utility import round_to
import datetime as dtt
import math
from typing import List, Dict, Set, Callable, Any, Type
from collections import defaultdict
import pandas as pd
import numpy as np
import talib as ta
import numpy as np
import copy
from collections import defaultdict
from typing import Dict, List, Set, Callable
import matplotlib.pyplot as plt

a = 10
a *= 1.5
print(a)
"""
x = np.random.poisson(1,100000)
y = np.random.random(10)
fig, ax = plt.subplots(2,1)
ax[0].hist(x)
ax[1].plot(y)
plt.show()"""
# arr = np.zeros(10)
# for i in range(10):
#     arr[i] = i
# print(arr)
# ts = 1585333791054
# dt = dtt.datetime.fromtimestamp(ts/1000)
# print(dt.strftime("%Y-%m-%d %H:%M:%S.%f"))


""" list index

l = ['a', 'as', 'b', 'bb']
l[l.index('bb')] = None
print(l)
"""
"""
bids = np.array([[1.2,100], [1.1, 20], [1.0, 102]])
print(bids)
b = copy.copy(bids)
b[0,0] = 999
print(b)
print(bids)
"""
# c = bids[bids[:,0]>1.05].shape[0]
# bids[:c,1] = np.cumsum(bids[:c,1], axis=0)
# print(bids[c-1:,:])
"""
print(bids[bids[:,1] > 100].shape)
bids[:,1][bids[:,1] > 100] = 0
print(bids)"""
"""  np.where
print(bids[1])
min_value = min(abs(bids[:,0]- 1.051))
arr_index = np.where(abs(bids[:,0]-1.051)==min_value)
print(arr_index)
print(bids[arr_index,1].shape)
"""
# for n in bids:
#     print(n)

# l = ['a', 'b', 'c']
# l1= []
# l1.extend([i,1,2] for i in l)
# print(l1)
# l = ['a', 1]
# arr = np.array([[9, 1], [9, 1]])
# print(np.cumsum(arr, axis=0))
# arr[:,1] = np.cumsum(arr[:,1])
# print(arr)

# df = pd.DataFrame(columns=['price', 'vol', 'symbol'])
# # print(df)
# df.loc['a'] = [1,2, 'btc']
# df.loc['b'] = [11,21, 'btc']

# def print_index(x):
#     print(x['vol'])


# df.apply(print_index, axis=1)
"""class AAA:
    def __init__(self):
        self.a =11
aaa = AAA()

print(isinstance(aaa,AAA))"""
"""
df = pd.Series([1,2,3,4,5,6,7,8])
s1 = (df.diff()/df).std()
print(s1)
"""
# df = pd.DataFrame([[1,2],[2,3],[3,4]])
# print(df.iloc[-2:,:])
"""
std = np.std(df['close'])
print(std)
u,m,d = ta.BBANDS(df['close'],2)
print(u.iloc[-1])
atr = ta.ATR(df['high'], df['low'], df['close'], 2)
print(atr.iloc[-1])
"""
# arr = np.array([[1.1,2],[1.0, 4], [0.9,3], [0.8,4]])

# print(type(arr))
# arr = np.array([1.0,2.0,3.,4.,5.])
# print(arr)
# u,m,d = ta.BBANDS(arr, 5)
# print(u[-1])
# print(m)
# print(d)
# df1 = pd.DataFrame([[1,2,3],[4,5,6]])
# df2 = pd.DataFrame([['a'],['b'],['c']])
# df1.set_index(pd.date_range('2020-1-1', '2020-1-2'), inplace=True)
# df2.set_index(pd.date_range('2020-1-1', '2020-1-3'), inplace=True)
# print(df2)
# df = pd.concat([df1,df2], axis=1, join='inner')
# print(df)
# class ABC:
#     def __init__(self):
#         self.d1: Dict(str, List) = defaultdict(list)
# now = dtt.datetime.now()
# print(now.minute)
# a = 10
# a = -a
# print(a)
# abc = ABC()
# abc.d1['a'].append(1)
# print(abc.d1)

# l1 = []
# l11 = [dtt.datetime.now(),"asd"]
# l1.append(l11)
# print(l1)
# l1.remove(l11)
# print(l1)

# params = {
#     "symbol": 'req.symbol',
#     "side": 'DIRECTION_VT2BINANCE[req.direction]',
#     "type": 'ORDERTYPE_VT2BINANCE[req.type]',
#     "price": 'str(req.price)',
#     "quantity": 'str(req.volume)',
#     "newClientOrderId": 'orderid',
#     "timeInForce": 'IOC',
#     "newOrderRespType": "ACK"
# }
   
# params["sideEffectType"]= 'sideEffectType'

# print(params)
