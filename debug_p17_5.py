import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, '.')

n = 200
closes = np.full(n, 21000.0)
opens = np.full(n, 20995.0)
highs = np.full(n, 21010.0)
lows = np.full(n, 20990.0)
vols = np.full(n, 10000.0)

for j, c in [(135, 21010), (136, 21025), (137, 21040), (138, 21060)]:
    closes[j], opens[j] = c, c - 6
    highs[j], lows[j] = c + 8, c - 9

closes[139], opens[139] = 21003, 21058
highs[139], lows[139] = 21062, 20993
closes[140], opens[140] = 21068, 21001
highs[140], lows[140] = 21080, 21001
vols[140] = 20000

for i in range(141, n):
    closes[i] = closes[i - 1] + 5
    opens[i] = closes[i] - 3
    highs[i] = closes[i] + 8
    lows[i] = opens[i] - 8

idx = pd.date_range('2025-01-02 09:15', periods=n, freq='5min')
df = pd.DataFrame({'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': vols}, index=idx)

sub = df.iloc[:141].copy()
sub.columns = [c.lower() for c in sub.columns]

# Signal detection logic (from adapter)
tp_series = (sub['high'] + sub['low'] + sub['close']) / 3
vwap_series = (tp_series * sub['volume']).cumsum() / sub['volume'].cumsum()
ema20_series = sub['close'].ewm(span=20, adjust=False).mean()

vwap = vwap_series.iloc[-1]
ema20 = ema20_series.iloc[-1]
bar = sub.iloc[-1]
prev = sub.iloc[-2]
buf = vwap * 0.0005
body = abs(bar['close'] - bar['open'])
rng = max(bar['high'] - bar['low'], 0.01)
vol_avg = sub['volume'].rolling(20).mean().iloc[-1]

print(f"VWAP={vwap:.2f}  EMA20={ema20:.2f}  buf={buf:.2f}")
print(f"prev_low={prev['low']:.2f} <= VWAP={vwap:.2f} : {prev['low'] <= vwap}")
print(f"close={bar['close']:.2f} > vwap+buf={vwap + buf:.2f} : {bar['close'] > vwap + buf}")
print(f"low={bar['low']:.2f} <= vwap+buf={vwap + buf:.2f} : {bar['low'] <= vwap + buf}")
print(f"body_pct={body / rng:.3f} > 0.55 : {body / rng > 0.55}")
print(f"vol_ratio={bar['volume'] / vol_avg:.3f} > 0.75 : {bar['volume'] / vol_avg > 0.75}")
print(f"close={bar['close']:.2f} > ema20={ema20:.2f} : {bar['close'] > ema20}")

from modules.options.signal_adapter import IndexLiquidityTrapAdapter
ad = IndexLiquidityTrapAdapter()
s = ad.evaluate_signal(sub, 'NIFTY', 14.0, 1.0, {}, False)
print(f"evaluate_signal result: {s}")

from modules.context_detector import ContextDetector
det = ContextDetector()
ctx = det.detect(sub, 14.0)
print(f"Detected Regime: {ctx.regime}")
