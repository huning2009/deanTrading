from vnpy.trader.utility import round_to
import datetime as dtt
d = dict()
d['a'] = 1
d['b'] = 2

print(dtt.datetime.now())
for i in range(10000000):
    s = d['a']
    s = d['b']
print(dtt.datetime.now())
for i in range(10000000):
    for k,v in d.items():
        s = v
print(dtt.datetime.now())
