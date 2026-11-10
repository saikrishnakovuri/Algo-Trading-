import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine
from modules.vix_filter import VIXDirectionalFilter

INITIAL_CAPITAL = 1000000.0
MAX_WORKERS = 8
LOT_SIZE = 65 # Nifty Lot Size
MAX_LOTS = 5
RISK_PER_TRADE_INR = 20000.0 # 2% of 10L
MIDCAP_DATA_DIR = "data/nifty200"
MIDCAP_SYMBOLS = ['ATGL', 'ADANIENSOL', 'TATAINVEST', 'ADANIPOWER', 'ASTRAL', 'SUZLON', 'BHEL', 'RADICO', 'BLUESTARCO', 'ADANIGREEN', 'LODHA', 'COCHINSHIP', 'SIEMENS', 'ADANIENT', 'KALYANKJIL', 'VOLTAS', 'HDFCAMC', 'SAIL', 'BSE', 'JSWENERGY', 'JUBLFOOD', 'RVNL', 'INDIANB', 'MCX', '360ONE', 'COFORGE', 'PRESTIGE', 'NATIONALUM', 'MOTHERSON', 'VBL']

def get_regime_series(start_date, end_date):
    nifty_path = "data/nifty50_5m.csv"
    df_nifty_raw = pd.read_csv(nifty_path)
    df_nifty_raw['Timestamp'] = pd.to_datetime(df_nifty_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_nifty_raw.set_index('Timestamp', inplace=True)
    df_nifty_raw = df_nifty_raw.between_time('09:15', '15:30')
    start_ist = pd.Timestamp(start_date).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_date).tz_localize('Asia/Kolkata')
    df_nifty = df_nifty_raw[(df_nifty_raw.index >= start_ist - timedelta(days=20)) & (df_nifty_raw.index <= end_ist)]
    regime_gate = RegimeGate() # Assume this exists from previous turns
    regime_map = {}
    for i in range(100, len(df_nifty)):
        ts = df_nifty.index[i]
        if ts < start_ist: continue
        regime = regime_gate.update_regime(df_nifty.iloc[max(0, i-150):i+1])
        regime_map[ts] = {'allowed': {s: regime_gate.is_strategy_allowed(s) for s in ['MOMENTUM', 'MEAN_REVERSION']}, 'regime': regime}
    return regime_map

# Mocking RegimeGate since it might not be fully instantiated in this session
class RegimeGate:
    def __init__(self): self.current_regime = "NORMAL"
    def update_regime(self, df): 
        # Simplified: If ATR expansion > 2.0, VOLATILE, else NORMAL
        self.current_regime = "NORMAL"
        return self.current_regime
    def is_strategy_allowed(self, name): return True

def calc_options_costs(qty, entry_p, exit_p):
    brokerage = 40.0
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    return brokerage + stt + exchange + 10.0

def process_symbol(args):
    symbol, start_dt, end_dt, regime_map, vix_df = args
    data_path = os.path.join(MIDCAP_DATA_DIR, f"{symbol}_1m.csv")
    if not os.path.exists(data_path): return []
    
    df_raw = pd.read_csv(data_path)
    df_raw['Datetime'] = pd.to_datetime(df_raw['Datetime'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Datetime', inplace=True)
    df_raw.sort_index(inplace=True)
    df_5m = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df_5m = df_5m.between_time('09:15', '15:30')
    
    ie = IndicatorEngine() # Assume exists
    df_5m['atr'] = ie.calculate_atr(df_5m)
    mom_engine = MomentumBreakoutEngine()
    consolidations = mom_engine.detect_consolidation(df_5m)
    vix_filter = VIXDirectionalFilter(config_path="config/vix_filter.yaml")
    
    trades = []
    start_ist = pd.Timestamp(start_dt).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_dt).tz_localize('Asia/Kolkata')
    entry_gate_time = time(13, 30)
    last_exit_ts = start_ist - timedelta(days=1)
    
    for i in range(50, len(df_5m)):
        ts = df_5m.index[i]
        if ts < start_ist or ts > end_ist: continue
        if ts <= last_exit_ts: continue
        if ts.time() > entry_gate_time: continue

        r_info = regime_map.get(ts, {'regime':'NORMAL'})
        vix_filter.update(vix_df[vix_df.index <= ts].tail(20))
        
        # 75% Confidence Threshold
        min_conf = 75
        
        mom_sig = mom_engine.detect_breakout(df_5m, consolidations, i)
        if mom_sig['signal']:
            conf = min(100, int(mom_sig['score'] * 12))
            rev_dir = 'PE' if mom_sig['direction'] == 'CE' else 'CE'
            adj_conf, allowed, _ = vix_filter.filter_signal(rev_dir, conf)
            
            if allowed and adj_conf >= min_conf:
                entry_spot = df_5m.iloc[i]['Close']
                atr = df_5m.iloc[i]['atr']
                sl_dist = atr * 2.5 # Hourly ATR proxy
                
                # Synthetic Premium
                vix = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
                entry_p = entry_spot * 0.006 * (vix/15.0)
                
                # Position Sizing FIX (Lots)
                lots = max(1, int(RISK_PER_TRADE_INR / (entry_p * LOT_SIZE)))
                lots = min(lots, MAX_LOTS)
                qty = lots * LOT_SIZE
                
                # MINIMUM PROFIT GATE
                projected_profit_at_t1 = qty * (entry_p * 0.5) # T1 = +50% of premium
                estimated_cost = 87
                if projected_profit_at_t1 < (estimated_cost * 2.0):
                    continue
                
                target_p = entry_p * 1.5
                be_trigger_p = entry_p * 1.35 # 0.7R move in underlying ≈ 35% premium move
                sl_p = entry_p * 0.7
                
                exit_p = entry_p; exit_reason = "EOD"
                be_active = False
                for j in range(i+1, min(i+20, len(df_5m))):
                    curr_bar = df_5m.iloc[j]
                    spot_move = (curr_bar['Close'] - entry_spot) / entry_spot
                    if rev_dir == 'PE': spot_move *= -1.0
                    
                    curr_p = entry_p + (0.5 * spot_move * entry_spot) + (0.5 * 0.002 * (spot_move * entry_spot)**2) - (0.5 * (j-i)/12)
                    
                    if not be_active and curr_p >= be_trigger_p:
                        be_active = True
                        sl_p = entry_p
                    
                    if curr_p >= target_p: exit_p = target_p; exit_reason = "TP"; break
                    if curr_p <= sl_p: exit_p = sl_p; exit_reason = "SL"; break
                    
                    struct_hit = (curr_bar['Close'] > mom_sig['entry']) if rev_dir == 'PE' else (curr_bar['Close'] < mom_sig['entry'])
                    if struct_hit: exit_p = curr_p; exit_reason = "STRUCT"; break
                
                if exit_reason == "EOD":
                    exit_p = curr_p; exit_time = ts # Rough estimate
                
                costs = calc_options_costs(qty, entry_p, exit_p)
                net_pnl = ((exit_p - entry_p) * qty) - costs
                
                last_exit_ts = df_5m.index[j]
                trades.append({'ts': ts, 'net': net_pnl, 'costs': costs, 'reason': exit_reason, 'gross': net_pnl + costs})
                
    return trades

def main():
    print("Loading Data...")
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    start_d = datetime(2026, 4, 8); end_d = datetime(2026, 4, 20)
    # Mocking regime map
    regime_map = {ts: {'regime':'NORMAL'} for ts in vix_df.index}
    
    print(f"Running V8 Final Optimization for {len(MIDCAP_SYMBOLS)} stocks...")
    args = [(s, start_d, end_d, regime_map, vix_df) for s in MIDCAP_SYMBOLS]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        results = list(ex.map(process_symbol, args))
    
    all_t = sorted([t for res in results for t in res], key=lambda x: x['ts'])
    
    if not all_t:
        print("No trades found."); return

    df = pd.DataFrame(all_t)
    total_net = df['net'].sum()
    total_costs = df['costs'].sum()
    avg_cost = df['costs'].mean()
    net_per_trade = total_net / len(df)
    
    print(f"\n--- V8 FINAL OPTIMIZATION SUMMARY ---")
    print(f"Total Trades: {len(df)}")
    print(f"Win Rate: {(df['net'] > 0).sum()/len(df)*100:.1f}%")
    print(f"Total Gross P&L: INR {df['gross'].sum():,.2f}")
    print(f"Total Costs (Taxes): INR {total_costs:,.2f}")
    print(f"**Final Net P&L**: **INR {total_net:,.2f}**")
    print(f"Net Profit per Trade: INR {net_per_trade:.2f}")
    print(f"Avg Cost per Trade: INR {avg_cost:.2f}")
    
    print("\nExit Reason Breakdown:")
    print(df['reason'].value_counts())
    
    print("\nDaily Equity Curve:")
    df['date'] = df['ts'].dt.date
    daily = df.groupby('date')['net'].sum()
    eq = INITIAL_CAPITAL
    max_dd = 0
    peak = INITIAL_CAPITAL
    for d, pnl in daily.items():
        eq += pnl
        if eq > peak: peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd: max_dd = dd
        print(f"{d} | PnL: {pnl:>10,.2f} | Eq: {eq:>12,.2f} | DD: {dd:>5.1f}%")
    
    print(f"\nMax Daily Drawdown: {max_dd:.2f}%")
    print(f"Final Status: {'PASS - DEPLOY READY' if (total_net > 0 and max_dd < 3.0 and net_per_trade > 50) else 'FAIL - NEEDS TWEAKING'}")

if __name__ == "__main__":
    main()
