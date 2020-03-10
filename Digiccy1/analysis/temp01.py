from vnpy.trader.utility import round_to
import datetime as dtt
import math
from typing import List, Dict, Set, Callable, Any, Type
from collections import defaultdict

# class ABC:
#     def __init__(self):
#         self.d1: Dict(str, List) = defaultdict(list)

# abc = ABC()
# abc.d1['a'].append(1)
# print(abc.d1)

l1 = []
l11 = [dtt.datetime.now(),"asd"]
l1.append(l11)
print(l1)
l1.remove(l11)
print(l1)