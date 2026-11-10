import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import TOTAL_CAPITAL, BROKERAGE_EQUITY, BROKERAGE_OPTIONS, NIFTY_LOT_SIZE, BANKNIFTY_LOT_SIZE
from modules.indicator_cache import precompute_indicators
from modules.options.risk_manager import OptionsRiskManager

# Setup detailed logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[
        logging.FileHandler("logs/validation_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ValidationBacktester")

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
RESULTS_PATH = "data/backtest_results"
os.makedirs(RESULTS_PATH, exist_ok=True)

class ValidationBacktester:
    def __init__(self, initial_capital=500000.0):
        self.master = MasterStrategySelector()
        self.risk_manager = OptionsRiskManager(total_capital=initial_capital)
        self.trade_log = []
        self.narrative_events = []
        self.metrics = {
            "total_trades": 0,
            "manipulation_veto_count": 0,
            "reclaim_invalidation_count": 0,
            "stale_setup_expiry_count": 0,
            "fake_bos_prevented": 0,
            "wick_only_breaks_rejected": 0,
            "double_sweep_detections": 0,
            "memory_persistence_success": 0,
            "bullish_bos_accuracy": {"wins": 0, "total": 0},
            "bearish_bos_accuracy": {"wins": 0, "total": 0},
            "choch_accuracy": {"wins": 0, "total": 0},
            "liquidity_bos_accuracy": {"wins": 0, "total": 0},
        }

    def load_data(self, symbol: str, start_date, end_date):
        filename = f"{symbol}_minute.csv"
        path = os.path.join(DATA_PATH, filename)
        if not os.path.exists(path):
            return None
        
        # Load the CSV
        df = pd.read_csv(path)
        
        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"], format='%Y-%m-%d %H:%M:%S')
        df.set_index("date", inplace=True)
        
        # Ensure dates are timezone-aware if the comparison is timezone-aware
        if start_date.tzinfo is not None and df.index.tz is None:
            df.index = df.index.tz_localize(start_date.tzinfo)
        
        # Filter range
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df

    def resample_5m(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = [c.lower() for c in df.columns]
        return df.resample("5min").agg({
            "open": "first", "high": "max",
            "low": "min", "close": "last", "volume": "sum"
        }).dropna()

    def estimate_premium(self, spot, strike, direction, iv=0.20):
        intrinsic = max(0, spot - strike) if direction == 'CE' else max(0, strike - spot)
        # Simplified time value for 3-day DTE
        time_value = spot * iv * (3/365)**0.5
        return max(intrinsic + time_value, 5.0)

    def run_for_symbol(self, symbol: str, start_date_str: str, end_date_str: str):
        self.run(symbol=symbol, start_date_str=start_date_str, end_date_str=end_date_str)

    def run(self, symbol="NIFTY", start_date_str="2026-03-01", end_date_str="2026-03-31"):
        start_date = pd.Timestamp(start_date_str).tz_localize('Asia/Kolkata')
        end_date = pd.Timestamp(end_date_str).tz_localize('Asia/Kolkata')
        
        df_1m = self.load_data(symbol, start_date, end_date)
        if df_1m is None or df_1m.empty:
            logger.error(f"No data for {symbol} in range {start_date_str} to {end_date_str}")
            return
            
        df_5m = self.resample_5m(df_1m)
        df_5m = precompute_indicators(df_5m)
        
        logger.info(f"Starting Validation Backtest for {symbol} | {start_date_str} to {end_date_str} | Future-Blind")
        
        # Clear logs for this symbol run
        self.trade_log = []

        i = 50
        while i < len(df_5m):
            current_idx = i
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            
            # Record narrative state before selection
            narrative = self.master.market_memory.narrative_state(symbol)
            
            # Logic Audit: Check for specific events to increment metrics
            self._audit_narrative_state(symbol, narrative, current_idx)
            
            signal = self.master.select_best_signal(sub_df, symbol, 15.0, current_time=now)
            
            if signal:
                # Check Veto
                if self.master.market_memory.should_veto_for_manipulation(symbol, current_idx=current_idx):
                    self.metrics["manipulation_veto_count"] += 1
                    logger.info(f"[{now}] VETO: {self.master.market_memory.manipulation_reason(symbol)}")
                    i += 1
                    continue
                
                # Check Invalidation
                if signal.get("memory_state") == "INVALIDATED":
                     self.metrics["reclaim_invalidation_count"] += 1
                     i += 1
                     continue

                # Can we trade? (Risk Manager)
                allowed, reason = self.risk_manager.can_trade(symbol, now)
                if allowed:
                    trade = self._simulate_trade(df_5m.iloc[i], df_5m.iloc[i+1:], signal, symbol)
                    if trade:
                        self.trade_log.append(trade)
                        self.risk_manager.record_trade(trade['net_pnl'], now)
                        
                        # Log detail
                        logger.info(f"[{now}] TRADE: {trade['strategy']} {trade['direction']} | PnL: {trade['net_pnl']} | MemoryID: {signal.get('memory_setup_id')}")
                        
                        # Update metrics
                        self.metrics["total_trades"] += 1
                        setup_base = trade['strategy'].replace("MARKET_MEMORY_", "")
                        if "BOS" in setup_base:
                            key = "bullish_bos_accuracy" if trade['direction'] == "CE" else "bearish_bos_accuracy"
                            self.metrics[key]["total"] += 1
                            if trade['net_pnl'] > 0: self.metrics[key]["wins"] += 1
                        elif "CHOCH" in setup_base:
                            self.metrics["choch_accuracy"]["total"] += 1
                            if trade['net_pnl'] > 0: self.metrics["choch_accuracy"]["wins"] += 1

                        i += trade['exit_idx'] + 1
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1
                
            # Daily reset for risk manager
            if i < len(df_5m) and df_5m.index[i].date() > now.date():
                self.risk_manager.daily_reset()

        self._finalize_reports()

    def _audit_narrative_state(self, symbol, narrative, current_idx):
        # Scan completed setups for metrics
        completed = self.master.market_memory.completed
        for setup in completed:
            if setup.updated_bar_idx == current_idx:
                if setup.state == "INVALIDATED" and "structure_reclaimed" in setup.reasons:
                    self.metrics["reclaim_invalidation_count"] += 1
                elif setup.state == "EXPIRED":
                    self.metrics["stale_setup_expiry_count"] += 1
                elif "double_sweep" in setup.reasons:
                    self.metrics["double_sweep_detections"] += 1

    def _simulate_trade(self, entry_bar, exit_df, signal, symbol):
        entry_price = entry_bar["close"]
        direction = signal['direction']
        sl = signal.get('sl')
        tp = signal.get('tp')
        
        # REQ 25a-4: Handle missing SL/TP
        if sl is None:
            atr = entry_bar.get("atr", entry_price * 0.005)
            sl_dist = 1.5 * atr
            sl = entry_price - sl_dist if direction == 'CE' else entry_price + sl_dist
        
        if tp is None:
            sl_dist = abs(entry_price - sl)
            tp = entry_price + (2.0 * sl_dist) if direction == 'CE' else entry_price - (2.0 * sl_dist)

        if exit_df.empty:
            return None

        entry_premium = self.estimate_premium(entry_price, entry_price, direction)
        qty = self.risk_manager.get_position_size(symbol, entry_premium, abs(entry_price - sl))
        
        exit_price, exit_reason, exit_idx = entry_price, "EOD", 0
        is_long = direction == "CE"
        
        found_exit = False
        for idx, bar in enumerate(exit_df.itertuples()):
            exit_idx = idx + 1
            if is_long:
                if bar.low <= sl:
                    exit_price, exit_reason = sl, "SL"
                    found_exit = True
                    break
                if bar.high >= tp:
                    exit_price, exit_reason = tp, "TP"
                    found_exit = True
                    break
            else:
                if bar.high >= sl:
                    exit_price, exit_reason = sl, "SL"
                    found_exit = True
                    break
                if bar.low <= tp:
                    exit_price, exit_reason = tp, "TP"
                    found_exit = True
                    break
            # Time exit after 4 hours
            if idx > 48: 
                exit_price, exit_reason = bar.close, "TIME"
                found_exit = True
                break 

        if not found_exit:
            exit_price = exit_df.iloc[-1]["close"]
            exit_reason = "DATA_END"
            exit_idx = len(exit_df)

        exit_premium = self.estimate_premium(exit_price, entry_price, direction)
        net_pnl = (exit_premium - entry_premium) * qty - BROKERAGE_OPTIONS
        
        return {
            "timestamp": entry_bar.name.isoformat(),
            "symbol": symbol,
            "strategy": signal['strategy'],
            "direction": direction,
            "entry": round(entry_price, 2),
            "exit": round(exit_price, 2),
            "exit_reason": exit_reason,
            "qty": qty,
            "net_pnl": round(net_pnl, 2),
            "exit_idx": exit_idx
        }

    def _finalize_reports(self):
        # Calculate final stats
        df = pd.DataFrame(self.trade_log)
        if df.empty:
            logger.error("No trades executed.")
            return

        wins = df[df["net_pnl"] > 0]
        summary = {
            "total_trades": len(df),
            "win_rate": f"{len(wins)/len(df)*100:.2f}%",
            "net_profit": df["net_pnl"].sum(),
            "profit_factor": abs(wins["net_pnl"].sum() / df[df["net_pnl"] < 0]["net_pnl"].sum()) if not df[df["net_pnl"] < 0].empty else 99,
            "max_drawdown_pct": self._calculate_drawdown(df["net_pnl"])
        }
        
        logger.info("\n=== VALIDATION RESULTS SUMMARY ===")
        for k, v in summary.items(): logger.info(f"{k}: {v}")
        
        logger.info("\n=== NARRATIVE ENGINE METRICS ===")
        for k, v in self.metrics.items(): logger.info(f"{k}: {v}")
        
        # Save files
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df.to_csv(f"{RESULTS_PATH}/validation_trades_{ts}.csv", index=False)
        with open(f"{RESULTS_PATH}/validation_metrics_{ts}.json", "w") as f:
            json.dump({"summary": summary, "metrics": self.metrics}, f, indent=4)
        
        logger.info(f"Reports saved to {RESULTS_PATH}")

    def _calculate_drawdown(self, pnls):
        capital = 500000.0
        peak = capital
        max_dd = 0
        current = capital
        for p in pnls:
            current += p
            if current > peak: peak = current
            dd = (peak - current) / peak
            if dd > max_dd: max_dd = dd
        return f"{max_dd*100:.2f}%"

if __name__ == "__main__":
    backtester = ValidationBacktester()
    backtester.run(symbol="NIFTY", start_date_str="2026-03-01", end_date_str="2026-03-31")
