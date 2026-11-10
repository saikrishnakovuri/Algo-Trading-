import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import yaml
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import TOTAL_CAPITAL, BROKERAGE_EQUITY, BROKERAGE_OPTIONS

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("FastBacktester")

from modules.indicator_cache import precompute_indicators

DATA_PATH = "data/angel_historical"
RESULTS_PATH = "data/fast_backtest_results"
os.makedirs(RESULTS_PATH, exist_ok=True)

pd.options.mode.chained_assignment = None

# Load Configs
try:
    with open("config/risk_execution.yaml", "r", encoding="utf-8") as f:
        _full_cfg = yaml.safe_load(f)
        COSTS_CFG = _full_cfg.get("transaction_costs", {"enabled": False})
        POS_CFG = _full_cfg.get("position_sizing", {"max_notional_per_trade_pct_of_capital": 15.0, "fixed_risk_per_trade_pct": 1.0})
except Exception as e:
    logger.warning(f"Failed to load config: {e}")
    COSTS_CFG = {"enabled": False}
    POS_CFG = {"max_notional_per_trade_pct_of_capital": 15.0, "fixed_risk_per_trade_pct": 1.0}

from modules.strategy_mapper import STRATEGY_MAP, MAX_STRATEGIES
print(f"STRATEGY_MAP loaded: {list(STRATEGY_MAP.keys())}")
print(f"LOW_VOL strategies: {STRATEGY_MAP.get('LOW_VOL', 'KEY MISSING')}")
print(f"TRENDING_UP strategies: {[s.name for s in STRATEGY_MAP.get('TRENDING_UP',[])]}")

def load_data(symbol: str) -> pd.DataFrame:
    if symbol == "NIFTY":
        filename = "nifty50_1m.csv"
    elif symbol == "BANKNIFTY":
        filename = "banknifty_1m.csv"
    elif symbol == "FINNIFTY":
        filename = "finnifty_1m.csv"
    else:
        filename = f"{symbol}_1m.csv"
        
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

# Load Centralized Configs (Phase 25a compliance)
from modules.v3_utils import TOTAL_CAPITAL, NIFTY_LOT_SIZE, BANKNIFTY_LOT_SIZE, FINNIFTY_LOT_SIZE

def compute_costs(entry_price, exit_price, qty, symbol, cfg, premium_proxy):
    """Realistic cost per round-trip trade."""
    if not cfg.get("enabled"):
        return BROKERAGE_OPTIONS if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else BROKERAGE_EQUITY

    is_option = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    
    if is_option:
        # Use premium_proxy for notional instead of spot index value
        notional_entry = premium_proxy * qty
        notional_exit  = (premium_proxy * exit_price / entry_price) * qty
        
        lot_size = NIFTY_LOT_SIZE if symbol == "NIFTY" else BANKNIFTY_LOT_SIZE if symbol == "BANKNIFTY" else FINNIFTY_LOT_SIZE
        lots = max(1, int(qty / lot_size))
        
        # Per-symbol slippage
        slippage_pct = cfg.get('slippage_pct_per_leg_by_symbol', {}).get(symbol, cfg.get('slippage_pct_per_leg_default', 0.3))
        
        brokerage = 2 * cfg['brokerage_per_lot'] * lots
        stt       = notional_exit * cfg['stt_pct_sell_side'] / 100
        exchange  = (notional_entry + notional_exit) * cfg['exchange_txn_pct'] / 100
        gst       = (brokerage + exchange) * cfg['gst_pct_on_brokerage'] / 100
        sebi      = (notional_entry + notional_exit) * cfg['sebi_charges_pct'] / 100
        slippage  = (notional_entry + notional_exit) * slippage_pct / 100
        
        return brokerage + stt + exchange + gst + sebi + slippage
    else:
        # Equity costs (Spot trading)
        notional_entry = entry_price * qty
        notional_exit  = exit_price * qty
        brokerage = 40.0 # flat round trip
        stt = (notional_entry + notional_exit) * 0.1 / 100 
        exchange = (notional_entry + notional_exit) * 0.00345 / 100
        slippage = (notional_entry + notional_exit) * 0.1 / 100 
        return brokerage + stt + exchange + slippage

def simulate_trade(entry_bar, df_5m, risk_amt, signal, symbol):
    entry_price = entry_bar["close"]
    is_option = symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"]
    
    sl_price = signal.get('sl')
    tp_price = signal.get('tp')
    
    # Estimate premium proxy (Option price is usually ~1-2% of Spot for weekly ATM)
    premium_proxy = entry_price * 0.015 
    
    if sl_price is None:
        atr = entry_bar.get("atr", entry_price * 0.005)
        sl_dist = 2 * atr
        sl_price = entry_price - sl_dist if signal['direction'] in ['CE', 'BUY', 'LONG'] else entry_price + sl_dist
        
    if tp_price is None:
        sl_dist = abs(entry_price - sl_price)
        tp_price = entry_price + (2.0 * sl_dist) if signal['direction'] in ['CE', 'BUY', 'LONG'] else entry_price - (2.0 * sl_dist)

    sl_dist = abs(entry_price - sl_price)
    
    # REQ 25a-3: Use centralized capital
    capital = TOTAL_CAPITAL
    max_notional_pct = 15.0 
    fixed_risk_pct = 1.0 

    max_notional = capital * max_notional_pct / 100.0
    risk_amt_fixed = capital * fixed_risk_pct / 100.0
    
    if is_option:
        lot_size = NIFTY_LOT_SIZE if symbol == "NIFTY" else BANKNIFTY_LOT_SIZE if symbol == "BANKNIFTY" else FINNIFTY_LOT_SIZE
        max_lots_by_notional = int(max_notional / (premium_proxy * lot_size))
        max_lots_by_risk = int(risk_amt_fixed / (sl_dist * lot_size)) if sl_dist > 0 else 1
        
        final_lots = max(1, min(max_lots_by_notional, max_lots_by_risk))
        qty = final_lots * lot_size
    else:
        max_qty_by_notional = int(max_notional / entry_price)
        max_qty_by_risk = int(risk_amt_fixed / sl_dist) if sl_dist > 0 else 1
        qty = max(1, min(max_qty_by_notional, max_qty_by_risk))
    
    qty = max(1, min(qty, 1000)) # Absolute sanity cap
    
    exit_price, exit_reason = entry_price, "EOD"
    exit_idx = 0
    
    is_long = signal['direction'] in ["CE", "BUY", "LONG"]
    
    # Pre-slice exit search for speed
    exit_slice = df_5m.iloc[1:80] # Max hold ~6.5 hours
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
    
    if is_long:
        gross_pnl = (exit_price - entry_price) * qty
    else:
        gross_pnl = (entry_price - exit_price) * qty
        
    # Apply Transaction Costs (Phase 24b)
    txn_costs = compute_costs(entry_price, exit_price, qty, symbol, COSTS_CFG, premium_proxy)
    net_pnl = gross_pnl - txn_costs
    
    return {
        "timestamp": entry_bar.name.isoformat(),
        "symbol": symbol,
        "strategy": signal['strategy'],
        "direction": signal['direction'],
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2),
        "exit_reason": exit_reason,
        "qty": qty,
        "gross_pnl": round(float(gross_pnl), 2),
        "costs": round(float(txn_costs), 2),
        "net_pnl": round(float(net_pnl), 2),
        "regime": signal['context'].regime,
        "exit_idx": exit_idx
    }

from modules.risk_guard import RiskGuard

def run_fast_backtest_window(start_date, end_date, symbols):
    master = MasterStrategySelector()
    trade_log = []
    
    # Initialize RiskGuard for backtest
    from pathlib import Path
    state_file = Path('data/risk_guard_state.json')
    if state_file.exists(): state_file.unlink()
    # Using calibrated thresholds from Phase 21
    guard = RiskGuard(starting_capital=TOTAL_CAPITAL, daily_loss_pct=5.0, weekly_loss_pct=10.0, streak_limit=7)
    skipped_count = 0
    edge_skipped_count = 0
    
    for symbol in symbols:
        df_full = load_data(symbol)
        if df_full is None: continue
        
        # Apply window filter
        df_1m = df_full[(df_full.index >= start_date) & (df_full.index <= end_date)]
        if df_1m.empty: continue
        
        df_5m = resample_5m(df_1m)
        df_5m = precompute_indicators(df_5m)
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1] # This is O(1) view in modern pandas
            now = sub_df.index[-1]
            risk_pct = 0.02 if symbol in ["NIFTY", "BANKNIFTY", "FINNIFTY"] else 0.01
            risk_amt = 100000.0 * risk_pct
            
            signal = master.select_best_signal(sub_df, symbol, 14.0, current_time=now)
            
            if signal:
                # ── Phase 24c: Expected-PnL Gate ──
                entry_p = float(signal.get('entry_price') or df_5m.iloc[i]['close'])
                sl_p = float(signal.get('sl') or (entry_p - 2 * df_5m.iloc[i]['atr'] if signal['direction'] in ['CE','BUY','LONG'] else entry_p + 2 * df_5m.iloc[i]['atr']))
                tp_p = float(signal.get('tp') or (entry_p + 2 * abs(entry_p - sl_p) if signal['direction'] in ['CE','BUY','LONG'] else entry_p - 2 * abs(entry_p - sl_p)))
                
                sl_dist = abs(entry_p - sl_p)
                qty = int(risk_amt / sl_dist) if sl_dist > 0 else 1
                qty = max(1, min(qty, 500))
                
                premium_proxy = entry_p * 0.015
                expected_pnl = abs(tp_p - entry_p) * qty * (signal.get('confidence', 50) / 100)
                estimated_cost = compute_costs(entry_p, tp_p, qty, symbol, COSTS_CFG, premium_proxy)
                min_edge_required = estimated_cost * 1.5
                
                # Re-enabled edge filter for Phase 25a compliance
                if expected_pnl < min_edge_required:
                    edge_skipped_count += 1
                    i += 1
                    continue
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
    master.edge_filter_skipped = edge_skipped_count
    return trade_log, master

def analyze_results(trades, initial_capital):
    if not trades: return {}
    df = pd.DataFrame(trades)
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
    total_gross = df["gross_pnl"].sum()
    total_costs = df["costs"].sum()
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
    total_losses = [p for p in total_pnls if p <= 0]
    pf = abs(sum(total_wins) / sum(total_losses)) if total_losses and sum(total_losses) != 0 else 0
    summary = {
        "Total Trades": len(trades),
        "WR": f"{total_wr:.1f}%",
        "Gross PnL": f"INR {total_gross:,.0f}",
        "Costs": f"INR {total_costs:,.0f}",
        "Net PnL": f"INR {total_pnl:,.0f}",
        "PF": round(pf, 2),
        "Max DD": f"{max_dd*100:.2f}%"
    }
    return summary, strat_perf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbols", type=str, default="NIFTY,BANKNIFTY,RELIANCE")
    parser.add_argument("--funnel-report", action="store_true")
    parser.add_argument("--json-summary", action="store_true")
    args = parser.parse_args()
    
    symbols = args.symbols.split(",")
    
    # Date Filtering Logic
    if args.start_date:
        start_date = pd.to_datetime(args.start_date).tz_localize('Asia/Kolkata')
        end_date = pd.to_datetime(args.end_date or datetime.now()).tz_localize('Asia/Kolkata')
    else:
        # Fallback to --days
        end_date = datetime.now().astimezone(None)
        start_date = end_date - timedelta(days=args.days)
    
    start_time = datetime.now()
    trades, master = run_fast_backtest_window(start_date, end_date, symbols)
    end_time = datetime.now()
    
    if trades:
        summary, strat_perf = analyze_results(trades, 100000.0)
        
        if not args.json_summary:
            print(f"\n=== FAST BACKTEST SUMMARY ({start_date.date()} to {end_date.date()}, {args.symbols}) ===")
            for k, v in summary.items(): print(f"{k}: {v}")
            print("\n=== STRATEGY PERFORMANCE ===")
            print(pd.DataFrame(strat_perf).to_string(index=False))
            if args.funnel_report: print(master.funnel_report())
            print(f"Trades skipped by RiskGuard: {getattr(master, 'risk_guard_skipped', 0)}")
            print(f"Signals rejected by Edge-Filter: {getattr(master, 'edge_filter_skipped', 0)}")
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.json_summary:
            print(json.dumps({"summary": summary, "strategies": strat_perf, "skipped": getattr(master, 'risk_guard_skipped', 0), "edge_rejected": getattr(master, 'edge_filter_skipped', 0)}))
        else:
            with open(f"{RESULTS_PATH}/fast_backtest_{ts}.json", "w") as f:
                json.dump({"summary": summary, "strategies": strat_perf}, f, indent=4)
            pd.DataFrame(trades).to_csv(f"{RESULTS_PATH}/trades_optimized.csv", index=False)
            print(f"\nResults saved to {RESULTS_PATH}")
    else:
        if args.json_summary:
            print(json.dumps({"error": "No trades generated", "edge_rejected": getattr(master, 'edge_filter_skipped', 0)}))
        else:
            print(f"No trades generated. Edge-Filter rejected: {getattr(master, 'edge_filter_skipped', 0)}")
    
    if not args.json_summary:
        print(f"\nRuntime: {(end_time - start_time).total_seconds() / 60:.2f} minutes")

if __name__ == "__main__":
    main()
