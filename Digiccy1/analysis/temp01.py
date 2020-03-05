from vnpy.trader.utility import round_to
import datetime as dtt
d = dict()
d['a'] = 1
d['b'] = 2

dt1 = dtt.datetime.now()
for i in range(100000):
    s = d['a']
    s = d['b']
dt2 = dtt.datetime.now()
for i in range(100000):
    for k,v in d.items():
        s = v
dt3 = dtt.datetime.now()

print(dt2-dt1)
print(dt3-dt2)
