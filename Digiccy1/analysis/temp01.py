from vnpy.trader.utility import round_to
import datetime as dtt
import math

dtt1 = dtt.datetime.now()
dtt2 = dtt.datetime(2020,3,9,11,0,0)
print(dtt1)
print(dtt2)
print(math.modf((dtt1-dtt2).seconds/3600)[0]*60)
