import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from modules.mean_reversion_engine import MeanReversionEngine

def run_diagnostic(symbol="RELIANCE"):
    engine = MeanReversionEngine()
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    
    if not os.path.exists(data_path):
        print(f"Data not found for {symbol}")
        return

    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    df_raw.sort_index(inplace=True)

    periods = {
        "April 2026": ("2026-04-01", "2026-04-12"),
        "Dec 2025": ("2025-12-01", "2025-12-12")
    }

    for name, (start, end) in periods.items():
        print(f"\n--- Diagnosing {name} ---")
        start_ist = pd.Timestamp(start).tz_localize('Asia/Kolkata')
        end_ist = pd.Timestamp(end).tz_localize('Asia/Kolkata')
        
        warmup_start = start_ist - timedelta(days=10)
        df_period = df_raw[(df_raw.index >= warmup_start) & (df_raw.index <= end_ist)]
        
        if df_period.empty:
            print(f"No data for {name}")
            continue

        df_5m = df_period.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        df_5m = df_5m.between_time('09:15', '15:30')
        
        # Total bars in target range
        target_bars = df_5m[df_5m.index >= start_ist]
        print(f"Total 5m Bars: {len(target_bars)}")

        # 1. RSI Extremes
        df_ind = engine._compute_indicators(df_5m)
        df_target = df_ind[df_ind.index >= start_ist]
        
        oversold = (df_target['rsi'] <= engine.rsi_oversold).sum()
        overbought = (df_target['rsi'] >= engine.rsi_overbought).sum()
        print(f"RSI Extremes: OS(<={engine.rsi_oversold}): {oversold}, OB(>={engine.rsi_overbought}): {overbought}")

        # 2. Tracking signal lifecycle
        counts = {
            'total_steps': 0,
            'passed_anti_trend': 0,
            'fired_raw_signal': 0,
            'passed_score_6': 0,
            'passed_score_12': 0,
            'blocked_by_conf_60': 0,
            'blocked_by_min_sl': 0
        }
        
        settings = {
            'rsi_oversold': engine.rsi_oversold,
            'rsi_overbought': engine.rsi_overbought,
            'sl_atr_mult': engine.sl_atr_mult,
            'min_score': engine.min_score
        }

        for idx in range(len(df_ind)):
            if df_ind.index[idx] < start_ist: continue
            
            counts['total_steps'] += 1
            row = df_ind.iloc[idx]
            
            trend_ok, _ = engine._check_anti_trend_filter(row)
            if not trend_ok: continue
            counts['passed_anti_trend'] += 1

            bb = engine._check_bb_reversion(row, settings)
            vwap = engine._check_vwap_reversion(row, settings)
            rsi = engine._check_rsi_extreme(row, settings)
            
            fired = [s for s in [bb, vwap, rsi] if s is not None]
            if not fired: continue
            counts['fired_raw_signal'] += 1
            
            direction = None
            long_votes = sum(1 for s in fired if s['direction'] == 'LONG')
            short_votes = sum(1 for s in fired if s['direction'] == 'SHORT')
            if long_votes > short_votes: direction = 'LONG'
            elif short_votes > long_votes: direction = 'SHORT'
            if not direction: continue
            
            aligned = [s for s in fired if s['direction'] == direction]
            base_score = sum(s['score'] for s in aligned)
            bonus_score, _ = engine._compute_bonuses(row, df_ind, idx)
            total_score = base_score + bonus_score
            
            if total_score >= 6:
                counts['passed_score_6'] += 1
                confidence = (total_score / 19.0) * 100
                if confidence < 60:
                    counts['blocked_by_conf_60'] += 1
                else:
                    counts['passed_score_12'] += 1

            # Check SL
            atr = row.get('atr', 1.0)
            sl_dist = settings['sl_atr_mult'] * atr
            if sl_dist < 0.5:
                counts['blocked_by_min_sl'] += 1

        print(f"Pipeline Counts: {counts}")
        
        # 3. SL Check
        atr_avg = df_target['atr'].mean()
        print(f"Avg ATR: {atr_avg:.2f}")
        print(f"Default SL Distance (0.5x ATR): {0.5 * atr_avg:.2f}")

if __name__ == "__main__":
    run_diagnostic()
