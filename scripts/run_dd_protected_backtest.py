import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import TOTAL_CAPITAL, BROKERAGE_OPTIONS
from modules.indicator_cache import precompute_indicators
from modules.portfolio_manager import PortfolioManager

# Silence spam
logging.getLogger("SMC_Engine").setLevel(logging.WARNING)
logging.getLogger("SMC_Structure").setLevel(logging.WARNING)
logging.getLogger("modules.strategy_selector").setLevel(logging.WARNING)

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
LOG_FILE = "logs/dd_protected_bg_run.log"

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(message)s')

class DDProtectedBacktester:
    def __init__(self, initial_capital=1248800.0):
        self.master = MasterStrategySelector()
        self.master.mode = "BALANCED"
        self.pm = PortfolioManager(initial_capital=initial_capital)
        self.data = {}
        self.trade_log = []
        self.active_trades = []
        self.target_stocks = [
            "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
            "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA"
        ]
        self.peak_equity = initial_capital

    def load_data(self, start, end):
        print(f"[INFO] Loading Data {start} to {end}...")
        self.data = {}
        for sym in self.target_stocks:
            path = os.path.join(DATA_PATH, f"{sym}_minute.csv")
            if not os.path.exists(path): continue
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[(df.index >= start) & (df.index <= end)].resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)
        print(f"[OK] Data loaded.")

    def run_month(self, start_date_str, end_date_str):
        start = pd.Timestamp(start_date_str)
        end = pd.Timestamp(end_date_str)
        self.load_data(start, end)
        
        all_indices = sorted(list(set([idx for df in self.data.values() for idx in df.index])))
        
        print(f"[START] Month {start_date_str}. Equity: Rs {self.pm.total_equity:.2f}")
        logging.info(f"[START] Month {start_date_str}. Equity: Rs {self.pm.total_equity:.2f}")

        is_daily_blocked = False
        daily_start_equity = self.pm.total_equity

        for now_naive in all_indices:
            now = now_naive.tz_localize('Asia/Kolkata')
            
            self.peak_equity = max(self.peak_equity, self.pm.total_equity)
            
            # Daily reset
            if now.hour == 9 and now.minute == 15:
                is_daily_blocked = False
                daily_start_equity = self.pm.total_equity
                self.pm.daily_reset()

            # Manage active trades
            self._manage_active_trades(now_naive, force_close=is_daily_blocked)
            
            # Circuit breaker check
            unrealized_pnl = 0
            for trade in self.active_trades:
                sym = trade['symbol']
                if now_naive in self.data[sym].index:
                    curr_price = self.data[sym].loc[now_naive]['close']
                    is_long = trade['signal']['direction'] == "CE"
                    if is_long:
                        unreal_trade_pnl = (curr_price - trade['entry_price']) * trade['qty']
                    else:
                        unreal_trade_pnl = (trade['entry_price'] - curr_price) * trade['qty']
                    unrealized_pnl += unreal_trade_pnl - 40.0

            total_daily_pnl = self.pm.daily_pnl + unrealized_pnl
            
            # PROTECT 1: 1% Daily Circuit Breaker (Tightened from 2%)
            max_daily_loss = -0.01 * daily_start_equity
            if total_daily_pnl <= max_daily_loss and not is_daily_blocked:
                is_daily_blocked = True
                logging.info(f"[{now}] [STOP] DAILY 1% CIRCUIT BREAKER. PnL: {total_daily_pnl:.2f}")

            # New entries
            if not is_daily_blocked:
                for sym, df in self.data.items():
                    if any(t['symbol'] == sym for t in self.active_trades): continue
                    if now_naive not in df.index: continue
                    
                    sub_df = df.loc[:now_naive]
                    if len(sub_df) < 50: continue

                    signal = self.master.select_best_signal(sub_df, sym, 15.0, current_time=now)
                    if signal:
                        entry_price = signal.get('entry', df.loc[now_naive]['close'])
                        sl_price = signal.get('sl')
                        tp_price = signal.get('tp')
                        
                        if sl_price is None:
                            atr = sub_df['atr'].iloc[-1] if 'atr' in sub_df.columns else entry_price * 0.01
                            sl_price = entry_price - (1.5 * atr) if signal['direction'] == "CE" else entry_price + (1.5 * atr)
                        if tp_price is None:
                            sl_dist = abs(entry_price - sl_price)
                            tp_price = entry_price + (2.0 * sl_dist) if signal['direction'] == "CE" else entry_price - (2.0 * sl_dist)

                        sl_dist = abs(entry_price - sl_price)
                        if sl_dist <= 0: sl_dist = 1.0
                        
                        # PROTECT 2: Drawdown-Aware Sizing
                        current_dd = (self.peak_equity - self.pm.total_equity) / self.peak_equity
                        base_risk_pct = 0.01
                        if current_dd > 0.05:
                            base_risk_pct = 0.005 # Halve risk if DD > 5%
                            
                        # PROTECT 3: Compounding Cap (Max 10k risk per trade)
                        calculated_risk = self.pm.total_equity * base_risk_pct
                        max_risk_per_stock = min(calculated_risk, 10000.0)
                        
                        # PROTECT 4: Asymmetric Tier Sizing
                        tier_info = signal.get('trade_tier', {})
                        tier_label = tier_info.get('tier', 'A')
                        if tier_label == 'B':
                            max_risk_per_stock *= 0.3
                        elif tier_label == 'C':
                            max_risk_per_stock *= 0.1
                            
                        raw_qty = max_risk_per_stock / sl_dist
                        qty = max(1, int(raw_qty))
                        
                        required_margin = (entry_price * qty) / 5.0
                        if required_margin > self.pm.total_equity:
                             qty = int((self.pm.total_equity * 5.0) / entry_price)
                             if qty < 1: continue

                        risk_val = sl_dist * qty
                        
                        self.active_trades.append({
                            "symbol": sym,
                            "signal": signal,
                            "entry_price": entry_price,
                            "sl": sl_price,
                            "tp": tp_price,
                            "qty": qty
                        })

            # Compounding EOD
            if now.hour == 15 and now.minute >= 15:
                self._manage_active_trades(now_naive, force_close=True)
                self.pm.update_equity(0) 

    def _manage_active_trades(self, now_naive, force_close=False):
        to_remove = []
        for trade in self.active_trades:
            sym = trade['symbol']
            df = self.data[sym]
            if now_naive not in df.index: continue
            
            bar = df.loc[now_naive]
            is_long = trade['signal']['direction'] == "CE"
            exit_price, exit_reason = None, None
            
            if force_close:
                exit_price, exit_reason = bar['close'], "FORCED_CLOSE"
            else:
                if is_long:
                    if bar['low'] <= trade['sl']: exit_price, exit_reason = trade['sl'], "SL"
                    elif bar['high'] >= trade['tp']: exit_price, exit_reason = trade['tp'], "TP"
                else:
                    if bar['high'] >= trade['sl']: exit_price, exit_reason = trade['sl'], "SL"
                    elif bar['low'] <= trade['tp']: exit_price, exit_reason = trade['tp'], "TP"
            
            if exit_price:
                if is_long:
                    gross_pnl = (exit_price - trade['entry_price']) * trade['qty']
                else:
                    gross_pnl = (trade['entry_price'] - exit_price) * trade['qty']
                
                net_pnl = gross_pnl - 40.0 
                self.pm.update_equity(net_pnl)
                
                self.trade_log.append({
                    "timestamp": now_naive.isoformat(),
                    "symbol": sym,
                    "strategy": trade['signal']['strategy'],
                    "net_pnl": net_pnl,
                    "reason": exit_reason
                })
                to_remove.append(trade)
        
        for t in to_remove: self.active_trades.remove(t)

    def run_all(self, months):
        for m in months:
            self.run_month(m[0], m[1])
            print(f"✅ Finished {m[2]}. Equity: Rs {self.pm.total_equity:.2f}")
            
        df_trades = pd.DataFrame(self.trade_log)
        df_trades.to_csv("data/backtest_results/dd_protected_bg_trades.csv", index=False)
        print("\n=== COMPLETE ===")
        print(f"Final Equity: Rs {self.pm.total_equity:.2f}")

if __name__ == "__main__":
    months_to_run = [
        ('2025-04-01', '2025-04-30', '2025-04'),
        ('2025-05-01', '2025-05-31', '2025-05'),
        ('2025-07-01', '2025-07-31', '2025-07'),
        ('2025-10-01', '2025-10-31', '2025-10'),
        ('2025-11-01', '2025-11-30', '2025-11'),
        ('2026-03-01', '2026-03-31', '2026-03')
    ]
    DDProtectedBacktester().run_all(months_to_run)
