import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame([[1,2,2],[5,6,7]])
df.index = [1,2]
df.columns = ['a', 'b', 'c']
df['c'].plot()
plt.show()
