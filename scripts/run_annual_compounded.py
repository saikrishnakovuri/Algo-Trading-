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
from modules.portfolio_manager import PortfolioManager
from modules.options.risk_manager import OptionsRiskManager

# Silence spam
logging.getLogger("SMC_Engine").setLevel(logging.WARNING)
logging.getLogger("SMC_Structure").setLevel(logging.WARNING)
logging.getLogger("modules.strategy_selector").setLevel(logging.WARNING)

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"

class AnnualCompoundedBacktester:
    def __init__(self, initial_capital=500000.0):
        self.master = MasterStrategySelector()
        self.master.mode = "BALANCED"
        # We use PortfolioManager for global equity and Daily Risk Budget (2%)
        self.pm = PortfolioManager(initial_capital=initial_capital)
        # We use RiskManager for position sizing logic (risking 2% per trade)
        self.risk_manager = OptionsRiskManager(total_capital=initial_capital)
        self.data = {}
        self.trade_log = []
        self.active_trades = [] # List to track open portfolio trades

    def load_all_2025(self, symbols):
        print(f"📊 Loading 2025 Data for {len(symbols)} stocks...")
        start, end = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
        for sym in symbols:
            path = os.path.join(DATA_PATH, f"{sym}_minute.csv")
            if not os.path.exists(path): continue
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df = df[(df.index >= start) & (df.index <= end)].resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)
        print("✅ Data loaded.")

    def run_custom(self, start_date_str, end_date_str):
        # Sync risk manager capital with portfolio manager
        self.risk_manager.total_capital = self.pm.total_equity
        
        all_indices = sorted(list(set([idx.tz_localize(None) for df in self.data.values() for idx in df.index])))
        start_ts = pd.Timestamp(start_date_str).tz_localize(None)
        end_ts = pd.Timestamp(end_date_str).tz_localize(None).replace(hour=15, minute=30)
        valid_indices = [idx for idx in all_indices if start_ts <= idx <= end_ts]

        for now_naive in valid_indices:
            now = now_naive.tz_localize('Asia/Kolkata')
            
            # 1. Daily Reset
            if now.hour == 9 and now.minute == 15:
                self.pm.daily_reset()
                self.risk_manager.daily_reset()

            # 2. Check Exits for active trades
            self._manage_active_trades(now)

            # 3. Scan for new entries
            for sym, df in self.data.items():
                # Skip if already in a trade for this symbol
                if any(t['symbol'] == sym for t in self.active_trades): continue
                
                # Check naive index
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
                    # Position sizing from risk manager
                    entry_premium = self._estimate_premium(entry_price, entry_price, signal['direction'])
                    qty = self.risk_manager.get_position_size(sym, entry_premium, sl_dist)
                    
                    if qty > 0:
                        risk_val = sl_dist * qty
                        if self.pm.can_enter_trade(risk_val):
                            # Entry logic
                            self.active_trades.append({
                                "symbol": sym,
                                "entry_bar": df.loc[now_naive],
                                "signal": signal,
                                "entry_price": entry_price,
                                "sl": sl_price,
                                "tp": tp_price,
                                "qty": qty,
                                "risk_val": risk_val,
                                "entry_premium": entry_premium
                            })

        return self.pm.total_equity, len(self.trade_log)

    def _manage_active_trades(self, now):
        now_naive = now.tz_localize(None)
        to_remove = []
        for trade in self.active_trades:
            sym = trade['symbol']
            df = self.data[sym]
            if now_naive not in df.index: continue
            
            bar = df.loc[now_naive]
            signal = trade['signal']
            is_long = signal['direction'] == "CE"
            exit_price, exit_reason = None, None
            
            # SL/TP Check
            if is_long:
                if bar['low'] <= trade['sl']: exit_price, exit_reason = trade['sl'], "SL"
                elif bar['high'] >= trade['tp']: exit_price, exit_reason = trade['tp'], "TP"
            else:
                if bar['high'] >= trade['sl']: exit_price, exit_reason = trade['sl'], "SL"
                elif bar['low'] <= trade['tp']: exit_price, exit_reason = trade['tp'], "TP"
            
            # EOD or Time exit
            if not exit_price and now.hour == 15 and now.minute >= 15:
                exit_price, exit_reason = bar['close'], "EOD"

            if exit_price:
                exit_premium = self._estimate_premium(exit_price, trade['entry_price'], signal['direction'])
                net_pnl = (exit_premium - trade['entry_premium']) * trade['qty'] - BROKERAGE_OPTIONS
                
                # Update PM and logs
                self.pm.update_equity(net_pnl)
                self.risk_manager.record_trade(net_pnl, now)
                self.pm.remove_risk(trade['risk_val'])
                
                self.trade_log.append({
                    "timestamp": now.isoformat(),
                    "symbol": sym,
                    "strategy": signal['strategy'],
                    "net_pnl": net_pnl,
                    "reason": exit_reason
                })
                to_remove.append(trade)
        
        for t in to_remove: self.active_trades.remove(t)

    def _estimate_premium(self, spot, strike, direction, iv=0.20):
        intrinsic = max(0, spot - strike) if direction == 'CE' else max(0, strike - spot)
        time_value = spot * iv * (3/365)**0.5
        return max(intrinsic + time_value, 5.0)

if __name__ == "__main__":
    pass
