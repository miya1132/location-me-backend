# %%

import pandas_datareader.data as data

df = data.DataReader("INTC", "stooq").sort_index()
print(df.head())
