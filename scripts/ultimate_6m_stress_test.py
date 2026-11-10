import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
import multiprocessing as mp
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
STARTING_CAPITAL = 100000.0
RISK_PCT = 0.01
RISK_AMOUNT = STARTING_CAPITAL * RISK_PCT
BROKERAGE = 87.0
LEVERAGE_CAP = 5.0
MAX_POS_VALUE = STARTING_CAPITAL * LEVERAGE_CAP

NIFTY50 = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'TCS', 'INFY', 'SBIN', 'BHARTIARTL', 'LT', 'KOTAKBANK', 'TITAN']
MIDCAP = ['ADANIENT', 'TATAPOWER', 'ZOMATO', 'IRCTC', 'POLYCAB']
SYMBOLS = NIFTY50 + MIDCAP

def calculate_vwap(df):
    v = df['Volume']
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * v).groupby(df.index.date).cumsum() / v.groupby(df.index.date).cumsum().replace(0, 1)

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
    
    high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    df_5m['ATR'] = tr.rolling(14).mean()
    df_5m['ATR_Avg'] = df_5m['ATR'].rolling(20).mean()
    
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['Highest20'] = df_5m['High'].rolling(20).max().shift(1)
    df_5m['Lowest20'] = df_5m['Low'].rolling(20).min().shift(1)
    df_5m['SwingH'] = df_5m['High'].rolling(5).max().shift(1)
    df_5m['SwingL'] = df_5m['Low'].rolling(5).min().shift(1)
    df_5m['Vol_Avg'] = df_5m['Volume'].rolling(20).mean()
    
    daily_df = df_5m.resample('D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    daily_df['Prev_Close'] = daily_df['Close'].shift(1)
    daily_df['Overnight_Gap_Pct'] = ((daily_df['Open'] - daily_df['Prev_Close']) / daily_df['Prev_Close'] * 100).abs()
    daily_df['Intraday_Drop_Pct'] = ((daily_df['High'] - daily_df['Low']) / daily_df['High'] * 100)
    
    return df_5m.dropna(), daily_df.dropna()

def tag_and_assign_exits(bar, prev_bar):
    c, o, h, l = bar['Close'], bar['Open'], bar['High'], bar['Low']
    vwap = bar['VWAP']
    
    side = None
    if l <= vwap and c > vwap and o >= vwap: side = 'CE'
    elif h >= vwap and c < vwap and o <= vwap: side = 'PE'
    if not side: return None
    
    ema50, ema50_prev = bar['EMA50'], prev_bar['EMA50']
    trend = "RANGING"
    if c > ema50 * 1.005 and ema50 > ema50_prev: trend = "TRENDING_UP"
    elif c < ema50 * 0.995 and ema50 < ema50_prev: trend = "TRENDING_DOWN"
    
    b_type = "VWAP_PULL" if side == 'CE' else "VWAP_PUSH"
    if abs(l - bar['Lowest20']) < (bar['ATR']*0.5): b_type = "SUPPORT_BOUNCE"
    if abs(c - bar['EMA20']) < (bar['ATR']*0.2): b_type = "EMA_BOUNCE"
    
    vol_regime = "NORMAL_VOL"
    if bar['ATR'] < 0.7 * bar['ATR_Avg']: vol_regime = "LOW_VOL"
    elif bar['ATR'] > 1.3 * bar['ATR_Avg']: vol_regime = "HIGH_VOL"
    
    if trend == "RANGING" or vol_regime == "HIGH_VOL" or b_type in ["VWAP_PUSH", "EMA_BOUNCE"]:
        return None
    
    # NEW FILTER: Counter-trend support bounces in downtrend are high-risk
    if trend == "TRENDING_DOWN" and b_type == "SUPPORT_BOUNCE":
        return None
        
    sl_type, tp_type = 'SL_ATR_1', 'TP_TRAIL_ATR'
    if trend == "TRENDING_UP": sl_type, tp_type = 'SL_EMA20', 'TP_FIX_2R'
    elif trend == "TRENDING_DOWN": sl_type, tp_type = 'SL_ATR_1', 'TP_TRAIL_ATR'
    elif b_type == "SUPPORT_BOUNCE": sl_type, tp_type = 'SL_ATR_2', 'TP_PARTIAL_1R'
    elif vol_regime == "LOW_VOL" or b_type == "VWAP_PULL": sl_type, tp_type = 'SL_ATR_1', 'TP_TRAIL_ATR'
        
    return {'side': side, 'entry': c, 'trend': trend, 'b_type': b_type, 'vol_regime': vol_regime, 'sl_type': sl_type, 'tp_type': tp_type}

def simulate_raw_trades(df, symbol):
    trades = []
    for i in range(21, len(df)-1):
        t_idx = df.index[i]
        curr_time = t_idx.time()
        
        if not (time(9, 45) <= curr_time <= time(13, 30)): continue
        
        bar = df.iloc[i]
        tag = tag_and_assign_exits(bar, df.iloc[i-1])
        if not tag: continue
        
        side, entry, sl_type, tp_type = tag['side'], tag['entry'], tag['sl_type'], tag['tp_type']
        
        sl = None
        if sl_type == 'SL_EMA20': sl = bar['EMA20']
        elif sl_type == 'SL_EMA50': sl = bar['EMA50']
        elif sl_type == 'SL_ATR_1': sl = entry - 1.0*bar['ATR'] if side == 'CE' else entry + 1.0*bar['ATR']
        elif sl_type == 'SL_ATR_2': sl = entry - 2.0*bar['ATR'] if side == 'CE' else entry + 2.0*bar['ATR']
        elif sl_type == 'SL_CANDLE': sl = bar['Low'] if side == 'CE' else bar['High']
        elif sl_type == 'SL_SWING': sl = bar['SwingL'] if side == 'CE' else bar['SwingH']
        elif sl_type == 'SL_FIXED_1PCT': sl = entry*0.99 if side == 'CE' else entry*1.01
        
        if sl is None or pd.isna(sl): continue
        dist = abs(entry - sl)
        if dist < 0.001*entry: dist = 0.001*entry
        
        qty = int(RISK_AMOUNT / dist)
        if qty <= 0: continue
        
        active = {'side': side, 'entry': entry, 'qty': qty, 'sl': sl, 'dist': dist, 'part_booked': False, 't1': None, 't1_r': None, 'tp': None}
        
        if tp_type in ['TP_FIX_1_5R', 'TP_FIX_2R', 'TP_FIB', 'TP_SR']:
            r = 1.5 if '1_5' in tp_type else (2.0 if '2R' in tp_type else 1.618)
            active['tp'] = entry + r*dist if side == 'CE' else entry - r*dist
            if tp_type == 'TP_SR': active['tp'] = bar['Highest20'] if side == 'CE' else bar['Lowest20']
        elif 'PARTIAL' in tp_type:
            active['t1_r'] = 1.0 if '1R' in tp_type else 1.5
            active['t1'] = entry + active['t1_r']*dist if side == 'CE' else entry - active['t1_r']*dist
            
        start_pos = i + 1
        exit_px, exit_rsn, exit_time = None, None, None
        
        for j in range(start_pos, len(df)):
            eb = df.iloc[j]
            eb_time = eb.name.time()
            
            if side == 'CE' and eb['Low'] <= active['sl']: exit_px, exit_rsn = active['sl'], "SL"
            elif side == 'PE' and eb['High'] >= active['sl']: exit_px, exit_rsn = active['sl'], "SL"
            
            if not exit_px:
                if side == 'CE':
                    if active['tp'] and eb['High'] >= active['tp']: exit_px, exit_rsn = active['tp'], "TP"
                    elif active['t1']:
                        if not active['part_booked'] and eb['High'] >= active['t1']:
                            active['part_booked'], active['sl'] = True, active['entry']
                        if active['part_booked']:
                            r_reach = (eb['High'] - active['entry'])/active['dist']
                            steps = int((r_reach - active['t1_r'])/0.5)
                            if steps > 0: active['sl'] = max(active['sl'], active['entry'] + (active['t1_r'] - 0.5 + steps*0.5)*active['dist'])
                    elif tp_type == 'TP_TRAIL_ATR':
                        active['sl'] = max(active['sl'], eb['Close'] - 1.5*eb['ATR'])
                else: 
                    if active['tp'] and eb['Low'] <= active['tp']: exit_px, exit_rsn = active['tp'], "TP"
                    elif active['t1']:
                        if not active['part_booked'] and eb['Low'] <= active['t1']:
                            active['part_booked'], active['sl'] = True, active['entry']
                        if active['part_booked']:
                            r_reach = (active['entry'] - eb['Low'])/active['dist']
                            steps = int((r_reach - active['t1_r'])/0.5)
                            if steps > 0: active['sl'] = min(active['sl'], active['entry'] - (active['t1_r'] - 0.5 + steps*0.5)*active['dist'])
                    elif tp_type == 'TP_TRAIL_ATR':
                        active['sl'] = min(active['sl'], eb['Close'] + 1.5*eb['ATR'])
            
            if not exit_px and sl_type == 'SL_EMA20':
                if (side == 'CE' and eb['Close'] < eb['EMA20']) or (side == 'PE' and eb['Close'] > eb['EMA20']): exit_px, exit_rsn = eb['Close'], "SL_EMA"
            
            if not exit_px and eb_time >= time(15, 15): exit_px, exit_rsn = eb['Close'], "EOD"
            
            if exit_px:
                exit_time = eb.name
                pnl = (exit_px - active['entry']) * active['qty'] if side == 'CE' else (active['entry'] - exit_px) * active['qty']
                if active['t1'] and active['part_booked']:
                    p1 = abs(active['t1'] - active['entry']) * (active['qty']/2)
                    p2 = (exit_px - active['entry']) * (active['qty']/2) if side == 'CE' else (active['entry'] - exit_px) * (active['qty']/2)
                    pnl = p1 + p2
                
                regime_flipped = (bar['EMA50'] > bar['Close'] and eb['EMA50'] < eb['Close']) or (bar['EMA50'] < bar['Close'] and eb['EMA50'] > eb['Close'])
                trades.append({
                    'Stock': symbol, 'Entry_Time': t_idx, 'Exit_Time': exit_time, 'Direction': side,
                    'Entry_Price': entry, 'Exit_Price': exit_px, 'Qty': qty, 'Gross_PnL': pnl,
                    'Context': f"{tag['trend']}+{tag['b_type']}", 'SL_Type': sl_type, 'TP_Type': tp_type,
                    'Reason': exit_rsn, 'Regime_Flipped': regime_flipped, 'Vol_Avg': bar['Vol_Avg']
                })
                break
    return trades

def worker(symbol):
    data = load_and_prep(symbol)
    if data is None: return [], pd.DataFrame()
    df_5m, daily_df = data
    daily_df['Stock'] = symbol
    trades = simulate_raw_trades(df_5m, symbol)
    return trades, daily_df

if __name__ == '__main__':
    print("🚀 Running Ultimate 6-Month Backtest...")
    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.map(worker, SYMBOLS)
    
    all_trades, daily_dfs = [], []
    for t, d in results:
        all_trades.extend(t); daily_dfs.append(d)
        
    df_raw = pd.DataFrame(all_trades)
    df_daily = pd.concat(daily_dfs)
    
    if df_raw.empty:
        print("❌ No trades generated.")
        exit()

    print("🛡️ Applying Portfolio Risk Manager...")
    df_raw.sort_values('Entry_Time', inplace=True)
    
    capital = STARTING_CAPITAL
    equity_curve, accepted_trades = [], []
    current_day = None
    daily_trades_count, daily_loss_streak, daily_pnl = 0, 0, 0.0
    current_week, weekly_pnl = None, 0.0
    circuit_breakers_daily, circuit_breakers_weekly = 0, 0
    
    for _, t in df_raw.iterrows():
        t_date, t_week = t['Entry_Time'].date(), t['Entry_Time'].isocalendar()[1]
        if t_date != current_day:
            if current_day is not None: equity_curve.append({'Date': current_day, 'Capital': capital, 'Daily_PnL': daily_pnl})
            current_day, daily_trades_count, daily_loss_count, daily_pnl = t_date, 0, 0, 0.0
        if t_week != current_week:
            current_week, weekly_pnl = t_week, 0.0
            
        # TIGHTER LIMITS: 3 trades max, 1 loss stop
        if daily_trades_count >= 3 or daily_loss_count >= 1: continue
        if daily_pnl <= -0.02 * STARTING_CAPITAL: # Tighter daily breaker
            circuit_breakers_daily += 1; continue
        if weekly_pnl <= -0.06 * STARTING_CAPITAL:
            circuit_breakers_weekly += 1; continue
            
        net_pnl = t['Gross_PnL'] - BROKERAGE
        t['Net_PnL'] = net_pnl
        accepted_trades.append(t.to_dict())
        
        daily_trades_count += 1; daily_pnl += net_pnl; weekly_pnl += net_pnl; capital += net_pnl
        if net_pnl < 0: daily_loss_count += 1
        
    if current_day is not None: equity_curve.append({'Date': current_day, 'Capital': capital, 'Daily_PnL': daily_pnl})
    df_trades = pd.DataFrame(accepted_trades)
    df_eq = pd.DataFrame(equity_curve)
    
    # METRICS
    df_trades['Month'] = df_trades['Entry_Time'].dt.to_period('M')
    
    def count_wins(x): return (x > 0).sum()
    
    m_table = df_trades.groupby('Month').agg({
        'Net_PnL': ['count', count_wins, 'sum'],
        'Gross_PnL': 'sum'
    })
    m_table.columns = ['Trades', 'Wins', 'Net_PnL', 'Gross_PnL']
    m_table['Win_Rate'] = (m_table['Wins'] / m_table['Trades']).round(2)
    m_table['Costs'] = m_table['Gross_PnL'] - m_table['Net_PnL']
    
    total_return = ((capital - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    df_eq['Peak'] = df_eq['Capital'].cummax()
    df_eq['Drawdown'] = (df_eq['Capital'] - df_eq['Peak']) / df_eq['Peak'] * 100
    max_dd = df_eq['Drawdown'].min()
    
    wins = df_trades[df_trades['Net_PnL'] > 0]
    losses = df_trades[df_trades['Net_PnL'] <= 0]
    pf = abs(wins['Net_PnL'].sum() / losses['Net_PnL'].sum()) if len(losses) > 0 and losses['Net_PnL'].sum() != 0 else float('inf')
    
    max_gap = df_daily[df_daily['Overnight_Gap_Pct'] > 2.0]['Overnight_Gap_Pct'].max() if not df_daily[df_daily['Overnight_Gap_Pct'] > 2.0].empty else 0
    max_drop = df_daily['Intraday_Drop_Pct'].max()
    regime_flips = df_trades[df_trades['Regime_Flipped'] == True]
    rf_pnl = regime_flips['Net_PnL'].sum() if not regime_flips.empty else 0
    
    df_eq['Loss_Streak'] = (df_eq['Daily_PnL'] < 0).astype(int).groupby((df_eq['Daily_PnL'] >= 0).cumsum()).cumsum()
    max_losing_streak_days = df_eq['Loss_Streak'].max()
    
    df_eq['Days_Diff'] = pd.to_datetime(df_eq['Date']).diff().dt.days
    max_idle_days = df_eq[df_eq['Daily_PnL'] == 0]['Days_Diff'].max() if not df_eq[df_eq['Daily_PnL'] == 0].empty else 0
    
    net_120 = df_trades['Gross_PnL'].sum() - (120 * len(df_trades))
    net_150 = df_trades['Gross_PnL'].sum() - (150 * len(df_trades))
    df_trades['Max_Liq_Qty'] = (df_trades['Vol_Avg'] * 0.05).astype(int)
    liq_breaches = len(df_trades[df_trades['Qty'] > df_trades['Max_Liq_Qty']])
    
    risk_metrics = pd.DataFrame({'Metric': ['Starting Capital', 'Final Capital', 'Total Return %', 'Max Drawdown %', 'Total Trades', 'Win Rate %', 'Profit Factor', 'Avg Net PnL', 'Circuit Breakers (Daily)'], 'Value': [STARTING_CAPITAL, capital, total_return, max_dd, len(df_trades), (len(wins)/len(df_trades)*100) if len(df_trades)>0 else 0, pf, df_trades['Net_PnL'].mean(), circuit_breakers_daily]})
    
    def win_rate_mean(x): return (x > 0).mean()
    context_breakdown = df_trades.groupby('Context').agg({'Net_PnL': ['count', win_rate_mean, 'sum']})
    context_breakdown.columns = ['Trades', 'WinRate', 'Net_PnL']
    context_breakdown = context_breakdown.reset_index()
    
    stock_perf = df_trades.groupby('Stock').agg({'Net_PnL': ['count', 'sum']})
    stock_perf.columns = ['Trades', 'Net_PnL']
    stock_perf = stock_perf.reset_index()
    
    destruct_df = pd.DataFrame({'Scenario': ['SUDDEN GAP (>2%)', 'INTRADAY CRASH', 'LOSING STREAK DAYS', 'REGIME FLIP (Mid-Trade)', 'COST @ 120', 'COST @ 150', 'LIQUIDITY BREACHES (5x Cap)'], 'Impact/Result': [f"Max Gap: {max_gap:.1f}%. Overnight risk isolated by 15:15 exit.", f"Max Intraday Drop: {max_drop:.1f}%. Daily CB protects portfolio.", f"Max consecutive losing days: {max_losing_streak_days}", f"{len(regime_flips)} trades flipped regime. Net PnL: ₹{rf_pnl:.0f}", f"Net PnL would be ₹{net_120:.0f}", f"Net PnL would be ₹{net_150:.0f}", f"{liq_breaches} trades exceeded 5% volume limit"]})
    
    passed = (total_return > 10) and (max_dd > -15) and (pf > 1.3) and ((len(wins)/len(df_trades)) > 0.4) and (net_120 > 0) if len(df_trades)>0 else False
    verdict = pd.DataFrame({'Criteria': ['Final Verdict'], 'Result': ['PASS ✅' if passed else 'FAIL ❌']})
    
    print(f"\n✅ Writing Master Excel Report. Final Return: {total_return:.2f}% | Max DD: {max_dd:.2f}%")
    with pd.ExcelWriter("6_Month_Stress_Test_MASTER.xlsx") as w:
        m_table.to_excel(w, sheet_name="Monthly_Performance")
        risk_metrics.to_excel(w, sheet_name="Risk_Metrics", index=False)
        context_breakdown.to_excel(w, sheet_name="Context_Breakdown", index=False)
        stock_perf.to_excel(w, sheet_name="Stock_Performance", index=False)
        df_eq[['Date', 'Capital', 'Daily_PnL', 'Drawdown']].to_excel(w, sheet_name="Equity_Curve", index=False)
        destruct_df.to_excel(w, sheet_name="Destruction_Tests", index=False)
        df_trades.to_excel(w, sheet_name="Trade_Log", index=False)
        verdict.to_excel(w, sheet_name="Pass_Fail_Verdict", index=False)

    print("💾 Saved to 6_Month_Stress_Test_MASTER.xlsx")
    print(f"\n{verdict.iloc[0]['Result']}")
