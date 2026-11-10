import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, time
import multiprocessing as mp
import warnings
warnings.filterwarnings('ignore')

CAPITAL = 100000.0
RISK_PCT = 0.01
RISK_AMOUNT = CAPITAL * RISK_PCT
BROKERAGE = 87.0
LEVERAGE_CAP = 5.0
MAX_POS_VALUE = CAPITAL * LEVERAGE_CAP

NIFTY50 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'TCS', 'INFY', 'SBIN', 'BHARTIARTL', 'LT', 'KOTAKBANK', 'TITAN']
MIDCAP = ['ADANIENT', 'TATAPOWER', 'ZOMATO', 'IRCTC', 'POLYCAB']
SYMBOLS = NIFTY50 + MIDCAP

def is_excluded(d):
    m, day = d.month, d.day
    if m == 12 and 1 <= day <= 12: return True
    if m == 12 and 24 <= day <= 31: return True
    if m == 1 and 1 <= day <= 31: return True
    if m == 2 and 1 <= day <= 29: return True
    if m == 3 and 1 <= day <= 6: return True
    if m == 4 and 8 <= day <= 20: return True
    return False

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
    
    df_5m['EMA9'] = df_5m['Close'].ewm(span=9, adjust=False).mean()
    df_5m['EMA20'] = df_5m['Close'].ewm(span=20, adjust=False).mean()
    df_5m['EMA21'] = df_5m['Close'].ewm(span=21, adjust=False).mean()
    df_5m['EMA50'] = df_5m['Close'].ewm(span=50, adjust=False).mean()
    
    high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    df_5m['ATR'] = tr.rolling(14).mean()
    
    delta = df_5m['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
    df_5m['RSI'] = 100 - (100 / (1 + rs))
    
    sma20 = df_5m['Close'].rolling(20).mean()
    std20 = df_5m['Close'].rolling(20).std()
    df_5m['BBU'] = sma20 + 2*std20
    df_5m['BBL'] = sma20 - 2*std20
    
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['Highest20'] = df_5m['High'].rolling(20).max().shift(1)
    df_5m['Lowest20'] = df_5m['Low'].rolling(20).min().shift(1)
    df_5m['SwingH'] = df_5m['High'].rolling(5).max().shift(1)
    df_5m['SwingL'] = df_5m['Low'].rolling(5).min().shift(1)
    
    return df_5m.dropna()

def detect_entries(df):
    entries = {k: [] for k in ['LIQUIDITY_TRAP', 'MOMENTUM_FOLLOW', 'MEAN_REVERSION', 'CONFIRMED_MR', 'EMA_CROSSOVER', 'VWAP_BOUNCE', 'BREAKOUT_RETEST']}
    
    for i in range(21, len(df)-1): # Reserve last bar for exit check
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        next_bar = df.iloc[i+1] # Peek for CONFIRMED_MR
        
        # Base Data
        c, o, h, l = bar['Close'], bar['Open'], bar['High'], bar['Low']
        pc, po = prev_bar['Close'], prev_bar['Open']
        h20, l20 = bar['Highest20'], bar['Lowest20']
        
        # 1 & 2. Breakouts
        is_bo_up = c > h20 and pc <= h20
        is_bo_dn = c < l20 and pc >= l20
        
        if is_bo_up:
            entries['MOMENTUM_FOLLOW'].append({'idx': i, 'side': 'CE', 'entry': c})
            entries['LIQUIDITY_TRAP'].append({'idx': i, 'side': 'PE', 'entry': c})
        if is_bo_dn:
            entries['MOMENTUM_FOLLOW'].append({'idx': i, 'side': 'PE', 'entry': c})
            entries['LIQUIDITY_TRAP'].append({'idx': i, 'side': 'CE', 'entry': c})
            
        # 3. Mean Reversion
        if bar['RSI'] < 30 and c < bar['BBL']:
            entries['MEAN_REVERSION'].append({'idx': i, 'side': 'CE', 'entry': c})
            if next_bar['Close'] > next_bar['Open']: # Confirmed
                entries['CONFIRMED_MR'].append({'idx': i+1, 'side': 'CE', 'entry': next_bar['Close']})
        if bar['RSI'] > 70 and c > bar['BBU']:
            entries['MEAN_REVERSION'].append({'idx': i, 'side': 'PE', 'entry': c})
            if next_bar['Close'] < next_bar['Open']:
                entries['CONFIRMED_MR'].append({'idx': i+1, 'side': 'PE', 'entry': next_bar['Close']})
                
        # 5. EMA Crossover
        if prev_bar['EMA9'] <= prev_bar['EMA21'] and bar['EMA9'] > bar['EMA21']:
            entries['EMA_CROSSOVER'].append({'idx': i, 'side': 'CE', 'entry': c})
        if prev_bar['EMA9'] >= prev_bar['EMA21'] and bar['EMA9'] < bar['EMA21']:
            entries['EMA_CROSSOVER'].append({'idx': i, 'side': 'PE', 'entry': c})
            
        # 6. VWAP Bounce
        vwap = bar['VWAP']
        # Touch VWAP and bounce up
        if l <= vwap and c > vwap and o > vwap:
            entries['VWAP_BOUNCE'].append({'idx': i, 'side': 'CE', 'entry': c})
        if h >= vwap and c < vwap and o < vwap:
            entries['VWAP_BOUNCE'].append({'idx': i, 'side': 'PE', 'entry': c})
            
        # 7. Breakout Retest
        # Approximation: Close is near Highest20 broken earlier
        if abs(c - h20)/c < 0.002 and prev_bar['High'] > h20 and c > o:
            entries['BREAKOUT_RETEST'].append({'idx': i, 'side': 'CE', 'entry': c})
        if abs(c - l20)/c < 0.002 and prev_bar['Low'] < l20 and c < o:
            entries['BREAKOUT_RETEST'].append({'idx': i, 'side': 'PE', 'entry': c})

    return entries

def simulate_combo(df, signals, sl_type, tp_type):
    trades = []
    active = None
    
    for i in range(21, len(df)):
        t_idx = df.index[i]
        curr_time = t_idx.time()
        bar = df.iloc[i]
        
        # Check Exits
        if active:
            exit_px = None
            exit_rsn = None
            side = active['side']
            
            # SL Checks
            sl = active['sl']
            if side == 'CE' and bar['Low'] <= sl: exit_px, exit_rsn = sl, "SL"
            elif side == 'PE' and bar['High'] >= sl: exit_px, exit_rsn = sl, "SL"
            
            # TP Checks
            if not exit_px:
                if side == 'CE':
                    if tp_type in ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR'] and bar['High'] >= active['tp']:
                        exit_px, exit_rsn = active['tp'], "TP"
                    elif 'PARTIAL' in tp_type:
                        if not active['part_booked'] and bar['High'] >= active['t1']:
                            active['part_booked'] = True
                            active['sl'] = active['entry']
                        if active['part_booked']:
                            r_reach = (bar['High'] - active['entry'])/active['dist']
                            steps = int((r_reach - active['t1_r'])/0.5)
                            if steps > 0:
                                n_sl = active['entry'] + (active['t1_r'] - 0.5 + steps*0.5) * active['dist']
                                active['sl'] = max(active['sl'], n_sl)
                    elif tp_type == 'TP_TRAIL_ATR':
                        n_sl = bar['Close'] - 1.5*bar['ATR']
                        active['sl'] = max(active['sl'], n_sl)
                        
                else: # PE
                    if tp_type in ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR'] and bar['Low'] <= active['tp']:
                        exit_px, exit_rsn = active['tp'], "TP"
                    elif 'PARTIAL' in tp_type:
                        if not active['part_booked'] and bar['Low'] <= active['t1']:
                            active['part_booked'] = True
                            active['sl'] = active['entry']
                        if active['part_booked']:
                            r_reach = (active['entry'] - bar['Low'])/active['dist']
                            steps = int((r_reach - active['t1_r'])/0.5)
                            if steps > 0:
                                n_sl = active['entry'] - (active['t1_r'] - 0.5 + steps*0.5) * active['dist']
                                active['sl'] = min(active['sl'], n_sl)
                    elif tp_type == 'TP_TRAIL_ATR':
                        n_sl = bar['Close'] + 1.5*bar['ATR']
                        active['sl'] = min(active['sl'], n_sl)

            # EMA SL Check
            if not exit_px:
                if sl_type == 'SL_EMA20':
                    if side == 'CE' and bar['Close'] < bar['EMA20']: exit_px, exit_rsn = bar['Close'], "SL_EMA"
                    elif side == 'PE' and bar['Close'] > bar['EMA20']: exit_px, exit_rsn = bar['Close'], "SL_EMA"
                elif sl_type == 'SL_EMA50':
                    if side == 'CE' and bar['Close'] < bar['EMA50']: exit_px, exit_rsn = bar['Close'], "SL_EMA"
                    elif side == 'PE' and bar['Close'] > bar['EMA50']: exit_px, exit_rsn = bar['Close'], "SL_EMA"

            if not exit_px and curr_time >= time(15, 15):
                exit_px, exit_rsn = bar['Close'], "EOD"
                
            if exit_px:
                if 'PARTIAL' in tp_type and active['part_booked']:
                    p1 = (active['t1'] - active['entry']) * (active['qty']/2)
                    p2 = (exit_px - active['entry']) * (active['qty']/2)
                    pnl = (p1 + p2) if side == 'CE' else -(p1 + p2)
                else:
                    pnl = (exit_px - active['entry']) * active['qty']
                    if side == 'PE': pnl = -pnl
                    
                trades.append({
                    'Date': t_idx.date(), 'Direction': side, 'Entry_Price': active['entry'],
                    'Exit_Price': exit_px, 'Exit_Reason': exit_rsn, 'Gross_PnL': pnl,
                    'Net_PnL': pnl - BROKERAGE
                })
                active = None

        # Check Entries
        if not active and time(9, 45) <= curr_time <= time(13, 30):
            # Check if any signal corresponds to current index `i-1` or `i`
            # Since signals are registered at `idx`, and we process `idx` sequentially
            sigs = [s for s in signals if s['idx'] == i]
            if sigs:
                s = sigs[0] # Take first
                side, entry = s['side'], s['entry']
                
                # Calc SL
                sl = None
                if sl_type == 'SL_EMA20': sl = bar['EMA20']
                elif sl_type == 'SL_EMA50': sl = bar['EMA50']
                elif sl_type == 'SL_ATR_1': sl = entry - 1.0*bar['ATR'] if side == 'CE' else entry + 1.0*bar['ATR']
                elif sl_type == 'SL_ATR_2': sl = entry - 2.0*bar['ATR'] if side == 'CE' else entry + 2.0*bar['ATR']
                elif sl_type == 'SL_CANDLE': sl = bar['Low'] if side == 'CE' else bar['High']
                elif sl_type == 'SL_SWING': sl = bar['SwingL'] if side == 'CE' else bar['SwingH']
                elif sl_type == 'SL_FIXED_1PCT': sl = entry*0.99 if side == 'CE' else entry*1.01
                
                if sl is None or pd.isna(sl): continue
                
                # Enforce min sl distance
                dist = abs(entry - sl)
                if dist < 0.0001*entry: dist = 0.001*entry
                if side == 'CE' and sl >= entry: sl = entry - dist
                if side == 'PE' and sl <= entry: sl = entry + dist
                
                qty = int(RISK_AMOUNT / dist)
                max_q = int(MAX_POS_VALUE / entry)
                qty = min(qty, max_q)
                if qty <= 0: continue
                
                # Calc TP
                tp = None
                t1, t1_r = None, None
                if tp_type == 'TP_FIX_1_5R': tp = entry + 1.5*dist if side == 'CE' else entry - 1.5*dist
                elif tp_type == 'TP_FIX_2R': tp = entry + 2.0*dist if side == 'CE' else entry - 2.0*dist
                elif tp_type == 'TP_FIB': tp = entry + 1.618*dist if side == 'CE' else entry - 1.618*dist
                elif tp_type == 'TP_SR': tp = bar['Highest20'] if side == 'CE' else bar['Lowest20']
                elif tp_type == 'TP_PARTIAL_1R':
                    t1_r = 1.0
                    t1 = entry + 1.0*dist if side == 'CE' else entry - 1.0*dist
                elif tp_type == 'TP_PARTIAL_1_5R':
                    t1_r = 1.5
                    t1 = entry + 1.5*dist if side == 'CE' else entry - 1.5*dist
                elif tp_type == 'TP_TRAIL_ATR':
                    pass # Handled in exit logic
                
                active = {
                    'side': side, 'entry': entry, 'sl': sl, 'qty': qty, 'dist': dist,
                    'tp': tp, 't1': t1, 't1_r': t1_r, 'part_booked': False
                }
                
    return trades

def process_stock(args):
    symbol, test_days = args
    df = load_and_prep(symbol)
    if df is None: return []
    
    # Filter to test days
    df = df[np.isin(df.index.date, test_days)]
    if df.empty: return []
    
    signals = detect_entries(df)
    
    sl_types = ['SL_EMA20', 'SL_EMA50', 'SL_ATR_1', 'SL_ATR_2', 'SL_CANDLE', 'SL_SWING', 'SL_FIXED_1PCT']
    tp_types = ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR', 'TP_PARTIAL_1R', 'TP_PARTIAL_1_5R', 'TP_TRAIL_ATR']
    
    res = []
    for en_name, sigs in signals.items():
        if not sigs: continue
        for sl in sl_types:
            for tp in tp_types:
                trades = simulate_combo(df, sigs, sl, tp)
                for t in trades:
                    t.update({'Combo_ID': f"{en_name}|{sl}|{tp}", 'Entry_Strategy': en_name, 'SL': sl, 'TP': tp, 'Stock': symbol})
                    res.append(t)
    return res

if __name__ == '__main__':
    # 1. Get dates
    ref_df = load_and_prep('RELIANCE')
    all_dates = sorted(list(set(ref_df.index.date)))
    valid_dates = [d for d in all_dates if not is_excluded(d)]
    
    # EXCLUDE PREVIOUS DATES (Set 1 & Set 2)
    prev_dates = [
        '2025-10-29', '2025-11-06', '2025-11-07', '2025-11-10', '2025-11-18', '2025-11-19', '2025-11-21', '2026-03-23', '2026-03-27', '2026-04-06',
        '2025-11-11', '2025-11-14', '2025-11-24', '2025-11-25', '2025-11-27', '2025-11-28', '2025-12-15', '2026-03-10', '2026-03-11', '2026-04-07'
    ]
    valid_dates = [d for d in valid_dates if str(d) not in prev_dates]

    random.seed(777) # New seed
    test_days = sorted(random.sample(valid_dates, 10))
    print(f"✅ Selected 10 Fresh Dates (SET 3): {[str(d) for d in test_days]}")
    
    # 2. Process all stocks
    pool_args = [(s, test_days) for s in SYMBOLS]
    print("🚀 Simulating 343 combinations (SET 3)...")
    
    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.map(process_stock, pool_args)
    
    all_trades = [t for sublist in results for t in sublist]
    df_trades = pd.DataFrame(all_trades)
    
    if df_trades.empty:
        print("❌ No trades generated.")
        exit()
        
    print(f"🎯 Simulation complete! Total trades processed: {len(df_trades):,}")
    
    # Group by Combo
    combo_stats = df_trades.groupby(['Combo_ID', 'Entry_Strategy', 'SL', 'TP'])['Net_PnL'].agg(
        Total_Trades='count',
        Wins=lambda x: (x > 0).sum(),
        Total_PnL_INR='sum'
    ).reset_index()
    
    combo_stats['Win_Rate%'] = (combo_stats['Wins'] / combo_stats['Total_Trades'] * 100).round(1)
    combo_stats['Avg_PnL_Per_Trade'] = (combo_stats['Total_PnL_INR'] / combo_stats['Total_Trades']).round(2)
    
    best_stocks = df_trades.loc[df_trades.groupby('Combo_ID')['Net_PnL'].idxmax()][['Combo_ID', 'Stock']].set_index('Combo_ID')
    worst_stocks = df_trades.loc[df_trades.groupby('Combo_ID')['Net_PnL'].idxmin()][['Combo_ID', 'Stock']].set_index('Combo_ID')
    
    combo_stats = combo_stats.join(best_stocks, on='Combo_ID', rsuffix='_best').rename(columns={'Stock': 'Best_Stock'})
    combo_stats = combo_stats.join(worst_stocks, on='Combo_ID', rsuffix='_worst').rename(columns={'Stock': 'Worst_Stock'})
    
    combo_stats = combo_stats.sort_values('Total_PnL_INR', ascending=False)
    combo_stats['Rank'] = range(1, len(combo_stats) + 1)
    
    print("\n🏆 TOP 10 COMBINATIONS OVERALL (SET 3)")
    print(combo_stats[['Rank', 'Entry_Strategy', 'SL', 'TP', 'Win_Rate%', 'Total_PnL_INR']].head(10).to_string(index=False))
    
    # Save to Excel
    with pd.ExcelWriter("Set3_Comprehensive_Backtest_Results.xlsx") as writer:
        combo_stats.to_excel(writer, sheet_name="All_Results", index=False)
        top_20_ids = combo_stats['Combo_ID'].head(20).tolist()
        df_trades[df_trades['Combo_ID'].isin(top_20_ids)].to_excel(writer, sheet_name="Top_20_Detail", index=False)
        entry_summary = df_trades.groupby('Entry_Strategy').agg({'Net_PnL': 'sum', 'Combo_ID': 'count'}).rename(columns={'Combo_ID': 'Total_Trades'})
        entry_summary.to_excel(writer, sheet_name="Entry_Strategy_Summary")
        stock_summary = df_trades.groupby('Stock').agg({'Net_PnL': 'sum', 'Combo_ID': 'count'}).rename(columns={'Combo_ID': 'Total_Trades'})
        stock_summary.to_excel(writer, sheet_name="Stock_Performance")
        pd.DataFrame({'Field': ['Dates', 'Stocks', 'Total Combos', 'Total Trades'], 'Value': [str(test_days), str(SYMBOLS), 343, len(df_trades)]}).to_excel(writer, sheet_name="Metadata", index=False)
        
    print("\n💾 Saved Set 3 results to Set3_Comprehensive_Backtest_Results.xlsx")
