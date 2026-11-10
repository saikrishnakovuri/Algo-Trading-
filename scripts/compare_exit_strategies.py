import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime, time, timedelta

# Mock/Import Engines
from modules.momentum_engine import MomentumBreakoutEngine

class StockBacktester:
    def __init__(self, symbols, data_dir, capital=100000.0, risk_per_trade=0.02):
        self.symbols = symbols
        self.data_dir = data_dir
        self.capital = capital
        self.risk_amount = capital * risk_per_trade
        self.engine = MomentumBreakoutEngine()
        self.cost_per_trade = 100.0 # Brokerage + Taxes + Slippage approx
        
    def load_data(self, symbol):
        path = os.path.join(self.data_dir, f"{symbol}_1m.csv")
        if not os.path.exists(path):
            print(f"Data not found for {symbol}")
            return None
        df = pd.read_csv(path)
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        # Convert to IST (from UTC)
        df['Datetime'] = df['Datetime'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
        df.set_index('Datetime', inplace=True)
        # Resample to 5m
        df_5m = df.resample('5min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        return df_5m

    def run_backtest(self, strategy_type='A'):
        results = []
        config = {
            'range_atr_threshold': 3.5, # Slightly tighter consolidation
            'volume_breakout_ratio': 1.1, # Relaxed volume for stocks
            'consolidation_bars': 4 # Relaxed bars
        }
        for symbol in self.symbols:
            df = self.load_data(symbol)
            if df is None: continue
            
            # Group by day
            df['Date'] = df.index.date
            days = df['Date'].unique()
            test_days = sorted(days)[-10:]
            print(f"Testing {symbol} over {len(test_days)} days...")
            
            for day in test_days:
                day_df = df[df['Date'] == day].copy()
                day_trades = 0
                consecutive_losses = 0
                
                # ATR for SL
                high = day_df['High']; low = day_df['Low']; close = day_df['Close'].shift(1)
                tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
                day_df['ATR'] = tr.rolling(14).mean()
                
                active_trade = None
                
                for i in range(20, len(day_df)):
                    curr_time = day_df.index[i].time()
                    
                    if active_trade:
                        curr_bar = day_df.iloc[i]
                        exit_price = None
                        exit_reason = None
                        
                        if active_trade['side'] == 'CE':
                            if strategy_type == 'A':
                                if not active_trade['partial_booked'] and curr_bar['High'] >= active_trade['target1']:
                                    active_trade['partial_booked'] = True
                                    active_trade['sl'] = active_trade['entry']
                                if active_trade['partial_booked']:
                                    r_reached = (curr_bar['High'] - active_trade['entry']) / active_trade['risk_dist']
                                    steps = int((r_reached - 1.5) / 0.5)
                                    if steps > 0:
                                        new_sl = active_trade['entry'] + (1.0 + steps * 0.5) * active_trade['risk_dist']
                                        active_trade['sl'] = max(active_trade['sl'], new_sl)
                                if curr_bar['Low'] <= active_trade['sl']:
                                    exit_price = active_trade['sl']
                                    exit_reason = "SL_HIT"
                            else:
                                if not active_trade['t2_hit'] and curr_bar['High'] >= active_trade['target2']:
                                    active_trade['t2_hit'] = True
                                    active_trade['sl'] = active_trade['entry']
                                if active_trade['t2_hit']:
                                    r_reached = (curr_bar['High'] - active_trade['entry']) / active_trade['risk_dist']
                                    new_sl = active_trade['entry'] + (r_reached - 1.0) * active_trade['risk_dist']
                                    active_trade['sl'] = max(active_trade['sl'], new_sl)
                                if curr_bar['Low'] <= active_trade['sl']:
                                    exit_price = active_trade['sl']
                                    exit_reason = "SL_HIT"
                        else: # PE
                            if strategy_type == 'A':
                                if not active_trade['partial_booked'] and curr_bar['Low'] <= active_trade['target1']:
                                    active_trade['partial_booked'] = True
                                    active_trade['sl'] = active_trade['entry']
                                if active_trade['partial_booked']:
                                    r_reached = (active_trade['entry'] - curr_bar['Low']) / active_trade['risk_dist']
                                    steps = int((r_reached - 1.5) / 0.5)
                                    if steps > 0:
                                        new_sl = active_trade['entry'] - (1.0 + steps * 0.5) * active_trade['risk_dist']
                                        active_trade['sl'] = min(active_trade['sl'], new_sl)
                                if curr_bar['High'] >= active_trade['sl']:
                                    exit_price = active_trade['sl']
                                    exit_reason = "SL_HIT"
                            else:
                                if not active_trade['t2_hit'] and curr_bar['Low'] <= active_trade['target2']:
                                    active_trade['t2_hit'] = True
                                    active_trade['sl'] = active_trade['entry']
                                if active_trade['t2_hit']:
                                    r_reached = (active_trade['entry'] - curr_bar['Low']) / active_trade['risk_dist']
                                    new_sl = active_trade['entry'] - (r_reached - 1.0) * active_trade['risk_dist']
                                    active_trade['sl'] = min(active_trade['sl'], new_sl)
                                if curr_bar['High'] >= active_trade['sl']:
                                    exit_price = active_trade['sl']
                                    exit_reason = "SL_HIT"
                        
                        if curr_time >= time(15, 15):
                            exit_price = curr_bar['Close']
                            exit_reason = "EOD"
                            
                        if exit_price:
                            pnl = (exit_price - active_trade['entry']) * active_trade['qty']
                            if active_trade['side'] == 'PE': pnl = -pnl
                            
                            # Adjust for partial booking in A
                            if strategy_type == 'A' and active_trade['partial_booked']:
                                # We already booked 50% at T1. The remaining 50% is at exit_price.
                                # Wait, the pnl above is for 100% at exit_price.
                                # Correct logic:
                                p1 = (active_trade['target1'] - active_trade['entry']) * (active_trade['qty'] / 2)
                                p2 = (exit_price - active_trade['entry']) * (active_trade['qty'] / 2)
                                pnl = (p1 + p2) if active_trade['side'] == 'CE' else -(p1 + p2)
                            
                            net_pnl = pnl - self.cost_per_trade
                            results.append({
                                'Date': day, 'Symbol': symbol, 'Type': active_trade['side'],
                                'Entry': active_trade['entry'], 'Exit': exit_price, 'PnL': net_pnl,
                                'Reason': exit_reason, 'Strategy': strategy_type
                            })
                            
                            if net_pnl < 0: consecutive_losses += 1
                            else: consecutive_losses = 0
                            active_trade = None
                            day_trades += 1
                            if day_trades >= 5 or consecutive_losses >= 2: break

                    if not active_trade and day_trades < 5 and consecutive_losses < 2:
                        if time(9, 45) <= curr_time <= time(14, 0):
                            df_slice = day_df.iloc[:i+1]
                            consolidations = self.engine.detect_consolidation(df_slice, config=config)
                            if consolidations:
                                print(f"  [DEBUG] Found {len(consolidations)} consolidations at {curr_time}")
                                breakout = self.engine.detect_breakout(df_slice, consolidations, i, config=config)
                                if breakout['signal']:
                                    # FADE THE BREAKOUT (Liquidity Trap)
                                    side = 'PE' if breakout['direction'] == 'CE' else 'CE'
                                    entry = day_df.iloc[i]['Close']
                                    atr = day_df.iloc[i]['ATR']
                                    if pd.isna(atr): continue
                                    risk_dist = atr * 2.5
                                    if risk_dist <= 0: continue
                                    sl = entry - risk_dist if side == 'CE' else entry + risk_dist
                                    qty = int(self.risk_amount / risk_dist)
                                    if qty > 0:
                                        active_trade = {
                                            'side': side, 'entry': entry, 'sl': sl, 'qty': qty,
                                            'risk_dist': risk_dist,
                                            'target1': entry + 1.5 * risk_dist if side == 'CE' else entry - 1.5 * risk_dist,
                                            'target2': entry + 2.0 * risk_dist if side == 'CE' else entry - 2.0 * risk_dist,
                                            'partial_booked': False, 't2_hit': False
                                        }
                                        print(f"  [SIGNAL] {day} {curr_time} {symbol} {side} at {entry}")


        return pd.DataFrame(results)

if __name__ == "__main__":
    symbols = ["RELIANCE", "ICICIBANK", "HDFCBANK", "INFY"]
    tester = StockBacktester(symbols, "data/nifty200")
    
    print("Running Strategy A (Partial Booking)...")
    res_a = tester.run_backtest(strategy_type='A')
    
    print("Running Strategy B (T2 BE + 1.0x TSL)...")
    res_b = tester.run_backtest(strategy_type='B')
    
    # Stats Calculation
    def get_stats(df):
        if df.empty: return {"Total Trades": 0, "Win Rate": "0%", "Net PnL": 0}
        wins = df[df['PnL'] > 0]
        win_rate = (len(wins) / len(df)) * 100
        return {
            "Total Trades": len(df),
            "Wins": len(wins),
            "Losses": len(df) - len(wins),
            "Win Rate": f"{win_rate:.1f}%",
            "Net PnL": f"₹{df['PnL'].sum():,.2f}",
            "Avg PnL": f"₹{df['PnL'].mean():,.2f}"
        }

    stats_a = get_stats(res_a)
    stats_b = get_stats(res_b)
    
    print("\n### RESULT A (Current Strategy - Partial Booking) ###")
    print(pd.Series(stats_a).to_string())
    
    print("\n### RESULT B (Modified - T2 BE + 1.0x TSL) ###")
    print(pd.Series(stats_b).to_string())
    
    # Save to files
    res_a.to_csv("Result_A_Trades.csv", index=False)
    res_b.to_csv("Result_B_Trades.csv", index=False)
    
    # Summary Comparison
    comparison = pd.DataFrame([stats_a, stats_b], index=["Strategy A", "Strategy B"])
    print("\n### COMPARISON SUMMARY ###")
    print(comparison)
