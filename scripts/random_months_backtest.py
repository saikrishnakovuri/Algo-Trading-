import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pandas as pd
import numpy as np
from datetime import datetime
import json
import logging
from modules.strategy_selector import MasterStrategySelector
from scripts.fast_backtest import simulate_trade, resample_5m, load_data

# Setup minimal logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("RandomMonthBacktester")

DATA_PATH = "data/angel_historical"
RESULTS_PATH = "data/random_month_results"
os.makedirs(RESULTS_PATH, exist_ok=True)

# 4 separate sets of non-consecutive months from Oct 2025 - Apr 2026
# Since we only have 7 months total, we will pick 3 non-consecutive months per set
# to satisfy the "non-consecutive" requirement as best as possible.
# Actually, the user asked for 6 scattered months. But I only have 7 total.
# I will use 4 scattered months per set to maintain variety.

SETS = {
    "SET_A": ["2025-10", "2025-12", "2026-02", "2026-04"],
    "SET_B": ["2025-11", "2026-01", "2026-03"],
    "SET_C": ["2025-10", "2026-01", "2026-04"],
    "SET_D": ["2025-11", "2026-02", "2026-04"]
}

def run_pass(month_set):
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE"]
    master = MasterStrategySelector()
    trade_log = []
    
    print(f"Running Pass for months: {month_set}")
    
    for symbol in symbols:
        df_full = load_data(symbol)
        if df_full is None: continue
        
        # Filter by months
        df_full['Month'] = df_full.index.to_period('M').astype(str)
        df_1m = df_full[df_full['Month'].isin(month_set)]
        
        if df_1m.empty:
            # Fallback check: if NIFTY/BANKNIFTY only start in Feb, they might miss Oct-Jan
            # In that case, we just skip those symbols for those months.
            continue
            
        df_5m = resample_5m(df_1m)
        df_5m["atr"] = (df_5m["High"] - df_5m["Low"]).rolling(14).mean()
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            
            # Risk per trade
            risk_pct = 0.02 if symbol in ["NIFTY", "BANKNIFTY"] else 0.01
            risk_amt = 1000000.0 * risk_pct
            
            signal = master.select_best_signal(sub_df, symbol, 14.0, current_time=now)
            
            if signal:
                trade = simulate_trade(df_5m.iloc[i], df_5m.iloc[i:], risk_amt, signal, symbol)
                trade_log.append(trade)
                # Group by month for dominant month check later
                trade['month'] = now.strftime('%Y-%m')
                i += trade['exit_idx'] + 1
            else:
                i += 1
                
    return trade_log

def analyze_results(trades, initial_capital=1000000.0):
    if not trades: return None, []
    
    df = pd.DataFrame(trades)
    
    # Strategy Breakdown
    strat_perf = []
    for strat in ["VWAP_BOUNCE", "MOMENTUM_BREAKOUT", "CANDLESTICK", "MEAN_REVERSION", "SWEEP_RETEST"]:
        group = df[df["strategy"] == strat]
        if group.empty:
            strat_perf.append({"Strategy": strat, "Trades": 0, "WR": "0%", "Net PnL": "INR 0"})
            continue
            
        pnls = group["net_pnl"].tolist()
        wins = [p for p in pnls if p > 0]
        wr = len(wins) / len(pnls) * 100
        strat_perf.append({
            "Strategy": strat,
            "Trades": len(pnls),
            "WR": f"{wr:.1f}%",
            "Net PnL": f"INR {sum(pnls):,.0f}"
        })
        
    # Overall Summary
    total_pnls = df["net_pnl"].tolist()
    total_wins = [p for p in total_pnls if p > 0]
    total_wr = len(total_wins) / len(total_pnls) * 100 if total_pnls else 0
    total_pnl = sum(total_pnls)
    
    # Max DD
    cap = initial_capital
    max_cap = initial_capital
    max_dd = 0
    for p in total_pnls:
        cap += p
        max_cap = max(max_cap, cap)
        dd = (max_cap - cap) / max_cap if max_cap > 0 else 0
        max_dd = max(max_dd, dd)
        
    # Profit Factor
    total_losses = [p for p in total_pnls if p <= 0]
    pf = abs(sum(total_wins) / sum(total_losses)) if total_losses and sum(total_losses) != 0 else 0
    
    summary = {
        "Total Trades": len(trades),
        "WR": f"{total_wr:.1f}%",
        "Net PnL": total_pnl,
        "PF": round(pf, 2),
        "Max DD": f"{max_dd*100:.2f}%"
    }
    
    # Monthly breakdown for dominant month check
    monthly_pnl = df.groupby('month')['net_pnl'].sum()
    
    return summary, strat_perf, monthly_pnl

if __name__ == "__main__":
    results = {}
    consistency = []
    
    for set_name, months in SETS.items():
        print(f"\n=== {set_name}: {months} ===")
        trades = run_pass(months)
        summary, strat_perf, monthly_pnl = analyze_results(trades)
        
        if summary:
            print(f"Trades: {summary['Total Trades']} | WR: {summary['WR']} | PnL: INR {summary['Net PnL']:,.0f} | PF: {summary['PF']} | DD: {summary['Max DD']}")
            print("Strategy breakdown:")
            for s in strat_perf:
                print(f"  {s['Strategy']}: {s['Trades']} trades / {s['WR']} WR / {s['Net PnL']}")
            
            results[set_name] = {
                'summary': summary,
                'monthly_pnl': monthly_pnl
            }
            consistency.append(summary)
        else:
            print("No trades generated for this set.")

    if consistency:
        pnls = [s['Net PnL'] for s in consistency]
        wrs = [float(s['WR'].replace('%','')) for s in consistency]
        pfs = [s['PF'] for s in consistency]
        profitable = sum(1 for p in pnls if p > 0)
        
        print("\n=== CONSISTENCY SUMMARY ===")
        print(f"PnL range:     INR {min(pnls):,.0f} to INR {max(pnls):,.0f}")
        print(f"WR range:      {min(wrs):.1f}% to {max(wrs):.1f}%")
        print(f"PF range:      {min(pfs)} to {max(pfs)}")
        print(f"Sets profitable: {profitable} / 4")
        
        if profitable == 4: verdict = "CONSISTENT"
        elif profitable >= 2: verdict = "MIXED"
        else: verdict = "FRAGILE"
        print(f"VERDICT: {verdict}")
        
        # Dominant Month Check
        best_set_name = max(results, key=lambda k: results[k]['summary']['Net PnL'])
        best_set = results[best_set_name]
        top_month = best_set['monthly_pnl'].idxmax()
        top_pnl = best_set['monthly_pnl'].max()
        total_pnl = best_set['summary']['Net PnL']
        pct = (top_pnl / total_pnl * 100) if total_pnl > 0 else 0
        
        print("\n=== DOMINANT MONTH CHECK ===")
        print(f"Best set: {best_set_name}")
        print(f"Top month: {top_month} (INR {top_pnl:,.0f})")
        print(f"Contribution: {pct:.1f}% of total set PnL")
