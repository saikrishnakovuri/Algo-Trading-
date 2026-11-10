import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
import warnings
warnings.filterwarnings('ignore')

# --- DEFINITIVE V1 AUDIT (43.7% WR BASELINE) ---
CAPITAL = 500000.0
LOT_SIZE = 65
RISK_PER_TRADE = 5000.0 
BROKERAGE = 70.0
SLIPPAGE_PCT = 0.0 # V1 used level-entry (idealized)
PERIOD_START = "2025-01-02"
PERIOD_END = "2026-04-30"
SIGNAL_GATE = time(9, 45)
HARD_CUTOFF = time(12, 0) # Per recent instruction
FORCE_CLOSE_AT = time(15, 15)
TP_MULT = 1.5 # V1

def load_data():
    path = "data/angel_historical/nifty50_18m_1m.csv"
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
    
    # RSI
    delta = df_5m['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean().replace(0, 0.001)
    df_5m['RSI'] = 100 - (100 / (1 + rs))
    return df_5m.dropna()

def detect_potential_breakout(bar, prev_bar):
    c, h, l = bar['Close'], bar['High'], bar['Low']
    ema50 = bar['EMA50']
    trend = "TRENDING_UP" if c > ema50 * 1.0005 else ("TRENDING_DOWN" if c < ema50 * 0.9995 else "RANGING")
    
    if trend == "TRENDING_UP" and c > prev_bar['High'] and bar['RSI'] > 51:
        return {'side': 'CE', 'level': prev_bar['High'], 'trend': trend}
    if trend == "TRENDING_DOWN" and c < prev_bar['Low'] and bar['RSI'] < 49:
        return {'side': 'PE', 'level': prev_bar['Low'], 'trend': trend}
    return None

def run_v1_audit():
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
                pnl = (exit_px - current_trade['entry']) * current_trade['qty'] if current_trade['side'] == 'CE' else (current_trade['entry'] - exit_px) * current_trade['qty']
                pnl_net = pnl - BROKERAGE
                trades.append({
                    'Symbol': 'NIFTY', 'Entry_Time': current_trade['ts'], 'Exit_Time': ts,
                    'Direction': current_trade['side'], 'Entry_Price': current_trade['entry'], 'Exit_Price': exit_px,
                    'PnL': pnl_net, 'Profit_Pct': (pnl_net/CAPITAL)*100, 'Result': "WIN" if pnl_net > 0 else "LOSS",
                    'Reason': exit_rsn if pnl_net <= 0 else "TARGET_HIT", 'Trend': current_trade['trend']
                })
                current_trade = None
            continue

        if pending:
            retested = False
            if (pending['side'] == 'CE' and bar['Low'] <= pending['level'] <= bar['High']): retested = True
            elif (pending['side'] == 'PE' and bar['High'] >= pending['level'] >= bar['Low']): retested = True
            
            if retested:
                exec_price = pending['level']
                sl = bar['EMA20']
                dist = abs(exec_price - sl)
                if dist < 15: dist = 15
                qty = int((RISK_PER_TRADE / dist) // 65) * 65
                if qty >= 65:
                    current_trade = {
                        'ts': ts, 'entry': exec_price, 'qty': qty, 'sl': sl, 
                        'tp': exec_price + dist * 1.5 if pending['side'] == 'CE' else exec_price - dist * 1.5, 
                        'side': pending['side'], 'trend': pending['trend']
                    }
                pending = None
            elif ts > pending['expiry']:
                pending = None

        if not current_trade and not pending and SIGNAL_GATE <= curr_time <= HARD_CUTOFF:
            pot = detect_potential_breakout(bar, df.iloc[i-1])
            if pot:
                pending = {'side': pot['side'], 'level': pot['level'], 'trend': pot['trend'], 'expiry': ts + timedelta(minutes=60)}

    return trades

if __name__ == "__main__":
    t_list = run_v1_audit()
    df = pd.DataFrame(t_list)
    winning = df[df['Result'] == 'WIN']
    loosing = df[df['Result'] == 'LOSS']
    winning.to_excel("winning09052026.xlsx", index=False)
    loosing.to_excel("loosing09052026.xlsx", index=False)
    
    net_pnl = df['PnL'].sum()
    print(f"\n[1.5-YEAR V1 AUDIT COMPLETE]")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(len(winning)/len(df)*100):.1f}%")
    print(f"Net PnL: ₹{net_pnl:,.0f} | ROI: {(net_pnl/CAPITAL)*100:.2f}%")
