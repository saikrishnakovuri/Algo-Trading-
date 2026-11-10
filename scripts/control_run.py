import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
import warnings
warnings.filterwarnings('ignore')

# --- V2 MANDATORY CONFIGURATION (CONTROL RUN: NO VOL) ---
CAPITAL = 500000.0
LOT_SIZE = 65
RISK_PER_TRADE = 5000.0 
BROKERAGE = 70.0
SLIPPAGE_PCT = 0.0005 
PERIOD_START = "2025-01-02"
PERIOD_END = "2026-04-30"
SIGNAL_GATE = time(10, 0)
HARD_CUTOFF = time(12, 0)
FORCE_CLOSE_AT = time(15, 15)
T1_MULT = 1.2 
SL_MULT = 0.6
MAX_TRADES_PER_DAY = 4 
MAX_CONSECUTIVE_LOSSES = 2
COOLDOWN_MIN = 60
DAILY_LOSS_LIMIT = 12500.0
WEEKLY_LOSS_LIMIT = 25000.0

def load_data():
    path = "data/angel_historical/nifty50_18m_1m.csv"
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
    df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    df.set_index(col, inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    df.sort_index(inplace=True)
    df = df[(df.index >= PERIOD_START) & (df.index <= PERIOD_END)]
    
    df_5m = df.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_5m['EMA20'] = df_5m['Close'].ewm(span=20, adjust=False).mean()
    df_5m['EMA50'] = df_5m['Close'].ewm(span=50, adjust=False).mean()
    
    high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    df_5m['ATR'] = tr.rolling(14).mean()
    
    delta = df_5m['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean().replace(0, 0.001)
    df_5m['RSI'] = 100 - (100 / (1 + rs))
    return df_5m.dropna()

def run_v2_backtest_novol():
    df = load_data()
    trades = []
    current_trade, pending = None, None
    day_trades, day_loss, last_date = 0, 0, None
    recent_losses, cooldown_until = [], None
    
    for i in range(21, len(df)):
        ts, bar = df.index[i], df.iloc[i]
        curr_date, curr_time = ts.date(), ts.time()
        
        if last_date != curr_date:
            day_trades, day_loss = 0, 0
            recent_losses, cooldown_until, last_date = [], None, curr_date

        if current_trade:
            exit_px, exit_rsn = None, None
            if current_trade['side'] == 'CE':
                if bar['Low'] <= current_trade['sl']: exit_px, exit_rsn = current_trade['sl'], "SL"
                elif bar['High'] >= current_trade['tp']: exit_px, exit_rsn = current_trade['tp'], "TP"
                elif bar['Close'] < bar['EMA50']: exit_px, exit_rsn = bar['Close'], "REGIME_EXIT"
            
            if not exit_px and curr_time >= FORCE_CLOSE_AT: exit_px, exit_rsn = bar['Close'], "EOD"
            
            if exit_px:
                exit_px_net = exit_px * (1 - SLIPPAGE_PCT)
                pnl = (exit_px_net - current_trade['entry_net']) * current_trade['qty']
                pnl_net = pnl - BROKERAGE
                res = "WIN" if pnl_net > 0 else "LOSS"
                
                trades.append({
                    'PnL': pnl_net, 'Result': res, 'Entry_Time': current_trade['ts']
                })
                if res == "LOSS":
                    day_loss += abs(pnl_net)
                    recent_losses.append(ts)
                    if len(recent_losses) >= 2:
                        if (recent_losses[-1] - recent_losses[-2]).total_seconds() / 60 <= 60:
                            cooldown_until = ts + timedelta(minutes=COOLDOWN_MIN)
                current_trade = None
            continue

        if day_loss >= DAILY_LOSS_LIMIT or day_trades >= MAX_TRADES_PER_DAY or (cooldown_until and ts < cooldown_until): continue

        if pending:
            # CONTROL: VOLUME DISABLED
            if bar['Low'] <= pending['level'] <= bar['High']:
                exec_price = pending['level']
                entry_net = exec_price * (1 + SLIPPAGE_PCT)
                atr = bar['ATR']
                sl = entry_net - (atr * SL_MULT)
                tp = entry_net + (atr * T1_MULT)
                qty = int((5000 / (atr * SL_MULT)) // 65) * 65
                if qty >= 65:
                    current_trade = {'ts': ts, 'entry_idx': i, 'entry_net': entry_net, 'qty': qty, 'sl': sl, 'tp': tp, 'side': 'CE'}
                    day_trades += 1
                pending = None
                continue
            if ts > pending['expiry'] or bar['Close'] < bar['EMA50']: pending = None

        if not current_trade and not pending and SIGNAL_GATE <= curr_time <= HARD_CUTOFF:
            prev_bar = df.iloc[i-1]
            if bar['Close'] > bar['EMA50'] * 1.0005 and bar['Close'] > prev_bar['High'] and bar['RSI'] > 52:
                pending = {'side': 'CE', 'level': prev_bar['High'], 'expiry': ts + timedelta(minutes=60)}
    return trades

if __name__ == "__main__":
    t_list = run_v2_backtest_novol()
    if t_list:
        df = pd.DataFrame(t_list)
        net_pnl = df['PnL'].sum()
        win_rate = (len(df[df['Result'] == 'WIN'])/len(df)) * 100
        print(f"Total trades: {len(df)}")
        print(f"Win rate: {win_rate:.1f}%")
        print(f"Net PnL: ₹{net_pnl:,.0f}")
