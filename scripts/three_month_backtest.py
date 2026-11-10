import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION (3-MONTH AUDIT: Jan, Feb, Apr 2026) ---
CAPITAL = 500000.0
RISK_AMOUNT = 5000.0 
BROKERAGE = 70.0
SLIPPAGE_PCT = 0.0005 
PERIOD_START = "2026-01-01"
PERIOD_END = "2026-04-30"
SIGNAL_GATE = time(9, 45)
HARD_CUTOFF = time(12, 0)
FORCE_CLOSE_AT = time(15, 15)
TP_MULT = 1.5
SL_MULT = 0.6

def load_data():
    path = "data/angel_historical/nifty50_18m_1m.csv"
    df = pd.read_csv(path)
    col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
    df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    df.set_index(col, inplace=True)
    df = df[~df.index.duplicated(keep='first')]
    df.sort_index(inplace=True)
    
    # Isolate to 3 months (Exclude March)
    df = df[((df.index.month == 1) | (df.index.month == 2) | (df.index.month == 4)) & (df.index.year == 2026)]
    
    df_5m = df.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_5m['EMA20'] = df_5m['Close'].ewm(span=20, adjust=False).mean()
    df_5m['EMA50'] = df_5m['Close'].ewm(span=50, adjust=False).mean()
    delta = df_5m['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean().replace(0, 0.001)
    df_5m['RSI'] = 100 - (100 / (1 + rs))
    return df_5m.dropna()

def detect_potential_breakout(bar, prev_bar):
    c, h, l = bar['Close'], bar['High'], bar['Low']
    ema50 = bar['EMA50']
    trend = "TRENDING_UP" if c > ema50 * 1.0005 else ("TRENDING_DOWN" if c < ema50 * 0.9995 else "RANGING")
    if trend == "TRENDING_UP" and c > prev_bar['High'] and bar['RSI'] > 52:
        return {'side': 'CE', 'level': prev_bar['High'], 'trend': trend}
    if trend == "TRENDING_DOWN" and c < prev_bar['Low'] and bar['RSI'] < 48:
        return {'side': 'PE', 'level': prev_bar['Low'], 'trend': trend}
    return None

def run_backtest():
    df = load_data()
    trades, pending = [], None
    current_trade = None
    for i in range(21, len(df)):
        ts, bar = df.index[i], df.iloc[i]
        curr_time = ts.time()
        if current_trade:
            exit_px, exit_rsn = None, None
            if current_trade['side'] == 'CE':
                if bar['Low'] <= current_trade['sl']: exit_px, exit_rsn = current_trade['sl'], "SL"
                elif bar['High'] >= current_trade['tp']: exit_px, exit_rsn = current_trade['tp'], "TP"
                elif bar['Close'] < bar['EMA50']: exit_px, exit_rsn = bar['Close'], "REGIME_EXIT"
            else:
                if bar['High'] >= current_trade['sl']: exit_px, exit_rsn = current_trade['sl'], "SL"
                elif bar['Low'] <= current_trade['tp']: exit_px, exit_rsn = current_trade['tp'], "TP"
                elif bar['Close'] > bar['EMA50']: exit_px, exit_rsn = bar['Close'], "REGIME_EXIT"
            if not exit_px and curr_time >= FORCE_CLOSE_AT: exit_px, exit_rsn = bar['Close'], "EOD"
            if exit_px:
                entry_net = current_trade['entry_raw'] * (1 + SLIPPAGE_PCT) if current_trade['side'] == 'CE' else current_trade['entry_raw'] * (1 - SLIPPAGE_PCT)
                exit_net = exit_px * (1 - SLIPPAGE_PCT) if current_trade['side'] == 'CE' else exit_px * (1 + SLIPPAGE_PCT)
                pnl = (exit_net - entry_net) * current_trade['qty'] if current_trade['side'] == 'CE' else (entry_net - exit_net) * current_trade['qty']
                trades.append({'PnL': pnl - BROKERAGE, 'Result': "WIN" if (pnl - BROKERAGE) > 0 else "LOSS"})
                current_trade = None
            continue
        if pending:
            if (pending['side'] == 'CE' and bar['Low'] <= pending['level'] <= bar['High']) or (pending['side'] == 'PE' and bar['High'] >= pending['level'] >= bar['Low']):
                exec_price = pending['level']
                sl = bar['EMA20']
                dist = abs(exec_price - sl)
                if dist < 15: dist = 15
                qty = int(RISK_AMOUNT / dist)
                current_trade = {'ts': ts, 'entry_raw': exec_price, 'qty': qty, 'sl': sl, 'tp': exec_price + dist * 1.5 if pending['side'] == 'CE' else exec_price - dist * 1.5, 'side': pending['side']}
                pending = None
            elif ts > pending['expiry']: pending = None
        if not current_trade and not pending and SIGNAL_GATE <= curr_time <= HARD_CUTOFF:
            pot = detect_potential_breakout(bar, df.iloc[i-1])
            if pot: pending = {'side': pot['side'], 'level': pot['level'], 'expiry': ts + timedelta(minutes=45)}
    return trades

if __name__ == "__main__":
    t_list = run_backtest()
    df = pd.DataFrame(t_list)
    win_rate = (len(df[df['Result'] == 'WIN'])/len(df)*100)
    print(f"Total trades: {len(df)}")
    print(f"Win rate: {win_rate:.1f}%")
    print(f"Net PnL: ₹{df['PnL'].sum():,.0f}")
