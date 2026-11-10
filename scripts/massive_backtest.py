import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta

from modules.momentum_engine import MomentumBreakoutEngine

class MassiveBacktester:
    def __init__(self, symbols, data_dir, capital=100000.0, risk_per_trade=0.02):
        self.symbols = symbols
        self.data_dir = data_dir
        self.capital = capital
        self.risk_amount = capital * risk_per_trade
        self.engine = MomentumBreakoutEngine()
        self.cost_per_trade = 100.0

    def load_data(self, symbol):
        path = os.path.join(self.data_dir, f"{symbol}_1m.csv")
        if not os.path.exists(path): return None
        df = pd.read_csv(path)
        # Handle 'Timestamp' column in angel_historical
        col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
        df['Datetime'] = pd.to_datetime(df[col])
        df['Datetime'] = df['Datetime'].dt.tz_localize(None)
        df.set_index('Datetime', inplace=True)
        
        # Add Technicals
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        df_5m = df.resample('5min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum',
            'EMA20': 'last', 'EMA50': 'last'
        }).dropna()
        return df_5m

    def run_all_strategies(self, start_day_idx=0):
        sl_types = ['STRUCTURE', 'ATR1.5', 'ATR2.0', 'PCT1.0', 'CANDLE', 'EMA20', 'EMA50']
        target_types = ['RR1.5', 'RR2.0', 'SR_LEVEL', 'PARTIAL_1.0_T1.0', 'PARTIAL_1.5_T0.5', 'MEASURED', 'PIVOTS']
        
        all_results = []
        strategy_counter = 1
        
        for sl_type in sl_types:
            for target_type in target_types:
                strat_name = f"C{strategy_counter}"
                res = self.run_backtest(sl_type, target_type, strat_name, start_day_idx)
                all_results.append(res)
                strategy_counter += 1
        
        return pd.concat(all_results) if all_results else pd.DataFrame()

    def run_backtest(self, sl_type, target_type, strat_name, start_day_idx):
        trades = []
        for symbol in self.symbols:
            df = self.load_data(symbol)
            if df is None: continue
            
            df['Date'] = df.index.date
            days = sorted(df['Date'].unique())
            
            # Select the 10-day window
            if start_day_idx >= len(days): continue
            test_days = days[start_day_idx : start_day_idx + 10]
            
            for day in test_days:
                day_df = df[df['Date'] == day].copy()
                
                # Pre-calculate Pivots for the day
                prev_data = df[df.index.date < day]
                pivots = None
                if not prev_data.empty:
                    last_day_in_prev = prev_data.index.date[-1]
                    last_day_df = prev_data[prev_data.index.date == last_day_in_prev]
                    ph = last_day_df['High'].max()
                    pl = last_day_df['Low'].min()
                    pc = last_day_df['Close'].iloc[-1]
                    p = (ph + pl + pc) / 3
                    pivots = {'R1': 2*p - pl, 'S1': 2*p - ph}

                day_trades = 0
                consecutive_losses = 0
                
                high = day_df['High']; low = day_df['Low']; close = day_df['Close'].shift(1)
                tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
                day_df['ATR'] = tr.rolling(14).mean()
                
                active_trade = None
                
                for i in range(20, len(day_df)):
                    curr_time = day_df.index[i].time()
                    curr_bar = day_df.iloc[i]

                    if active_trade:
                        exit_price = None
                        exit_reason = None
                        
                        # 1. Update Trailing / Partials
                        if active_trade['side'] == 'CE':
                            # TARGET LOGIC
                            if target_type == 'RR1.5' and curr_bar['High'] >= active_trade['target1']:
                                exit_price = active_trade['target1']; exit_reason = "TARGET_HIT"
                            elif target_type == 'RR2.0' and curr_bar['High'] >= active_trade['target2']:
                                exit_price = active_trade['target2']; exit_reason = "TARGET_HIT"
                            elif target_type == 'SR_LEVEL' and curr_bar['High'] >= active_trade.get('sr_level', 999999):
                                exit_price = active_trade['sr_level']; exit_reason = "SR_HIT"
                            elif target_type == 'MEASURED' and curr_bar['High'] >= active_trade.get('measured', 999999):
                                exit_price = active_trade['measured']; exit_reason = "PATTERN_HIT"
                            elif target_type == 'PIVOTS' and pivots and curr_bar['High'] >= pivots['R1']:
                                exit_price = pivots['R1']; exit_reason = "PIVOT_R1"
                            
                            # PARTIALS
                            elif 'PARTIAL' in target_type:
                                t1_r = 1.0 if '1.0' in target_type else 1.5
                                trail_r = 1.0 if 'T1.0' in target_type else 0.5
                                
                                if not active_trade['partial_booked'] and curr_bar['High'] >= active_trade['entry'] + t1_r * active_trade['risk_dist']:
                                    active_trade['partial_booked'] = True
                                    active_trade['sl'] = active_trade['entry']
                                
                                if active_trade['partial_booked']:
                                    r_reached = (curr_bar['High'] - active_trade['entry']) / active_trade['risk_dist']
                                    steps = int((r_reached - t1_r) / trail_r)
                                    if steps > 0:
                                        new_sl = active_trade['entry'] + (t1_r - (1.0 - trail_r) + steps * trail_r) * active_trade['risk_dist']
                                        active_trade['sl'] = max(active_trade['sl'], new_sl)
                            
                            # SL CHECK
                            if not exit_price and curr_bar['Low'] <= active_trade['sl']:
                                exit_price = active_trade['sl']; exit_reason = "SL_HIT"
                        
                        else: # PE
                            if target_type == 'RR1.5' and curr_bar['Low'] <= active_trade['target1']:
                                exit_price = active_trade['target1']; exit_reason = "TARGET_HIT"
                            elif target_type == 'RR2.0' and curr_bar['Low'] <= active_trade['target2']:
                                exit_price = active_trade['target2']; exit_reason = "TARGET_HIT"
                            elif target_type == 'SR_LEVEL' and curr_bar['Low'] <= active_trade.get('sr_level', 0):
                                exit_price = active_trade['sr_level']; exit_reason = "SR_HIT"
                            elif target_type == 'MEASURED' and curr_bar['Low'] <= active_trade.get('measured', 0):
                                exit_price = active_trade['measured']; exit_reason = "PATTERN_HIT"
                            elif pivots and target_type == 'PIVOTS' and curr_bar['Low'] <= pivots['S1']:
                                exit_price = pivots['S1']; exit_reason = "PIVOT_S1"
                            
                            elif 'PARTIAL' in target_type:
                                t1_r = 1.0 if '1.0' in target_type else 1.5
                                trail_r = 1.0 if 'T1.0' in target_type else 0.5
                                if not active_trade['partial_booked'] and curr_bar['Low'] <= active_trade['entry'] - t1_r * active_trade['risk_dist']:
                                    active_trade['partial_booked'] = True
                                    active_trade['sl'] = active_trade['entry']
                                if active_trade['partial_booked']:
                                    r_reached = (active_trade['entry'] - curr_bar['Low']) / active_trade['risk_dist']
                                    steps = int((r_reached - t1_r) / trail_r)
                                    if steps > 0:
                                        new_sl = active_trade['entry'] - (t1_r - (1.0 - trail_r) + steps * trail_r) * active_trade['risk_dist']
                                        active_trade['sl'] = min(active_trade['sl'], new_sl)
                            
                            if not exit_price and curr_bar['High'] >= active_trade['sl']:
                                exit_price = active_trade['sl']; exit_reason = "SL_HIT"

                        if not exit_price and curr_time >= time(15, 15):
                            exit_price = curr_bar['Close']; exit_reason = "EOD"
                        
                        if exit_price:
                            pnl = (exit_price - active_trade['entry']) * active_trade['qty']
                            if active_trade['side'] == 'PE': pnl = -pnl
                            
                            if 'PARTIAL' in target_type and active_trade['partial_booked']:
                                t1_r = 1.0 if '1.0' in target_type else 1.5
                                t1_price = active_trade['entry'] + t1_r * active_trade['risk_dist'] if active_trade['side'] == 'CE' else active_trade['entry'] - t1_r * active_trade['risk_dist']
                                p1 = (t1_price - active_trade['entry']) * (active_trade['qty'] / 2)
                                p2 = (exit_price - active_trade['entry']) * (active_trade['qty'] / 2)
                                pnl = (p1 + p2) if active_trade['side'] == 'CE' else -(p1 + p2)
                            
                            net_pnl = pnl - self.cost_per_trade
                            trades.append({'Strategy': strat_name, 'PnL': net_pnl, 'Win': 1 if net_pnl > 0 else 0})
                            
                            if net_pnl < 0: consecutive_losses += 1
                            else: consecutive_losses = 0
                            active_trade = None
                            day_trades += 1
                            if day_trades >= 5 or consecutive_losses >= 2: break

                    # SIGNAL
                    if not active_trade and day_trades < 5 and consecutive_losses < 2:
                        if time(9, 45) <= curr_time <= time(14, 0):
                            df_slice = day_df.iloc[:i+1]
                            consolidations = self.engine.detect_consolidation(df_slice, config={'consolidation_bars': 4})
                            if consolidations:
                                breakout = self.engine.detect_breakout(df_slice, consolidations, i, config={'volume_breakout_ratio': 1.1})
                                if breakout['signal']:
                                    side = 'PE' if breakout['direction'] == 'CE' else 'CE'
                                    entry = day_df.iloc[i]['Close']
                                    atr = day_df.iloc[i]['ATR']
                                    if pd.isna(atr): continue
                                    
                                    # SL CALCULATION
                                    if sl_type == 'STRUCTURE': sl = breakout['sl']
                                    elif sl_type == 'ATR1.5': sl = entry - 1.5*atr if side == 'CE' else entry + 1.5*atr
                                    elif sl_type == 'ATR2.0': sl = entry - 2.0*atr if side == 'CE' else entry + 2.0*atr
                                    elif sl_type == 'PCT1.0': sl = entry * 0.99 if side == 'CE' else entry * 1.01
                                    elif sl_type == 'CANDLE': sl = day_df.iloc[i]['Low'] if side == 'CE' else day_df.iloc[i]['High']
                                    elif sl_type == 'EMA20': sl = day_df.iloc[i]['EMA20']
                                    elif sl_type == 'EMA50': sl = day_df.iloc[i]['EMA50']
                                    
                                    risk_dist = abs(entry - sl)
                                    if risk_dist <= 0: continue
                                    qty = int(self.risk_amount / risk_dist)
                                    
                                    if qty > 0:
                                        # Next SR
                                        next_sr = None
                                        if consolidations:
                                            if side == 'CE':
                                                higher = [c['high'] for c in consolidations if c['high'] > entry + 5]
                                                next_sr = min(higher) if higher else entry + 2*risk_dist
                                            else:
                                                lower = [c['low'] for c in consolidations if c['low'] < entry - 5]
                                                next_sr = max(lower) if lower else entry - 2*risk_dist
                                        
                                        active_trade = {
                                            'side': side, 'entry': entry, 'sl': sl, 'qty': qty,
                                            'risk_dist': risk_dist,
                                            'target1': entry + 1.5 * risk_dist if side == 'CE' else entry - 1.5 * risk_dist,
                                            'target2': entry + 2.0 * risk_dist if side == 'CE' else entry - 2.0 * risk_dist,
                                            'sr_level': next_sr,
                                            'measured': entry + (breakout['consolidation']['high'] - breakout['consolidation']['low']) if side == 'CE' else entry - (breakout['consolidation']['high'] - breakout['consolidation']['low']),
                                            'partial_booked': False
                                        }

        return pd.DataFrame(trades)

def get_summary(all_trades):
    if all_trades.empty: return pd.DataFrame()
    summary = all_trades.groupby('Strategy').agg({
        'PnL': 'sum',
        'Win': 'mean',
        'Strategy': 'count'
    }).rename(columns={'Win': 'WinRate', 'Strategy': 'Trades'})
    summary['WinRate'] = (summary['WinRate'] * 100).round(1).astype(str) + '%'
    return summary.sort_values('PnL', ascending=False)

if __name__ == "__main__":
    symbols = ["RELIANCE", "ICICIBANK", "HDFCBANK", "INFY"]
    data_dir = "data/angel_historical"
    tester = MassiveBacktester(symbols, data_dir)
    
    # Get 3 windows of 10 days
    summaries = []
    for run in range(3):
        start_idx = run * 10
        print(f"\n🚀 Running 10-day Window #{run+1} (Start Day Index: {start_idx})...")
        trades = tester.run_all_strategies(start_idx)
        summary = get_summary(trades)
        summaries.append(summary)
        
        if not summary.empty:
            print(f"Top 5 for Window #{run+1}:")
            print(summary.head(5))
        else:
            print(f"No trades found in Window #{run+1}.")

    # Comparison Table
    if summaries[0] is not None:
        final_comp = pd.DataFrame()
        for i, s in enumerate(summaries):
            if not s.empty:
                top_10 = s.head(10).index.tolist()
                final_comp[f'Window_{i+1}'] = top_10
        
        print("\n### CONSISTENCY COMPARISON (TOP 10 STRATEGIES) ###")
        print(final_comp)
        final_comp.to_csv("Consistency_Comparison.csv")
