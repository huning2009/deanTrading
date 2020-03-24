import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt

start = '2010-01-01'
end = '2017-02-25'
get_px = lambda x: web.get_data_yahoo(x, start=start, end=end)['Adj Close']

symbols = ['SPY', 'TLT', 'MSFT']
data = pd.DataFrame({sym:get_px(sym) for sym in symbols})

print(data.shape)
re = np.log(data/data.shift(1))
print(re[-5:])

re.plot()
plt.show()