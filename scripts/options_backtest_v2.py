import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

from modules.momentum_engine import MomentumBreakoutEngine
from modules.indicator_engine import IndicatorEngine
from modules.options.signal_adapter import IndexLiquidityTrapAdapter

# --- Constants & Config ---
INITIAL_CAPITAL = 1000000.0
LOT_SIZE = 25 # NIFTY
RISK_PER_TRADE = 20000.0 # 2% of 10L

class IndexOptionsBacktest:
    def __init__(self):
        self.momentum_engine = MomentumBreakoutEngine()
        self.ie = IndicatorEngine()
        
    def get_price_consolidations(self, df):
        """Volume-agnostic consolidation detection for Index Spot data."""
        # Using a fixed ATR threshold for indices
        atr_series = self.ie.calculate_atr(df)
        rolling_high = df['High'].rolling(20).max()
        rolling_low = df['Low'].rolling(20).min()
        
        consolidations = []
        for i in range(20, len(df)):
            range_val = rolling_high.iloc[i-1] - rolling_low.iloc[i-1]
            # If range < 3x ATR, it's a tight zone
            if range_val < (atr_series.iloc[i-1] * 3.5):
                consolidations.append({
                    'high': rolling_high.iloc[i-1],
                    'low': rolling_low.iloc[i-1],
                    'end_idx': i - 1,
                    'volume_avg': 1.0 # Force neutral volume
                })
        return consolidations

    def detect_price_breakout(self, df, consolidations, i):
        """Price-Action-Only breakout detection."""
        curr = df.iloc[i]
        # Range expansion check (>1.5x ATR)
        atr = self.ie.calculate_atr(df).iloc[i]
        candle_range = curr['High'] - curr['Low']
        
        for consol in [c for c in consolidations if i - c['end_idx'] < 10]:
            # BULLISH BREAKOUT
            if curr['Close'] > consol['high'] and candle_range > (atr * 1.2):
                return {'signal': True, 'direction': 'CE', 'entry': curr['Close'], 'level_swept': consol['high'], 'score': 8.0}
            # BEARISH BREAKOUT
            if curr['Close'] < consol['low'] and candle_range > (atr * 1.2):
                return {'signal': True, 'direction': 'PE', 'entry': curr['Close'], 'level_swept': consol['low'], 'score': 8.0}
        return {'signal': False}

def calc_options_costs(qty, entry_p, exit_p):
    brokerage = 40.0
    sell_premium_val = qty * exit_p
    stt = 0.000625 * sell_premium_val
    exchange = 0.0005 * (qty * (entry_p + exit_p))
    return brokerage + stt + exchange + 10.0 # + taxes

def run_sim():
    print("Running V2 Options Backtest (Price-Action Only)...")
    df = pd.read_csv("data/nifty50_5m.csv")
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df.set_index('Timestamp', inplace=True); df.sort_index(inplace=True)
    
    vix_df = pd.read_csv("data/indiavix_5m.csv")
    vix_df['Timestamp'] = pd.to_datetime(vix_df['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    vix_df.set_index('Timestamp', inplace=True); vix_df.sort_index(inplace=True)
    
    engine = IndexOptionsBacktest()
    consolidations = engine.get_price_consolidations(df)
    
    trades = []
    equity = INITIAL_CAPITAL
    
    # Oct 2025 - Apr 2026
    for i in range(100, len(df)-20):
        ts = df.index[i]
        if ts.time() > time(13, 30): continue
        
        res = engine.detect_price_breakout(df, consolidations, i)
        if res['signal']:
            # FADE THE SIGNAL
            direction = 'PE' if res['direction'] == 'CE' else 'CE'
            entry_spot = res['entry']
            
            # Premium Estimation
            vix = vix_df.iloc[vix_df.index.get_loc(ts, method='nearest')]['Close']
            entry_p = entry_spot * 0.006 * (vix/15.0)
            target_p = entry_p * 1.5
            sl_p = entry_p * 0.7
            
            qty = int(RISK_PER_TRADE / entry_p)
            if qty < 1: qty = 1
            
            exit_p = entry_p; exit_reason = "EOD"
            for j in range(i+1, min(i+20, len(df))): # 90 min limit
                curr = df.iloc[j]
                spot_move = (curr['Close'] - entry_spot) / entry_spot
                if direction == 'PE': spot_move *= -1.0
                
                # Synthetic Premium Change
                curr_p = entry_p + (0.5 * spot_move * entry_spot) + (0.5 * 0.002 * (spot_move * entry_spot)**2) - (0.5 * (j-i)/12)
                
                if curr_p >= target_p: exit_p = target_p; exit_reason = "TP"; break
                if curr_p <= sl_p: exit_p = sl_p; exit_reason = "SL"; break
                
                # Structural
                struct_hit = (curr['Close'] > res['level_swept']) if direction == 'PE' else (curr['Close'] < res['level_swept'])
                if struct_hit: exit_p = curr_p; exit_reason = "STRUCT"; break
            
            costs = calc_options_costs(qty * LOT_SIZE, entry_p, exit_p)
            net_pnl = ((exit_p - entry_p) * qty * LOT_SIZE) - costs
            equity += net_pnl
            trades.append({'date': ts.date(), 'net': net_pnl, 'reason': exit_reason})
            
    df_results = pd.DataFrame(trades)
    print(f"\n--- FINAL OPTIONS SUMMARY (Price Action Logic) ---")
    print(f"Total Trades: {len(df_results)}")
    print(f"Win Rate: {(df_results['net']>0).sum()/len(df_results)*100:.1f}%")
    print(f"Final Equity: INR {equity:,.2f}")
    print(f"Total Return: {((equity/INITIAL_CAPITAL)-1)*100:.2f}%")
    
    # Monthly
    df_results['month'] = pd.to_datetime(df_results['date']).dt.strftime('%Y-%m')
    print("\nMonthly P&L:")
    print(df_results.groupby('month')['net'].sum())

if __name__ == "__main__":
    run_sim()
