
import sys; sys.path.insert(0,'.')
from modules.v3_utils import (
    TOTAL_CAPITAL, MAX_TRADES_PER_DAY,
    MAX_CONSECUTIVE_LOSSES, DAILY_LOSS_LIMIT_PCT,
    NIFTY_LOT_SIZE, BANKNIFTY_LOT_SIZE
)
print('Risk Parameters:')
print(f'  Capital:           ₹{TOTAL_CAPITAL:,.0f}')
print(f'  Max trades/day:    {MAX_TRADES_PER_DAY}')
print(f'  Consec loss stop:  {MAX_CONSECUTIVE_LOSSES}')
print(f'  Daily loss limit:  {DAILY_LOSS_LIMIT_PCT*100}%')
print(f'  NIFTY lot size:    {NIFTY_LOT_SIZE}')
print(f'  BANKNIFTY lot:     {BANKNIFTY_LOT_SIZE}')
print('Risk params: OK')

# Test position sizing formula
risk_amt = TOTAL_CAPITAL * 0.01  # 1%
premium = 150
lots = int(risk_amt / (premium * NIFTY_LOT_SIZE))
print(f'Position sizing test: Risk ₹{risk_amt} | Premium ₹{premium} | Lots: {lots}')
assert lots >= 1, 'Position sizing returned 0 lots!'
print('Position sizing: OK')
