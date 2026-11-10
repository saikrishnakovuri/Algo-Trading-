
import sys; sys.path.insert(0,'.')
import pandas as pd
import numpy as np
from datetime import datetime

print('=== FULL DRY RUN ===')

# Step 1: Context detection
from modules.context_detector import ContextDetector
np.random.seed(42)
prices = 24000 + np.cumsum(np.random.randn(60)*20)
df = pd.DataFrame({
    'open': prices*0.999, 'high': prices*1.001,
    'low': prices*0.998, 'close': prices,
    'volume': np.random.randint(1000,5000,60)
}, index=pd.date_range('2026-05-05 09:15', periods=60, freq='5min'))

ctx = ContextDetector().detect(df, vix=14.5)
print(f'Step 1 Context: {ctx.regime} | Vol: {ctx.volatility} | Confidence: {ctx.confidence}')

# Step 2: Strategy mapping
from modules.strategy_mapper import StrategyMapper
candidates = StrategyMapper().get_candidates(ctx)
print(f'Step 2 Candidates: {[c.name for c in candidates]}')

# Step 3: Signal generation
from modules.strategy_selector import MasterStrategySelector
selector = MasterStrategySelector()
signal = selector.select_best_signal(df, 'NIFTY', vix=14.5,
    current_time=datetime(2026,5,5,10,30))
print(f'Step 3 Signal: {signal["strategy"] if signal else "None (normal for synthetic data)"}')

# Step 4: Position sizing
from modules.v3_utils import TOTAL_CAPITAL, NIFTY_LOT_SIZE
risk_amt = TOTAL_CAPITAL * 0.01
premium = 150
lots = int(risk_amt / (premium * NIFTY_LOT_SIZE))
print(f'Step 4 Position: {lots} lots | Risk: ₹{risk_amt}')

print('=== DRY RUN COMPLETE ===')
