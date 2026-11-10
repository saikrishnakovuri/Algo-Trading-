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
LOG_FILE = "logs/feb_mar_2025_bg_run.log"

os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(message)s')

class BackgroundCompoundingBacktester:
    def __init__(self, initial_capital=839430.31):
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

    def load_data(self):
        print("[INFO] Loading Feb-Mar 2025 Data for 12 stocks...")
        start, end = pd.Timestamp("2025-02-01"), pd.Timestamp("2025-03-31")
        for sym in self.target_stocks:
            path = os.path.join(DATA_PATH, f"{sym}_minute.csv")
            if not os.path.exists(path): continue
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            # Make naive
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[(df.index >= start) & (df.index <= end)].resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)
        print(f"[OK] Data loaded for {len(self.data)} stocks.")

    def _estimate_premium(self, spot, strike, direction, iv=0.20):
        intrinsic = max(0, spot - strike) if direction == 'CE' else max(0, strike - spot)
        time_value = spot * iv * (3/365)**0.5
        return max(intrinsic + time_value, 5.0)

    def run(self):
        self.load_data()
        all_indices = sorted(list(set([idx for df in self.data.values() for idx in df.index])))
        
        print(f"[START] Starting Background Run. Initial Equity: Rs {self.pm.total_equity:.2f}")
        logging.info(f"[START] Starting Feb-Mar 2025 Background Run. Initial Equity: Rs {self.pm.total_equity:.2f}")

        is_daily_blocked = False
        daily_start_equity = self.pm.total_equity

        for now_naive in all_indices:
            now = now_naive.tz_localize('Asia/Kolkata')
            
            # Daily reset
            if now.hour == 9 and now.minute == 15:
                is_daily_blocked = False
                daily_start_equity = self.pm.total_equity
                self.pm.daily_reset()

            # Manage active trades & check global daily loss limit
            daily_realized_pnl = self._manage_active_trades(now_naive, force_close=is_daily_blocked)
            
            # Unrealized PnL check for circuit breaker
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
                        
                    unrealized_pnl += unreal_trade_pnl - 40.0 # Deducting assumed equity brokerage

            total_daily_pnl = self.pm.daily_pnl + unrealized_pnl
            
            # Circuit Breaker: 2% of daily start equity
            max_daily_loss = -0.02 * daily_start_equity
            if total_daily_pnl <= max_daily_loss and not is_daily_blocked:
                is_daily_blocked = True
                logging.info(f"[{now}] [STOP] DAILY 2% CIRCUIT BREAKER HIT. PnL: {total_daily_pnl:.2f}. Closing all positions.")
                print(f"[{now}] [STOP] DAILY 2% CIRCUIT BREAKER HIT. PnL: {total_daily_pnl:.2f}. Closing all positions.")
                # Force close happens on next loop iteration

            # Scan for new entries if not blocked
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
                        
                        # Intraday Cash Equity Logic (5x Leverage)
                        # Risk per trade is 1% of total equity
                        max_risk_per_stock = self.pm.total_equity * 0.01
                        
                        # Position Sizing: Qty = Risk / StopLoss Distance
                        raw_qty = max_risk_per_stock / sl_dist
                        qty = max(1, int(raw_qty)) # Integer quantity for stocks
                        
                        # Check margin requirements (5x leverage)
                        required_margin = (entry_price * qty) / 5.0
                        
                        if required_margin > self.pm.total_equity:
                             # Cap qty to available margin if risk calculation exceeds buying power
                             qty = int((self.pm.total_equity * 5.0) / entry_price)
                             if qty < 1: continue

                        risk_val = sl_dist * qty
                        
                        # In this test, we enforce the 1% risk per trade
                        self.active_trades.append({
                            "symbol": sym,
                            "signal": signal,
                            "entry_price": entry_price,
                            "sl": sl_price,
                            "tp": tp_price,
                            "qty": qty
                        })
                        logging.info(f"[{now}] [ENTER] {sym} | {signal['direction']} | {signal['strategy']} | Qty: {qty} | Risk: Rs {risk_val:.2f} | Margin: Rs {required_margin:.2f}")

            # Compounding at end of day
            if now.hour == 15 and now.minute == 25:
                # Force close anything left
                self._manage_active_trades(now_naive, force_close=True)
                self.pm.update_equity(0) # Equity is updated iteratively during trades
                
                # Output daily status
                status = f"[{now.date()}] EOD Equity: Rs {self.pm.total_equity:.2f} | Daily PnL: Rs {self.pm.daily_pnl:.2f}"
                print(status)
                logging.info(status)

        # Final Summary
        df_trades = pd.DataFrame(self.trade_log)
        df_trades.to_csv("data/backtest_results/feb_mar_2025_bg_trades.csv", index=False)
        print("\n=== FEB-MAR 2025 COMPLETED ===")
        print(f"Final Equity: Rs {self.pm.total_equity:.2f}")
        if not df_trades.empty:
            wins = len(df_trades[df_trades['net_pnl'] > 0])
            total = len(df_trades)
            print(f"Total Trades: {total} | Win Rate: {(wins/total)*100:.1f}%")
        logging.info("BACKTEST COMPLETE.")

    def _manage_active_trades(self, now_naive, force_close=False):
        to_remove = []
        realized_pnl_this_bar = 0
        
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
                # Cash Equity PnL Calculation
                if is_long:
                    gross_pnl = (exit_price - trade['entry_price']) * trade['qty']
                else:
                    gross_pnl = (trade['entry_price'] - exit_price) * trade['qty']
                
                # Assume standard equity intraday brokerage + STT
                equity_brokerage = 40.0 
                net_pnl = gross_pnl - equity_brokerage
                
                # Update compounding capital immediately
                self.pm.update_equity(net_pnl)
                realized_pnl_this_bar += net_pnl
                
                self.trade_log.append({
                    "timestamp": now_naive.isoformat(),
                    "symbol": sym,
                    "strategy": trade['signal']['strategy'],
                    "net_pnl": net_pnl,
                    "reason": exit_reason
                })
                logging.info(f"[{now_naive}] [EXIT] {sym} | Reason: {exit_reason} | PnL: Rs {net_pnl:.2f}")
                to_remove.append(trade)
        
        for t in to_remove: self.active_trades.remove(t)
        return realized_pnl_this_bar

if __name__ == "__main__":
    BackgroundCompoundingBacktester().run()
