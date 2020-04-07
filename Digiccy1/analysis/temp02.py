import numpy as np
import pandas as pd
from math import e
import matplotlib.pyplot as plt

arr = np.array(np.linspace(-10,10,num=100))
print(arr)
func = lambda x: 1.0 / (1 + e**-x)

arr_y = func(arr)
fig, ax = plt.subplots(1,1)
ax.plot(arr, arr_y)

plt.show()