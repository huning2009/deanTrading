a = 'asd'
d = dict()
d['hu'] = 999
import datetime as dtt
msg = "%s %s : %s" % (dtt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),a,d)
print(msg)
