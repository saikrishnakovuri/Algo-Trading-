import pandas as pd
import numpy as np
import os
from datetime import datetime, time
import multiprocessing as mp
import warnings
warnings.filterwarnings('ignore')

# Constants from previous test
CAPITAL = 100000.0
RISK_PCT = 0.01
RISK_AMOUNT = CAPITAL * RISK_PCT
BROKERAGE = 87.0
LEVERAGE_CAP = 5.0
MAX_POS_VALUE = CAPITAL * LEVERAGE_CAP

NIFTY50 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'TCS', 'INFY', 'SBIN', 'BHARTIARTL', 'LT', 'KOTAKBANK', 'TITAN']
MIDCAP = ['ADANIENT', 'TATAPOWER', 'ZOMATO', 'IRCTC', 'POLYCAB']
SYMBOLS = NIFTY50 + MIDCAP

# 30-Day Master Date List
SET1_DATES = ['2025-10-29', '2025-11-06', '2025-11-07', '2025-11-10', '2025-11-18', '2025-11-19', '2025-11-21', '2026-03-23', '2026-03-27', '2026-04-06']
SET2_DATES = ['2025-11-11', '2025-11-14', '2025-11-24', '2025-11-25', '2025-11-27', '2025-11-28', '2025-12-15', '2026-03-10', '2026-03-11', '2026-04-07']
SET3_DATES = ['2025-10-30', '2025-11-20', '2025-12-16', '2025-12-17', '2025-12-22', '2026-03-12', '2026-03-13', '2026-03-30', '2026-04-02', '2026-04-24']
ALL_DATES = SET1_DATES + SET2_DATES + SET3_DATES

def calculate_vwap(df):
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * v).groupby(df.index.date).cumsum() / v.groupby(df.index.date).cumsum()

def load_and_prep(symbol):
    path = None
    for d in ['data/angel_historical', 'data/nifty200']:
        p = os.path.join(d, f"{symbol}_1m.csv")
        if os.path.exists(p):
            path = p; break
    if not path: return None
    
    df = pd.read_csv(path)
    col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
    df['Datetime'] = pd.to_datetime(df[col]).dt.tz_localize(None)
    df.set_index('Datetime', inplace=True)
    df_5m = df.resample('5min').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    
    df_5m['EMA20'] = df_5m['Close'].ewm(span=20, adjust=False).mean()
    df_5m['EMA50'] = df_5m['Close'].ewm(span=50, adjust=False).mean()
    
    # ATR & Avg ATR
    high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    df_5m['ATR'] = tr.rolling(14).mean()
    df_5m['ATR_Avg'] = df_5m['ATR'].rolling(20).mean()
    
    # VWAP
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['Highest20'] = df_5m['High'].rolling(20).max().shift(1)
    df_5m['Lowest20'] = df_5m['Low'].rolling(20).min().shift(1)
    df_5m['SwingH'] = df_5m['High'].rolling(5).max().shift(1)
    df_5m['SwingL'] = df_5m['Low'].rolling(5).min().shift(1)
    
    # Vol Average
    df_5m['Vol_Avg'] = df_5m['Volume'].rolling(20).mean()
    
    return df_5m.dropna()

def tag_vwap_bounce(bar, prev_bar, df_slice):
    """Detects VWAP_BOUNCE and tags with 6 context variables."""
    c, o, h, l, v = bar['Close'], bar['Open'], bar['High'], bar['Low'], bar['Volume']
    vwap = bar['VWAP']
    
    side = None
    # Long: Touch VWAP and close above
    if l <= vwap and c > vwap and o >= vwap: side = 'CE'
    # Short: Touch VWAP and close below
    elif h >= vwap and c < vwap and o <= vwap: side = 'PE'
    
    if not side: return None
    
    # A. TREND CONTEXT
    ema50 = bar['EMA50']
    ema50_prev = prev_bar['EMA50']
    trend = "RANGING"
    if c > ema50 * 1.005 and ema50 > ema50_prev: trend = "TRENDING_UP"
    elif c < ema50 * 0.995 and ema50 < ema50_prev: trend = "TRENDING_DOWN"
    
    # B. BOUNCE TYPE
    b_type = "VWAP_PULL" if side == 'CE' else "VWAP_PUSH"
    if abs(l - bar['Lowest20']) < (bar['ATR']*0.5): b_type = "SUPPORT_BOUNCE"
    if abs(c - bar['EMA20']) < (bar['ATR']*0.2): b_type = "EMA_BOUNCE"
    
    # C. VOLATILITY REGIME
    vol_regime = "NORMAL_VOL"
    if bar['ATR'] < 0.7 * bar['ATR_Avg']: vol_regime = "LOW_VOL"
    elif bar['ATR'] > 1.3 * bar['ATR_Avg']: vol_regime = "HIGH_VOL"
    
    # D. TIME OF DAY
    t = bar.name.time()
    tod = "MORNING"
    if t >= time(13, 30): tod = "AFTERNOON"
    elif t >= time(11, 30): tod = "MIDDAY"
    
    # E. CANDLE STRENGTH
    body = abs(c - o)
    full_range = h - l if (h - l) > 0 else 0.01
    body_pct = body / full_range
    strength = "DOJI_BOUNCE"
    if body_pct > 0.6: strength = "STRONG_BOUNCE"
    elif body_pct < 0.3: strength = "WEAK_BOUNCE"
    
    # F. VOLUME CONFIRMATION
    v_conf = "NORMAL_VOLUME"
    if v > 1.5 * bar['Vol_Avg']: v_conf = "VOLUME_SURGE"
    elif v < 0.7 * bar['Vol_Avg']: v_conf = "LOW_VOLUME"
    
    return {
        'side': side, 'entry': c,
        'trend': trend, 'b_type': b_type, 'vol_regime': vol_regime,
        'tod': tod, 'strength': strength, 'v_conf': v_conf
    }

def simulate_context_trade(df, sig_idx, sig_data, sl_type, tp_type):
    active = {
        'side': sig_data['side'], 'entry': sig_data['entry'], 'qty': 0, 
        'sl': 0, 'tp': 0, 't1': 0, 't1_r': 0, 'dist': 0, 'part_booked': False
    }
    
    bar_entry = df.loc[sig_idx]
    entry = sig_data['entry']
    side = sig_data['side']
    
    # Calc SL
    sl = None
    if sl_type == 'SL_EMA20': sl = bar_entry['EMA20']
    elif sl_type == 'SL_EMA50': sl = bar_entry['EMA50']
    elif sl_type == 'SL_ATR_1': sl = entry - 1.0*bar_entry['ATR'] if side == 'CE' else entry + 1.0*bar_entry['ATR']
    elif sl_type == 'SL_ATR_2': sl = entry - 2.0*bar_entry['ATR'] if side == 'CE' else entry + 2.0*bar_entry['ATR']
    elif sl_type == 'SL_CANDLE': sl = bar_entry['Low'] if side == 'CE' else bar_entry['High']
    elif sl_type == 'SL_SWING': sl = bar_entry['SwingL'] if side == 'CE' else bar_entry['SwingH']
    elif sl_type == 'SL_FIXED_1PCT': sl = entry*0.99 if side == 'CE' else entry*1.01
    
    if sl is None or pd.isna(sl): return None
    dist = abs(entry - sl)
    if dist < 0.0001*entry: dist = 0.001*entry
    if side == 'CE' and sl >= entry: sl = entry - dist
    if side == 'PE' and sl <= entry: sl = entry + dist
    
    qty = int(RISK_AMOUNT / dist)
    max_q = int(MAX_POS_VALUE / entry)
    qty = min(qty, max_q)
    if qty <= 0: return None
    
    # Calc TP
    tp = None
    t1, t1_r = None, None
    if tp_type == 'TP_FIX_1_5R': tp = entry + 1.5*dist if side == 'CE' else entry - 1.5*dist
    elif tp_type == 'TP_FIX_2R': tp = entry + 2.0*dist if side == 'CE' else entry - 2.0*dist
    elif tp_type == 'TP_FIB': tp = entry + 1.618*dist if side == 'CE' else entry - 1.618*dist
    elif tp_type == 'TP_SR': tp = bar_entry['Highest20'] if side == 'CE' else bar_entry['Lowest20']
    elif tp_type == 'TP_PARTIAL_1R': t1, t1_r = (entry + 1.0*dist if side == 'CE' else entry - 1.0*dist), 1.0
    elif tp_type == 'TP_PARTIAL_1_5R': t1, t1_r = (entry + 1.5*dist if side == 'CE' else entry - 1.5*dist), 1.5
    
    active.update({'sl': sl, 'tp': tp, 't1': t1, 't1_r': t1_r, 'qty': qty, 'dist': dist})
    
    # Run simulation from sig_idx + 1
    start_pos = df.index.get_loc(sig_idx) + 1
    for i in range(start_pos, len(df)):
        bar = df.iloc[i]
        curr_time = bar.name.time()
        exit_px, exit_rsn = None, None
        
        # SL/TP logic
        if side == 'CE' and bar['Low'] <= active['sl']: exit_px, exit_rsn = active['sl'], "SL"
        elif side == 'PE' and bar['High'] >= active['sl']: exit_px, exit_rsn = active['sl'], "SL"
        
        if not exit_px:
            if side == 'CE':
                if tp_type in ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR'] and bar['High'] >= active['tp']: exit_px, exit_rsn = active['tp'], "TP"
                elif t1:
                    if not active['part_booked'] and bar['High'] >= active['t1']:
                        active['part_booked'], active['sl'] = True, active['entry']
                    if active['part_booked']:
                        r_reach = (bar['High'] - active['entry'])/active['dist']
                        steps = int((r_reach - active['t1_r'])/0.5)
                        if steps > 0: active['sl'] = max(active['sl'], active['entry'] + (active['t1_r'] - 0.5 + steps*0.5)*active['dist'])
                elif tp_type == 'TP_TRAIL_ATR':
                    active['sl'] = max(active['sl'], bar['Close'] - 1.5*bar['ATR'])
            else: # PE
                if tp_type in ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR'] and bar['Low'] <= active['tp']: exit_px, exit_rsn = active['tp'], "TP"
                elif t1:
                    if not active['part_booked'] and bar['Low'] <= active['t1']:
                        active['part_booked'], active['sl'] = True, active['entry']
                    if active['part_booked']:
                        r_reach = (active['entry'] - bar['Low'])/active['dist']
                        steps = int((r_reach - active['t1_r'])/0.5)
                        if steps > 0: active['sl'] = min(active['sl'], active['entry'] - (active['t1_r'] - 0.5 + steps*0.5)*active['dist'])
                elif tp_type == 'TP_TRAIL_ATR':
                    active['sl'] = min(active['sl'], bar['Close'] + 1.5*bar['ATR'])

        # EMA Close logic
        if not exit_px:
            if sl_type == 'SL_EMA20':
                if (side == 'CE' and bar['Close'] < bar['EMA20']) or (side == 'PE' and bar['Close'] > bar['EMA20']): exit_px, exit_rsn = bar['Close'], "SL_EMA"
            elif sl_type == 'SL_EMA50':
                if (side == 'CE' and bar['Close'] < bar['EMA50']) or (side == 'PE' and bar['Close'] > bar['EMA50']): exit_px, exit_rsn = bar['Close'], "SL_EMA"

        if not exit_px and curr_time >= time(15, 15): exit_px, exit_rsn = bar['Close'], "EOD"
        
        if exit_px:
            pnl = (exit_px - active['entry']) * active['qty'] if side == 'CE' else (active['entry'] - exit_px) * active['qty']
            if t1 and active['part_booked']:
                p1 = abs(active['t1'] - active['entry']) * (active['qty']/2)
                p2 = (exit_px - active['entry']) * (active['qty']/2) if side == 'CE' else (active['entry'] - exit_px) * (active['qty']/2)
                pnl = p1 + p2
            return pnl - BROKERAGE
    return 0

def process_stock_adaptive(args):
    symbol, all_days = args
    df = load_and_prep(symbol)
    if df is None: return []
    
    df = df[np.isin(df.index.date, [datetime.strptime(d, '%Y-%m-%d').date() for d in ALL_DATES])]
    if df.empty: return []
    
    sl_types = ['SL_EMA20', 'SL_EMA50', 'SL_ATR_1', 'SL_ATR_2', 'SL_CANDLE', 'SL_SWING', 'SL_FIXED_1PCT']
    tp_types = ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR', 'TP_PARTIAL_1R', 'TP_PARTIAL_1_5R', 'TP_TRAIL_ATR']
    
    stock_results = []
    for i in range(1, len(df)):
        bar = df.iloc[i]
        tag = tag_vwap_bounce(bar, df.iloc[i-1], df.iloc[:i+1])
        if tag:
            # Simulate all 49 exit combos for THIS specific signal
            for sl in sl_types:
                for tp in tp_types:
                    net_pnl = simulate_context_trade(df, df.index[i], tag, sl, tp)
                    if net_pnl is not None:
                        res = tag.copy()
                        res.update({'Stock': symbol, 'Date': df.index[i].date(), 'SL': sl, 'TP': tp, 'Net_PnL': net_pnl, 'Win': 1 if net_pnl > 0 else 0})
                        stock_results.append(res)
    return stock_results

if __name__ == '__main__':
    print(f"🚀 Starting Context-Adaptive Backtest on {len(SYMBOLS)} stocks across 30 days...")
    pool_args = [(s, ALL_DATES) for s in SYMBOLS]
    
    with mp.Pool(mp.cpu_count()) as pool:
        all_results_list = pool.map(process_stock_adaptive, pool_args)
    
    all_trades = [r for sublist in all_results_list for r in sublist]
    df_all = pd.DataFrame(all_trades)
    
    if df_all.empty:
        print("No trades found.")
        exit()
        
    print(f"✅ Total data points generated: {len(df_all):,}")
    
    # ANALYSIS: Group by each context variable to find best exit
    context_vars = ['trend', 'vol_regime', 'b_type', 'tod', 'strength', 'v_conf']
    
    writer = pd.ExcelWriter("Context_Adaptive_Exits.xlsx", engine='openpyxl')
    df_all.to_excel(writer, sheet_name="Raw_Trades_Context", index=False)
    
    decision_matrix = []
    rules = []
    
    for var in context_vars:
        # Find best SL/TP for each value of context variable
        summary = df_all.groupby([var, 'SL', 'TP']).agg({'Net_PnL': 'sum', 'Win': 'mean', 'Date': 'count'}).rename(columns={'Date': 'Trades'})
        summary = summary.reset_index()
        
        # For each value of context (e.g., TRENDING_UP), find the row with max PnL
        best_per_context = summary.loc[summary.groupby(var)['Net_PnL'].idxmax()]
        decision_matrix.append(best_per_context)
        
        # Build Rules
        for _, row in best_per_context.iterrows():
            if row['Net_PnL'] > 0:
                rules.append(f"IF {var} == {row[var]}: use {row['SL']} + {row['TP']} (WR: {row['Win']*100:.1f}%, PnL: {row['Net_PnL']:.0f})")
            else:
                rules.append(f"IF {var} == {row[var]}: NO TRADE ZONE (All combos negative)")

    pd.concat(decision_matrix).to_excel(writer, sheet_name="Decision_Matrix", index=False)
    pd.DataFrame({'Rules': rules}).to_excel(writer, sheet_name="Rule_Set", index=False)
    
    # Sheet 4: No Trade Zones (Contexts where total PnL is negative across all strategies)
    no_trades = []
    for var in context_vars:
        ctx_pnl = df_all.groupby(var)['Net_PnL'].sum()
        for ctx, pnl in ctx_pnl.items():
            if pnl < 0: no_trades.append({'Context_Variable': var, 'Value': ctx, 'Aggregate_PnL': pnl})
    pd.DataFrame(no_trades).to_excel(writer, sheet_name="No_Trade_Zones", index=False)
    
    writer.save()
    print("\n✅ Context-Adaptive Analysis complete! File: Context_Adaptive_Exits.xlsx")
    
    # Output top rules to console
    print("\n🏆 KEY ADAPTIVE RULES:")
    for r in rules[:10]: print(f" - {r}")
