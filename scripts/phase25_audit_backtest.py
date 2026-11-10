import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION (Phase 25 Calibrated) ---
STARTING_CAPITAL = 500000.0
RISK_PCT = 0.01 
RISK_AMOUNT = STARTING_CAPITAL * RISK_PCT
BROKERAGE = 70.0
SYMBOLS = ["NIFTY"]

def calculate_vwap(df):
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * v).groupby(df.index.date).cumsum() / v.groupby(df.index.date).cumsum().replace(0, 1)

def load_and_prep(symbol):
    path = "data/angel_historical/nifty50_18m_1m.csv"
    if not os.path.exists(path): return None
    
    df = pd.read_csv(path)
    col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
    df['Datetime'] = pd.to_datetime(df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    df.set_index('Datetime', inplace=True)
    
    # 5-minute resampling
    df_5m = df.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_5m['EMA20'] = df_5m['Close'].ewm(span=20, adjust=False).mean()
    df_5m['EMA50'] = df_5m['Close'].ewm(span=50, adjust=False).mean()
    
    high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    df_5m['ATR'] = tr.rolling(14).mean()
    df_5m['VWAP'] = calculate_vwap(df_5m)
    
    delta = df_5m['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean().replace(0, 0.001)
    df_5m['RSI'] = 100 - (100 / (1 + rs))

    if df_5m['Volume'].sum() == 0:
        df_5m['Volume'] = ((df_5m['High'] - df_5m['Low']) / df_5m['Close'] * 100000).clip(lower=1000).astype(int)
    
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

def analyze_failure(df, trade_idx, side, exit_idx, exit_rsn):
    if exit_rsn != "SL": return "N/A"
    entry_bar, exit_bar = df.iloc[trade_idx], df.iloc[exit_idx]
    if (side == 'CE' and exit_bar['Close'] < exit_bar['EMA50']) or (side == 'PE' and exit_bar['Close'] > exit_bar['EMA50']):
        return "TREND_REVERSAL"
    if (exit_idx - trade_idx) <= 3: return "FAKEOUT"
    return "CHOPPY_NOISE"

def run_backtest(symbol):
    df = load_and_prep(symbol)
    if df is None: return []
    trades, current_trade, pending = [], None, None
    
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
            
            if not exit_px and curr_time >= time(15, 15): exit_px, exit_rsn = bar['Close'], "EOD"
            
            if exit_px:
                pnl = (exit_px - current_trade['entry']) * current_trade['qty'] if current_trade['side'] == 'CE' else (current_trade['entry'] - exit_px) * current_trade['qty']
                pnl_net = pnl - BROKERAGE
                prof_pct = (pnl_net / STARTING_CAPITAL) * 100
                
                trades.append({
                    'Symbol': symbol,
                    'Entry_Time': current_trade['ts'],
                    'Exit_Time': ts,
                    'Entry_Strategy': 'RETEST_CONFIRM',
                    'Exit_Strategy': exit_rsn,
                    'Direction': current_trade['side'],
                    'Entry_Price': current_trade['entry'],
                    'Exit_Price': exit_px,
                    'Target_T1': current_trade['tp'],
                    'StopLoss': current_trade['sl'],
                    'PnL': pnl_net,
                    'Profit_Pct': prof_pct,
                    'Result': 'WIN' if pnl_net > 0 else 'LOSS',
                    'Reason': analyze_failure(df, current_trade['entry_idx'], current_trade['side'], i, exit_rsn) if pnl_net <= 0 else "TARGET_HIT",
                    'Trend': current_trade['trend']
                })
                current_trade = None
            continue
            
        if pending:
            retested = False
            if pending['side'] == 'CE' and bar['Low'] <= pending['level'] <= bar['High']: retested = True
            elif pending['side'] == 'PE' and bar['High'] >= pending['level'] >= bar['Low']: retested = True
            
            if retested:
                sl = bar['EMA20']
                dist = abs(pending['level'] - sl)
                if dist <= 0.0001 * pending['level']: dist = 0.002 * pending['level']
                qty = int(RISK_AMOUNT / dist)
                if qty > 0:
                    current_trade = {'ts': ts, 'entry_idx': i, 'strategy': 'RETEST_CONFIRM', 'side': pending['side'], 'entry': pending['level'], 'sl': sl, 'tp': pending['level'] + dist * 1.5 if pending['side'] == 'CE' else pending['level'] - dist * 1.5, 'qty': qty, 'trend': pending['trend']}
                pending = None
            elif ts > pending['expiry'] or (pending['side'] == 'CE' and bar['Close'] < bar['EMA50']) or (pending['side'] == 'PE' and bar['Close'] > bar['EMA50']):
                pending = None 
                
        if not current_trade and not pending and curr_time <= time(12, 0) and curr_time >= time(9, 45):
            pot = detect_potential_breakout(bar, df.iloc[i-1])
            if pot:
                pending = {'side': pot['side'], 'level': pot['level'], 'trend': pot['trend'], 'expiry': ts + timedelta(minutes=45)}
                
    return trades

if __name__ == "__main__":
    print("🚀 Starting 1.5-Year Comprehensive NIFTY Backtest...")
    all_trades = run_backtest("NIFTY")
    
    if not all_trades:
        print("❌ No trades found.")
        exit()
        
    df = pd.DataFrame(all_trades)
    winning_trades = df[df['Result'] == 'WIN']
    loosing_trades = df[df['Result'] == 'LOSS']
    
    winning_trades.to_excel("winning09052026.xlsx", index=False)
    loosing_trades.to_excel("loosing09052026.xlsx", index=False)
    
    print("\n" + "="*60)
    print(f"1.5-YEAR NIFTY REPORT (JAN 2025 - APR 2026)")
    print("="*60)
    print(f"TOTAL TRADES: {len(df)}")
    print(f"WINNING TRADES: {len(winning_trades)}")
    print(f"LOSING TRADES: {len(loosing_trades)}")
    print(f"WIN RATE: {(len(winning_trades)/len(df)*100):.2f}%")
    print(f"NET PNL: ₹{df['PnL'].sum():,.2f}")
    print(f"ROI: {((df['PnL'].sum()/STARTING_CAPITAL)*100):.2f}%")
    print("="*60)
    print("💾 Files saved: winning09052026.xlsx, loosing09052026.xlsx")
