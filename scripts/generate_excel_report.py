import pandas as pd
import numpy as np
import os
from datetime import datetime, time, timedelta
from modules.momentum_engine import MomentumBreakoutEngine

class FinalReportGenerator:
    def __init__(self, symbols, data_dir, capital=100000.0, risk_per_trade=0.02):
        self.symbols = symbols
        self.data_dir = data_dir
        self.capital = capital
        self.risk_amount = capital * risk_per_trade
        self.engine = MomentumBreakoutEngine()
        self.cost_per_trade = 100.0
        
        self.sl_types = ['STRUCTURE', 'ATR1.5', 'ATR2.0', 'PCT1.0', 'CANDLE', 'EMA20', 'EMA50']
        self.target_types = ['RR1.5', 'RR2.0', 'SR_LEVEL', 'PARTIAL_1.0_T1.0', 'PARTIAL_1.5_T0.5', 'MEASURED', 'PIVOTS']
        self.data_cache = {}

    def preload_data(self):
        for symbol in self.symbols:
            print(f"Preloading {symbol}...")
            path = os.path.join(self.data_dir, f"{symbol}_1m.csv")
            if not os.path.exists(path): continue
            df = pd.read_csv(path)
            col = 'Timestamp' if 'Timestamp' in df.columns else 'Datetime'
            df['Datetime'] = pd.to_datetime(df[col])
            df['Datetime'] = df['Datetime'].dt.tz_localize(None)
            df.set_index('Datetime', inplace=True)
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df_5m = df.resample('5min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum',
                'EMA20': 'last', 'EMA50': 'last'
            }).dropna()
            
            # ATR pre-calc
            high, low, close = df_5m['High'], df_5m['Low'], df_5m['Close'].shift(1)
            tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
            df_5m['ATR'] = tr.rolling(14).mean()
            
            self.data_cache[symbol] = df_5m

    def run_backtest(self, sl_type, target_type, strat_name, test_days):
        trades = []
        for symbol, df in self.data_cache.items():
            for day in test_days:
                day_df = df[df.index.date == day].copy()
                if day_df.empty: continue
                
                prev_data = df[df.index.date < day]
                pivots = None
                if not prev_data.empty:
                    last_day_in_prev = prev_data.index.date[-1]
                    ld_df = prev_data[prev_data.index.date == last_day_in_prev]
                    ph, pl, pc = ld_df['High'].max(), ld_df['Low'].min(), ld_df['Close'].iloc[-1]
                    p = (ph + pl + pc) / 3
                    pivots = {'R1': 2*p - pl, 'S1': 2*p - ph}

                day_trades, consecutive_losses = 0, 0
                active_trade = None
                
                for i in range(20, len(day_df)):
                    curr_time = day_df.index[i].time()
                    curr_bar = day_df.iloc[i]

                    if active_trade:
                        exit_price, exit_reason = None, None
                        if active_trade['side'] == 'CE':
                            if target_type == 'RR1.5' and curr_bar['High'] >= active_trade['target1']:
                                exit_price, exit_reason = active_trade['target1'], "TARGET"
                            elif target_type == 'RR2.0' and curr_bar['High'] >= active_trade['target2']:
                                exit_price, exit_reason = active_trade['target2'], "TARGET"
                            elif target_type == 'SR_LEVEL' and curr_bar['High'] >= active_trade.get('sr_level', 999999):
                                exit_price, exit_reason = active_trade['sr_level'], "SR"
                            elif target_type == 'MEASURED' and curr_bar['High'] >= active_trade.get('measured', 999999):
                                exit_price, exit_reason = active_trade['measured'], "PATTERN"
                            elif target_type == 'PIVOTS' and pivots and curr_bar['High'] >= pivots['R1']:
                                exit_price, exit_reason = pivots['R1'], "PIVOT"
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
                            if not exit_price and curr_bar['Low'] <= active_trade['sl']:
                                exit_price, exit_reason = active_trade['sl'], "SL"
                        else: # PE
                            if target_type == 'RR1.5' and curr_bar['Low'] <= active_trade['target1']:
                                exit_price, exit_reason = active_trade['target1'], "TARGET"
                            elif target_type == 'RR2.0' and curr_bar['Low'] <= active_trade['target2']:
                                exit_price, exit_reason = active_trade['target2'], "TARGET"
                            elif target_type == 'SR_LEVEL' and curr_bar['Low'] <= active_trade.get('sr_level', 0):
                                exit_price, exit_reason = active_trade['sr_level'], "SR"
                            elif target_type == 'MEASURED' and curr_bar['Low'] <= active_trade.get('measured', 0):
                                exit_price, exit_reason = active_trade['measured'], "PATTERN"
                            elif pivots and target_type == 'PIVOTS' and curr_bar['Low'] <= pivots['S1']:
                                exit_price, exit_reason = pivots['S1'], "PIVOT"
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
                                exit_price, exit_reason = active_trade['sl'], "SL"

                        if not exit_price and curr_time >= time(15, 15):
                            exit_price, exit_reason = curr_bar['Close'], "EOD"
                        
                        if exit_price:
                            pnl = (exit_price - active_trade['entry']) * active_trade['qty']
                            if active_trade['side'] == 'PE': pnl = -pnl
                            if 'PARTIAL' in target_type and active_trade['partial_booked']:
                                t1_r = 1.0 if '1.0' in target_type else 1.5
                                t1_px = active_trade['entry'] + t1_r*active_trade['risk_dist'] if active_trade['side'] == 'CE' else active_trade['entry'] - t1_r*active_trade['risk_dist']
                                pnl = ((t1_px - active_trade['entry']) * active_trade['qty']/2) + ((exit_price - active_trade['entry']) * active_trade['qty']/2)
                                if active_trade['side'] == 'PE': pnl = -((t1_px - active_trade['entry']) * active_trade['qty']/2) - ((exit_price - active_trade['entry']) * active_trade['qty']/2)
                            
                            net_pnl = pnl - self.cost_per_trade
                            trades.append({'Strategy': strat_name, 'SL': sl_type, 'Target': target_type, 'PnL': net_pnl, 'Win': 1 if net_pnl > 0 else 0})
                            if net_pnl < 0: consecutive_losses += 1
                            else: consecutive_losses = 0
                            active_trade = None
                            day_trades += 1
                            if day_trades >= 5 or consecutive_losses >= 2: break

                    if not active_trade and day_trades < 5 and consecutive_losses < 2:
                        if time(9, 45) <= curr_time <= time(14, 0):
                            df_slice = day_df.iloc[:i+1]
                            breakout = self.engine.detect_breakout(df_slice, self.engine.detect_consolidation(df_slice, config={'consolidation_bars': 4}), i, config={'volume_breakout_ratio': 1.1})
                            if breakout['signal']:
                                side = 'PE' if breakout['direction'] == 'CE' else 'CE'
                                entry, atr = day_df.iloc[i]['Close'], day_df.iloc[i]['ATR']
                                if pd.isna(atr): continue
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
                                    active_trade = {
                                        'side': side, 'entry': entry, 'sl': sl, 'qty': qty, 'risk_dist': risk_dist,
                                        'target1': entry + 1.5*risk_dist if side == 'CE' else entry - 1.5*risk_dist,
                                        'target2': entry + 2.0*risk_dist if side == 'CE' else entry - 2.0*risk_dist,
                                        'partial_booked': False
                                    }
        return pd.DataFrame(trades)

if __name__ == "__main__":
    symbols = ["RELIANCE", "ICICIBANK", "HDFCBANK", "INFY"]
    data_dir = "data/angel_historical"
    gen = FinalReportGenerator(symbols, data_dir)
    gen.preload_data()
    
    ref_df = pd.read_csv(os.path.join(data_dir, "RELIANCE_1m.csv"))
    all_days = sorted(pd.to_datetime(ref_df['Timestamp']).dt.date.unique())
    
    all_window_summaries = []
    for w in range(3):
        start_idx = w * 10
        test_days = all_days[start_idx : start_idx + 10]
        print(f"Processing Window {w+1}...")
        window_trades = []
        strategy_counter = 1
        for sl in gen.sl_types:
            for target in gen.target_types:
                strat_name = f"C{strategy_counter}"
                res = gen.run_backtest(sl, target, strat_name, test_days)
                if not res.empty: window_trades.append(res)
                strategy_counter += 1
        if window_trades:
            df_w = pd.concat(window_trades)
            summary = df_w.groupby(['Strategy', 'SL', 'Target']).agg({'PnL': 'sum', 'Win': 'mean', 'Strategy': 'count'}).rename(columns={'Win': 'WinRate', 'Strategy': 'Trades'}).reset_index()
            summary['Window'] = f"Window {w+1}"
            all_window_summaries.append(summary)
final_df = pd.concat(all_window_summaries)

# Use pivot_table to handle any missing strategy-window combinations with 0 PnL
pivoted = final_df.pivot_table(index=['Strategy', 'SL', 'Target'], columns='Window', values='PnL', aggfunc='sum', fill_value=0)

# Calculate Overall Stats (Total PnL across 30 days)
overall = final_df.groupby(['Strategy', 'SL', 'Target']).agg({
    'PnL': 'sum', 
    'Trades': 'sum',
    'WinRate': 'mean' # Average WinRate across windows
}).sort_values('PnL', ascending=False)

report = overall.join(pivoted).reset_index()
report.to_excel("Full_30Day_Backtest_Results.xlsx", index=False)
print("\n✅ Report saved to Full_30Day_Backtest_Results.xlsx")
print(f"Top 5 Overall Winners:\n", report.head(5))

