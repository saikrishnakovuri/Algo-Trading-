import sys, os
# Add parent directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import TOTAL_CAPITAL, BROKERAGE_EQUITY

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Comparator")

DATA_PATH = "data/angel_historical"

def load_data(symbol: str) -> pd.DataFrame:
    filename = "nifty50_1m.csv" if symbol == "NIFTY" else "banknifty_1m.csv"
    path = f"{DATA_PATH}/{filename}"
    if not os.path.exists(path):
        raise FileNotFoundError(f"No data for {symbol}: {path}")
    df = pd.read_csv(path)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    df.set_index("Timestamp", inplace=True)
    return df

def resample_5m(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("5min").agg({
        "Open": "first", "High": "max",
        "Low": "min", "Close": "last", "Volume": "sum"
    }).dropna()

def simulate_trade(entry_bar, df_5m, risk_amt, direction):
    entry_price = entry_bar["Close"]
    atr = entry_bar.get("atr", entry_price * 0.005)
    sl_dist = 2 * atr # Default ATR_2
    
    # Standardize direction
    is_long = direction in ["CE", "BUY", "LONG"]
    
    if is_long:
        sl_price = entry_price - sl_dist
        tp_price = entry_price + (2.0 * sl_dist)
    else:
        sl_price = entry_price + sl_dist
        tp_price = entry_price - (2.0 * sl_dist)
    
    qty = int(risk_amt / sl_dist) if sl_dist > 0 else 1
    qty = max(1, min(qty, 500))
    
    exit_price, exit_reason = entry_price, "EOD"
    
    for i, (idx, bar) in enumerate(df_5m.iterrows()):
        if i == 0: continue
        
        if is_long:
            if bar["Low"] <= sl_price:
                exit_price, exit_reason = sl_price, "SL"
                break
            if bar["High"] >= tp_price:
                exit_price, exit_reason = tp_price, "TP"
                break
        else:
            if bar["High"] >= sl_price:
                exit_price, exit_reason = sl_price, "SL"
                break
            if bar["Low"] <= tp_price:
                exit_price, exit_reason = tp_price, "TP"
                break
                
        if i > 78:
            exit_price, exit_reason = bar["Close"], "TIME"
            break
    
    if is_long:
        gross_pnl = (exit_price - entry_price) * qty
    else:
        gross_pnl = (entry_price - exit_price) * qty
        
    net_pnl = gross_pnl - BROKERAGE_EQUITY
    return net_pnl

def run_backtest(config_type, start_date, end_date):
    stocks = ["NIFTY", "BANKNIFTY"]
    capital = 1000000.0
    risk_pct = 0.01
    risk_amt = capital * risk_pct
    
    all_pnls = []
    
    if config_type == "OLD":
        adapter = IndexLiquidityTrapAdapter()
    else:
        master = MasterStrategySelector()
        
    for symbol in stocks:
        df_1m = load_data(symbol)
        df_1m = df_1m[(df_1m.index >= start_date) & (df_1m.index <= end_date)]
        df_5m = resample_5m(df_1m)
        df_5m["atr"] = (df_5m["High"] - df_5m["Low"]).rolling(14).mean()
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            
            signal = None
            direction = None
            if config_type == "OLD":
                is_expiry = (now.weekday() == 3)
                sig_dict = adapter.evaluate_signal(sub_df, symbol, 15.0, 1.0, {}, is_expiry)
                if sig_dict and sig_dict['strategy'] == 'VWAP_BOUNCE' and sig_dict['confidence'] >= 65:
                    signal = sig_dict
                    direction = sig_dict['options_direction']
            else:
                signal = master.select_best_signal(sub_df, symbol, 15.0, current_time=now)
                if signal:
                    direction = signal['direction']
            
            if signal and direction:
                pnl = simulate_trade(df_5m.iloc[i], df_5m.iloc[i:], risk_amt, direction)
                all_pnls.append(pnl)
                i += 78 # Skip bars to simulate single position
            else:
                i += 1
                
    return all_pnls

def compute_stats(pnls, initial_capital):
    if not pnls: return {"Net PnL": "₹0", "Win Rate": "0%", "Trades": 0, "Max DD": "0%", "PF": "0"}
    
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    
    net_pnl = sum(pnls)
    wr = len(wins) / len(pnls) * 100
    
    cap = initial_capital
    equity = []
    max_cap = initial_capital
    max_dd = 0
    for p in pnls:
        cap += p
        equity.append(cap)
        max_cap = max(max_cap, cap)
        dd = (max_cap - cap) / max_cap if max_cap > 0 else 0
        max_dd = max(max_dd, dd)
        
    pf = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
    
    return {
        "Net PnL": f"₹{net_pnl:,.0f}",
        "Win Rate": f"{wr:.1f}%",
        "Trades": len(pnls),
        "Max DD": f"{max_dd*100:.2f}%",
        "PF": f"{pf:.2f}"
    }

# Run period: last 30 days of data
start = pd.Timestamp("2026-03-24").tz_localize('Asia/Kolkata')
end = pd.Timestamp("2026-04-24").tz_localize('Asia/Kolkata')

print(f"Running Comparative Backtest from {start.date()} to {end.date()}...")

pnls_old = run_backtest("OLD", start, end)
stats_old = compute_stats(pnls_old, 1000000.0)

pnls_new = run_backtest("NEW", start, end)
stats_new = compute_stats(pnls_new, 1000000.0)

print("\nSIDE-BY-SIDE RESULTS:")
print(f"{'Metric':<15} | {'Config A (OLD)':<15} | {'Config B (NEW)':<15}")
print("-" * 50)
for metric in ["Net PnL", "Win Rate", "Trades", "Max DD", "PF"]:
    print(f"{metric:<15} | {stats_old[metric]:<15} | {stats_new[metric]:<15}")
