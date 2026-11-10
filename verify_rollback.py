import inspect
import pandas as pd
from modules.context_detector import ContextDetector
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.strategy_mapper import STRATEGY_MAP

src = inspect.getsource(ContextDetector.detect)
src2 = inspect.getsource(IndexLiquidityTrapAdapter.evaluate_signal)

v1 = 'ema9.iloc[-1] > ema20.iloc[-1] > ema50.iloc[-1]' in src
v2 = '0.0001' in src
v3 = 'vwap * 0.0005' in src2
v4 = "'range_atr_threshold': 3.5" in src2
v5 = 'ema50 * 1.005' in src2
v6 = '1.8 * bar' in src2

print(f'EMA stack: {v1}')
print(f'Slope threshold: {v2}')
print(f'VWAP buffer: {v3}')
print(f'ATR threshold: {v4}')
print(f'Trend multiplier: {v5}')
print(f'Vol veto: {v6}')

mr_gone = True
for regime in ['TRENDING_UP', 'TRENDING_DOWN', 'BREAKOUT_SETUP', 'LOW_VOL']:
    names = [c.name for c in STRATEGY_MAP.get(regime, [])]
    if 'MEAN_REVERSION' in names:
        print(f'FAIL: MEAN_REVERSION still in {regime}')
        mr_gone = False

if all([v1, v2, v3, v4, v5, v6, mr_gone]):
    print('ROLLBACK VERIFIED: all 7 spec values + MR removal correct')
else:
    print('VERIFICATION FAILED')
