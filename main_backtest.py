import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import json
import logging
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import TOTAL_CAPITAL, BROKERAGE_EQUITY, BROKERAGE_OPTIONS, NIFTY_LOT_SIZE, BANKNIFTY_LOT_SIZE

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Backtester")

from modules.strategy_mapper import STRATEGY_MAP, MAX_STRATEGIES
from modules.indicator_cache import precompute_indicators

print(f"[20b-VERIFY] LOW_VOL max={MAX_STRATEGIES.get('LOW_VOL','MISSING')}")
print(f"[20b-VERIFY] BREAKOUT_SETUP max={MAX_STRATEGIES.get('BREAKOUT_SETUP','MISSING')}")
print(f"[20b-VERIFY] TRENDING_UP strategies={[s.name for s in STRATEGY_MAP.get('TRENDING_UP',[])]}")

pd.options.mode.chained_assignment = None

DATA_PATH = "data/angel_historical"
RESULTS_PATH = "data/backtest_results"
os.makedirs(RESULTS_PATH, exist_ok=True)

def load_data(symbol: str) -> pd.DataFrame:
    filename = "nifty50_1m.csv" if symbol == "NIFTY" else "banknifty_1m.csv" if symbol == "BANKNIFTY" else f"{symbol}_1m.csv"
    path = f"{DATA_PATH}/{filename}"
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df.set_index("Timestamp", inplace=True)
    return df

def resample_5m(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("5min").agg({
        "Open": "first", "High": "max",
        "Low": "min", "Close": "last", "Volume": "sum"
    }).dropna()

def estimate_premium(spot, strike, dte_days, direction, iv=0.15):
    """Realistic premium proxy for backtest (REQ 25a-6)."""
    intrinsic = max(0, spot - strike) if direction == 'CE' else max(0, strike - spot)
    time_value = spot * iv * (max(0.5, dte_days) / 365) ** 0.5
    return max(intrinsic + time_value, 5.0)

def simulate_trade(entry_bar, df_5m, risk_amt, signal, symbol):
    entry_price = entry_bar["close"]
    is_option = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    
    sl_price = signal.get('sl')
    tp_price = signal.get('tp')
    direction = 'CE' if signal['direction'] in ['CE', 'BUY', 'LONG'] else 'PE'
    
    # REQ 25a-6: Use realistic premium
    entry_premium = estimate_premium(entry_price, entry_price, 4, direction)
    
    if sl_price is None:
        atr = entry_bar.get("atr", entry_price * 0.005)
        sl_dist = 2 * atr
        sl_price = entry_price - sl_dist if direction == 'CE' else entry_price + sl_dist
        
    if tp_price is None:
        sl_dist = abs(entry_price - sl_price)
        tp_price = entry_price + (2.0 * sl_dist) if direction == 'CE' else entry_price - (2.0 * sl_dist)

    sl_dist = abs(entry_price - sl_price)
    
    if is_option:
        lot_size = NIFTY_LOT_SIZE if symbol == "NIFTY" else BANKNIFTY_LOT_SIZE if symbol == "BANKNIFTY" else 40
        # REQ 25a-5: sizing based on premium proxy
        qty_lots = max(1, int(risk_amt / (sl_dist * 0.5 * lot_size)) if sl_dist > 0 else 1)
        qty = qty_lots * lot_size
    else:
        qty = int(risk_amt / sl_dist) if sl_dist > 0 else 1
        qty = max(1, min(qty, 500))
    
    exit_price, exit_reason = entry_price, "EOD"
    exit_idx = 0
    is_long = direction == 'CE'
    
    exit_slice = df_5m.iloc[1:80]
    for i, (idx, bar) in enumerate(exit_slice.iterrows()):
        exit_idx = i + 1
        if is_long:
            if bar["low"] <= sl_price:
                exit_price, exit_reason = sl_price, "SL"
                break
            if bar["high"] >= tp_price:
                exit_price, exit_reason = tp_price, "TP"
                break
        else:
            if bar["high"] >= sl_price:
                exit_price, exit_reason = sl_price, "SL"
                break
            if bar["low"] <= tp_price:
                exit_price, exit_reason = tp_price, "TP"
                break
                
    if exit_reason == "EOD":
        exit_price = exit_slice.iloc[-1]["close"] if not exit_slice.empty else entry_price
        exit_idx = len(exit_slice)
    
    if is_option:
        # REQ 25a-5: Premium-to-premium PnL
        exit_premium = estimate_premium(exit_price, entry_price, 3.5, direction)
        gross_pnl = (exit_premium - entry_premium) * qty
    else:
        if is_long:
            gross_pnl = (exit_price - entry_price) * qty
        else:
            gross_pnl = (entry_price - exit_price) * qty
        
    costs = BROKERAGE_OPTIONS if is_option else BROKERAGE_EQUITY
    net_pnl = gross_pnl - costs
    
    return {
        "timestamp": entry_bar.name.isoformat(),
        "symbol": symbol,
        "strategy": signal['strategy'],
        "direction": signal['direction'],
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2),
        "exit_reason": exit_reason,
        "qty": qty,
        "net_pnl": round(float(net_pnl), 2),
        "regime": signal['context'].regime,
        "exit_idx": exit_idx
    }

from modules.risk_guard import RiskGuard

def run_main_backtest(start_date_str=None, end_date_str=None):
    symbols = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL",
        "BRITANNIA", "CIPLA", "COFORGE", "MPHASIS",
        "PERSISTENT", "POLYCAB", "GODREJPROP", "AUBANK", "CUMMINSIND",
        "MARICO", "INDUSTOWER", "AUROPHARMA", "ASHOKLEY", "HDFCAMC",
        "FEDERALBNK", "LUPIN"
    ]
    
    if start_date_str:
        start_date = pd.Timestamp(start_date_str).tz_localize('Asia/Kolkata')
    else:
        start_date = pd.Timestamp("2025-10-28").tz_localize('Asia/Kolkata')
        
    if end_date_str:
        end_date = pd.Timestamp(end_date_str).tz_localize('Asia/Kolkata')
    else:
        end_date = pd.Timestamp("2026-04-24").tz_localize('Asia/Kolkata')
    
    master = MasterStrategySelector()
    trade_log = []
    
    # Initialize RiskGuard (Phase 21)
    from pathlib import Path
    state_file = Path('data/risk_guard_state.json')
    if state_file.exists(): state_file.unlink()
    guard = RiskGuard(starting_capital=TOTAL_CAPITAL)
    skipped_count = 0
    
    print(f"Running Main Backtest on {len(symbols)} symbols from {start_date.date()} to {end_date.date()}...")
    
    for symbol in symbols:
        df_full = load_data(symbol)
        if df_full is None: continue
        
        df_1m = df_full[(df_full.index >= start_date) & (df_full.index <= end_date)]
        if df_1m.empty: continue
        
        df_5m = resample_5m(df_1m)
        df_5m = precompute_indicators(df_5m)
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            risk_pct = 0.02 if symbol in ["NIFTY", "BANKNIFTY"] else 0.01
            risk_amt = TOTAL_CAPITAL * risk_pct
            
            signal = master.select_best_signal(sub_df, symbol, 15.0, current_time=now)
            
            if signal:
                allowed, reason = guard.can_trade(now=now)
                if allowed:
                    trade = simulate_trade(df_5m.iloc[i], df_5m.iloc[i:], risk_amt, signal, symbol)
                    trade_log.append(trade)
                    # Record trade in guard
                    exit_time = pd.to_datetime(trade['timestamp']) + timedelta(minutes=5 * trade['exit_idx'])
                    guard.record_trade(pnl=trade['net_pnl'], now=exit_time)
                    i += trade['exit_idx'] + 1
                else:
                    skipped_count += 1
                    i += 1
            else:
                i += 1
    
    master.risk_guard_skipped = skipped_count
    return trade_log, master

def analyze_results(trades, initial_capital):
    if not trades: return {}
    df = pd.DataFrame(trades)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["month"] = df["timestamp"].dt.to_period("M")
    monthly = []
    for month, group in df.groupby("month"):
        pnls = group["net_pnl"].tolist()
        wins = [p for p in pnls if p > 0]
        wr = len(wins) / len(pnls) * 100
        total_wins = sum(wins)
        total_losses = abs(sum([p for p in pnls if p <= 0]))
        pf = total_wins / total_losses if total_losses > 0 else 99
        monthly.append({
            "Month": str(month),
            "Trades": len(pnls),
            "WR": f"{wr:.1f}%",
            "Net PnL": f"INR {sum(pnls):,.0f}",
            "PF": round(pf, 2),
            "Regimes": ", ".join(group["regime"].unique())
        })
    strat_perf = []
    for strat, group in df.groupby("strategy"):
        pnls = group["net_pnl"].tolist()
        wins = [p for p in pnls if p > 0]
        wr = len(wins) / len(pnls) * 100
        strat_perf.append({
            "Strategy": strat,
            "Trades": len(pnls),
            "WR": f"{wr:.1f}%",
            "Net PnL": f"INR {sum(pnls):,.0f}"
        })
    total_pnls = df["net_pnl"].tolist()
    total_wins = [p for p in total_pnls if p > 0]
    total_wr = len(total_wins) / len(total_pnls) * 100 if total_pnls else 0
    total_pnl = sum(total_pnls)
    cap = initial_capital
    max_cap = initial_capital
    max_dd = 0
    for p in total_pnls:
        cap += p
        max_cap = max(max_cap, cap)
        dd = (max_cap - cap) / max_cap if max_cap > 0 else 0
        max_dd = max(max_dd, dd)
    total_losses = abs(sum([p for p in total_pnls if p <= 0]))
    pf = sum(total_wins) / total_losses if total_losses > 0 else 99
    summary = {
        "Total Trades": len(trades),
        "WR": f"{total_wr:.1f}%",
        "Net PnL": f"INR {total_pnl:,.0f}",
        "Max DD": f"{max_dd*100:.2f}%",
        "PF": round(pf, 2),
        "Trades/Day": round(len(trades) / 125, 2)
    }
    return summary, monthly, strat_perf

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", type=str)
    parser.add_argument("--end_date", type=str)
    args = parser.parse_args()
    
    trades, master = run_main_backtest(args.start_date, args.end_date)
    if trades:
        print(master.funnel_report())
        summary, monthly, strat_perf = analyze_results(trades, TOTAL_CAPITAL)
        print("\n=== BACKTEST SUMMARY ===")
        for k, v in summary.items(): print(f"{k}: {v}")
        print("\n=== MONTHLY BREAKDOWN ===")
        print(pd.DataFrame(monthly).to_string(index=False))
        print("\n=== STRATEGY PERFORMANCE ===")
        print(pd.DataFrame(strat_perf).to_string(index=False))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"{RESULTS_PATH}/validation_{ts}.json", "w") as f:
            json.dump({"summary": summary, "monthly": monthly, "strategies": strat_perf}, f, indent=4)
        pd.DataFrame(trades).to_csv(f"{RESULTS_PATH}/trades_{ts}.csv", index=False)
        print(f"\nResults saved to {RESULTS_PATH}")
    else:
        print("No trades generated.")
