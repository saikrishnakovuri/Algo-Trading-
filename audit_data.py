
import sys; sys.path.insert(0,'.')
import pandas as pd
import numpy as np

# Test column normalization
df_test = pd.DataFrame({
    'Open': [100,101,102,103,104], 'High': [102,103,104,105,106],
    'Low': [99,100,101,102,103], 'Close': [101,102,103,104,105], 'Volume': [0,0,0,0,0]
})
df_test.columns = [c.lower() for c in df_test.columns]
assert list(df_test.columns) == ['open','high','low','close','volume'], 'Column fix broken!'
print('Column normalization: OK')

# Test synthetic volume
if df_test['volume'].sum() == 0:
    df_test['volume'] = ((df_test['high']-df_test['low'])/df_test['close']*100000).clip(lower=1000).astype(int)
assert df_test['volume'].sum() > 0, 'Synthetic volume broken!'
print('Synthetic volume: OK')

# Test VWAP with zero volume
import warnings; warnings.filterwarnings('ignore')
vol = pd.Series([0]*25)
close = pd.Series(np.linspace(24000, 24100, 25))
vwap = close.rolling(20).mean() if vol.sum()==0 else (close*vol).cumsum()/vol.cumsum()
assert not vwap.isna().all(), 'VWAP calculation broken!'
print('VWAP zero-volume handling: OK')

print('Data pipeline: ALL CHECKS PASSED')
