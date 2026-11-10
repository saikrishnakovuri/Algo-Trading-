
import sys, os
import pandas as pd
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())

from modules.options.signal_adapter import IndexLiquidityTrapAdapter

def run_quick_backtest():
    # Load today's data
    df = pd.read_csv("data/nifty50_5m.csv")
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df.set_index('Datetime', inplace=True)
    
    # Filter for today (May 5, 2026)
    today = "2026-05-05"
    df_today = df.loc[today].copy()
    
    if df_today.empty:
        print("No data found for today!")
        return

    # Prepare columns for adapter
    df_today.columns = [c.lower() for c in df_today.columns]
    
    # Add synthetic volume if zero
    if df_today['volume'].sum() == 0:
        df_today['volume'] = ((df_today['high'] - df_today['low']) / df_today['close'] * 100000).clip(lower=1000).astype(int)

    # Add indicators
    df_today['vwap'] = (df_today['close'] * df_today['volume']).cumsum() / df_today['volume'].cumsum()
    df_today['ema20'] = df_today['close'].ewm(span=20).mean()
    df_today['atr'] = (df_today['high'] - df_today['low']).rolling(14).mean()

    adapter = IndexLiquidityTrapAdapter()
    vix = 12.5 # Approximate today's VIX
    
    trades = []
    active_trade = None
    
    print(f"--- NIFTY Quick Backtest (Today: {today}) ---")
    
    for i in range(10, len(df_today)):
        sub_df = df_today.iloc[:i+1]
        current_bar = df_today.iloc[i]
        timestamp = df_today.index[i]
        
        # 1. Check Exits if in trade
        if active_trade:
            # (Exits logic remains the same)
            if current_bar['low'] <= active_trade['sl']:
                active_trade['exit_price'] = active_trade['sl']
                active_trade['exit_time'] = timestamp
                active_trade['reason'] = "SL"
                trades.append(active_trade)
                active_trade = None
            elif current_bar['high'] >= active_trade['tp']:
                active_trade['exit_price'] = active_trade['tp']
                active_trade['exit_time'] = timestamp
                active_trade['reason'] = "TP"
                trades.append(active_trade)
                active_trade = None
            elif i == len(df_today) - 1:
                active_trade['exit_price'] = current_bar['close']
                active_trade['exit_time'] = timestamp
                active_trade['reason'] = "EOD"
                trades.append(active_trade)
                active_trade = None
            continue

        # 2. Check Entry Signals
        sig = adapter.evaluate_signal(sub_df, "NIFTY", vix, 1.0, {}, False)
        
        # Log periodically
        if i % 10 == 0:
            vwap = sub_df['vwap'].iloc[-1]
            print(f"[{timestamp.time()}] Price: {current_bar['close']:.2f} | VWAP: {vwap:.2f} | ATR: {current_bar['atr']:.2f}")

        if sig:
            # Simple simulation: use sl/tp from signal or ATR based
            sl_dist = 2 * current_bar['atr'] if not pd.isna(current_bar['atr']) else current_bar['close'] * 0.005
            active_trade = {
                'symbol': "NIFTY",
                'direction': sig['direction'],
                'entry_price': current_bar['close'],
                'entry_time': timestamp,
                'strategy': sig['strategy'],
                'sl': current_bar['close'] - sl_dist if sig['direction'] == 'BUY' else current_bar['close'] + sl_dist,
                'tp': current_bar['close'] + (2 * sl_dist) if sig['direction'] == 'BUY' else current_bar['close'] - (2 * sl_dist)
            }
            print(f"[SIGNAL] {timestamp.time()} | {sig['direction']} | {sig['strategy']} @ {active_trade['entry_price']:.2f}")

    # Results
    if not trades:
        print("No trades taken today.")
    else:
        total_pnl = 0
        print("\n--- Trade Log ---")
        for t in trades:
            pnl = (t['exit_price'] - t['entry_price']) if t['direction'] == 'BUY' else (t['entry_price'] - t['exit_price'])
            total_pnl += pnl
            print(f"{t['entry_time'].time()} -> {t['exit_time'].time()} | {t['direction']} | {t['reason']} | PnL: {pnl:.2f}")
        
        print(f"\nTotal Points: {total_pnl:.2f}")
        print(f"Total ₹ (1 Lot/50 qty): ₹{total_pnl * 50:.2f}")

if __name__ == "__main__":
    run_quick_backtest()
