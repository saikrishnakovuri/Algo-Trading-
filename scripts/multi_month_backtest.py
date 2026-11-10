import os
import pandas as pd
import numpy as np
import random
from datetime import datetime, time, timedelta
import logging

# Set up simple logging for backtest
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RandomBacktest")

# Import our actual production modules
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.options.risk_manager import OptionsRiskManager
from modules.options.trade_executor import OptionTradeManager

# Configuration
TOTAL_CAPITAL = 500000.0
SYMBOL = "NIFTY"
LOT_SIZE = 65

class BacktestBroker:
    def __init__(self, df):
        self.df = df
    def get_ltp(self, symbol_key):
        # symbol_key is NIFTY or NIFTY_STRIKE_TYPE
        if symbol_key == "NIFTY":
            return self.current_row['Close']
        return self.current_premium # Simplified for backtest
    def login(self): return True
    def get_vix(self): return self.current_vix
    def get_pcr(self, sym): return 1.0 # Neutral proxy
    def get_option_chain_oi(self, sym): return {} # Empty dict for simplicity
    def get_expiry_list(self, sym): return ["2026-12-31"] # Placeholder
    def get_full_option_chain(self, sym):
        # Mocking an option chain row
        return pd.DataFrame([{
            'expiry': "2026-12-31",
            'strike': int(round(self.current_row['Close'] / 50) * 50),
            'type': self.pending_type,
            'ltp': self.current_premium,
            'bid': self.current_premium - 0.5,
            'ask': self.current_premium + 0.5,
            'delta': 0.5,
            'oi': 1000000,
            'volume': 500000
        }])

def run_random_days_backtest():
    # 1. Load Data
    logger.info("Loading NIFTY Data...")
    df = pd.read_csv("data/nifty50_5m.csv")
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df.set_index('Timestamp', inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True)

    # 2. Pick 10 Random Days (Dec - Mar)
    valid_dates = df.index.normalize().unique()
    target_dates = [d for d in valid_dates if d.month in [12, 1, 2, 3] and d.year in [2025, 2026]]
    
    if len(target_dates) < 10:
        sampled_dates = target_dates
    else:
        sampled_dates = sorted(random.sample(target_dates, 10))

    logger.info(f"Sampled Dates: {[d.date() for d in sampled_dates]}")

    # 3. Initialize Engines
    broker = BacktestBroker(df)
    adapter = IndexLiquidityTrapAdapter()
    risk_manager = OptionsRiskManager(TOTAL_CAPITAL)
    trade_manager = OptionTradeManager(broker, None, risk_manager)
    
    # We need a mock selector that doesn't filter too hard for backtest
    from modules.options.strike_selector import OptionSelector
    selector = OptionSelector(broker)

    results = []
    
    for day in sampled_dates:
        logger.info(f"--- Processing Day: {day.date()} ---")
        day_df = df[df.index.normalize() == day]
        risk_manager.daily_reset()
        
        for i in range(20, len(day_df)):
            current_ts = day_df.index[i]
            broker.current_row = day_df.iloc[i]
            broker.current_vix = vix_df.iloc[vix_df.index.get_loc(current_ts, method='nearest')]['Close']
            
            # A. Check Exits (High Frequency Proxy)
            if trade_manager.active_trades:
                quotes = {}
                for tid, t in list(trade_manager.active_trades.items()):
                    spot_entry = t['spot_at_entry']
                    spot_now = broker.current_row['Close']
                    move_pct = (spot_now - spot_entry) / spot_entry
                    if t['type'] == 'PE': move_pct *= -1.0
                    
                    # More realistic premium: Delta 0.5 + Gamma
                    # 1% spot move = ~20-25% premium move
                    current_premium = t['entry_price'] * (1 + move_pct * 25) 
                    current_premium -= (i - t['start_idx']) * 0.15 # Theta
                    
                    quotes[tid] = {'ltp': max(0.1, current_premium), 'spot': spot_now}
                
                trade_manager.monitor_exits(quotes)
            
            # B. EOD Force Close at 15:20 if still open
            if current_ts.time() >= time(15, 20) and trade_manager.active_trades:
                for tid in list(trade_manager.active_trades.keys()):
                    t = trade_manager.active_trades[tid]
                    # Get final premium
                    spot_now = broker.current_row['Close']
                    move_pct = (spot_now - t['spot_at_entry']) / t['spot_at_entry']
                    if t['type'] == 'PE': move_pct *= -1.0
                    final_p = t['entry_price'] * (1 + move_pct * 25) - (i - t['start_idx']) * 0.15
                    trade_manager.close_trade(tid, max(0.1, final_p), "BACKTEST_EOD")
                    del trade_manager.active_trades[tid]

            # C. Check Entry
            can_trade, reason = risk_manager.can_trade(SYMBOL, current_ts)
            if can_trade:
                # Use slice up to current i
                hist_df = day_df.iloc[max(0, i-100):i+1]
                # Pass mock OI that satisfies adapter
                mock_oi = {int(round(broker.current_row['Close']/50)*50): {'ce_oi': 2000000, 'pe_oi': 2000000, 'ce_oi_change': 100000, 'pe_oi_change': 100000}}
                
                signal = adapter.evaluate_signal(hist_df, SYMBOL, broker.current_vix, 1.0, mock_oi, False)
                
                if signal and signal['confidence'] >= 40: # Lowered for backtest sensitivity
                    # Mock Selection
                    broker.pending_type = signal['options_direction']
                    # Premium Proxy: 1% of index price
                    broker.current_premium = broker.current_row['Close'] * 0.008 
                    
                    opt = selector.select_option(signal['options_direction'], signal['confidence'], 
                                              signal['spot_price'], broker.current_vix, ["2026-12-31"], 
                                              broker.get_full_option_chain(SYMBOL), current_ts)
                    if not opt:
                        # Force select ATM if selector is too picky for backtest
                        opt = {
                            'symbol': SYMBOL, 'strike': int(round(broker.current_row['Close']/50)*50),
                            'option_type': signal['options_direction'], 'expiry': "2026-12-31",
                            'premium': broker.current_premium, 'lot_size': 65
                        }
                    
                    if opt:
                        tid = trade_manager.enter_trade(signal, opt, TOTAL_CAPITAL)
                        if tid in trade_manager.active_trades:
                            trade_manager.active_trades[tid]['spot_at_entry'] = signal['spot_price']
                            trade_manager.active_trades[tid]['start_idx'] = i

        day_status = risk_manager.get_risk_status()
        logger.info(f"Day Result: {day_status}")
        results.append({'date': day.date(), 'pnl': day_status['daily_pnl'], 'trades': day_status['trades']})

    # Final Summary
    res_df = pd.DataFrame(results)
    print("\n" + "="*40)
    print("RANDOM 10-DAY BACKTEST RESULTS (DEC-MAR)")
    print("="*40)
    print(res_df)
    print("-"*40)
    print(f"Total PnL: ₹{res_df['pnl'].sum():,.2f}")
    print(f"Win Days: {(res_df['pnl'] > 0).sum()}/10")
    print(f"Total Trades: {res_df['trades'].sum()}")
    print("="*40)

if __name__ == "__main__":
    run_random_days_backtest()
