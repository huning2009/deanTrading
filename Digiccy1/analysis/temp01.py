from vnpy.trader.utility import round_to
import datetime as dtt
import math
from typing import List, Dict, Set, Callable, Any, Type
from collections import defaultdict
import pandas as pd
import numpy as np
import talib as ta

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
l = ['a', 'b']
l.remove("a")
print(l)
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
