import pandas as pd

values = pd.read_excel('standardValueFreelySwimZebrafishLarvae.xls')

values.to_pickle('standardValueFreelySwimZebrafishLarvae.pkl')
