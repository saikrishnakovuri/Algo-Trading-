import os
import pandas as pd
import numpy as np
import argparse
import sys
from datetime import datetime, timedelta, time
from concurrent.futures import ProcessPoolExecutor

# Import engines and adapters
from modules.momentum_engine import MomentumBreakoutEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.strategy_selector import StrategySelector, StrategyResult
from modules.strategy_adapters import momentum_adapter, mean_reversion_adapter, sweep_retest_adapter, structure_strategy_adapter
from modules.regime_gate import RegimeGate

# Configuration
RISK_PER_TRADE = 5000.0
MAX_WORKERS = 8

def simulate_trade(df, entry_idx, signal):
    """Simulate a trade outcome with granular details."""
    entry = signal.entry
    sl = signal.sl
    target = signal.target1
    direction = signal.direction
    
    if entry is None or sl is None or target is None:
        return None
        
    risk = abs(entry - sl)
    if risk == 0: return None
    
    outcome = "PENDING"
    r_multiple = 0.0
    exit_price = 0.0
    exit_time = None
    
    entry_ts = df.index[entry_idx]
    session_end = entry_ts.replace(hour=15, minute=29)
    
    for j in range(entry_idx + 1, len(df)):
        current_ts = df.index[j]
        if current_ts > session_end: break
        
        high = df.iloc[j]['high']
        low = df.iloc[j]['low']
        
        if direction == "CE":
            if low <= sl:
                outcome = "LOSE"; r_multiple = -1.0; exit_price = sl; exit_time = current_ts; break
            if high >= target:
                outcome = "WIN"; r_multiple = (target - entry) / risk; exit_price = target; exit_time = current_ts; break
        else: # PE
            if high >= sl:
                outcome = "LOSE"; r_multiple = -1.0; exit_price = sl; exit_time = current_ts; break
            if low <= target:
                outcome = "WIN"; r_multiple = (entry - target) / risk; exit_price = target; exit_time = current_ts; break
                
    if outcome == "PENDING":
        day_df = df[df.index.date == entry_ts.date()]
        last_candle = day_df.iloc[-1]
        exit_price = last_candle['close']
        exit_time = day_df.index[-1]

        r_multiple = (exit_price - entry) / risk if direction == "CE" else (entry - exit_price) / risk
        outcome = "WIN" if r_multiple > 0 else "LOSE"
        
    return {
        'date': entry_ts.strftime('%Y-%m-%d'),
        'entry_time': entry_ts.strftime('%H:%M'),
        'exit_time': exit_time.strftime('%H:%M'),
        'strategy': signal.strategy_name,
        'direction': direction,
        'pnl': r_multiple * RISK_PER_TRADE,
        'r_multiple': r_multiple,
        'outcome': outcome
    }

def get_regime_series(start_date, end_date):
    """Pre-calculate regime for all timestamps in the range."""
    print("Pre-calculating market regimes...")
    nifty_path = "data/nifty50_5m.csv"
    if not os.path.exists(nifty_path): return {}
    
    df_nifty_raw = pd.read_csv(nifty_path)
    df_nifty_raw['Timestamp'] = pd.to_datetime(df_nifty_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_nifty_raw.set_index('Timestamp', inplace=True)
    df_nifty_raw.sort_index(inplace=True)
    
    start_ist = pd.Timestamp(start_date).tz_localize('Asia/Kolkata')
    end_ist = pd.Timestamp(end_date).tz_localize('Asia/Kolkata')
    warmup_start = start_ist - timedelta(days=10)
    
    df_nifty_full = df_nifty_raw[(df_nifty_raw.index >= warmup_start) & (df_nifty_raw.index <= end_ist)]
    df_nifty = df_nifty_full.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).ffill()
    
    # Speed Optimization: Only keep market hours (9:15 to 15:30)
    df_nifty = df_nifty.between_time('09:15', '15:30')
    df_nifty.columns = [c.lower() for c in df_nifty.columns]
    
    regime_gate = RegimeGate()

    regime_map = {}
    
    # Find start index for the target range
    start_idx = 0
    for i, ts in enumerate(df_nifty.index):
        if ts >= start_ist:
            start_idx = i; break
            
    total_bars = len(df_nifty) - start_idx
    print(f"Pre-calculating regimes for {total_bars} market-hour bars...")
    
    for i in range(start_idx, len(df_nifty)):
        if (i - start_idx) % 50 == 0:
            print(f"  Regime Progress: {i - start_idx}/{total_bars} bars...")
            sys.stdout.flush()
            
        ts = df_nifty.index[i]
        # Always provide enough history (e.g., last 100 bars) for classification
        df_slice = df_nifty.iloc[max(0, i-150):i+1]
        regime = regime_gate.update_regime(df_slice)
        regime_map[ts] = {
            'regime': regime,
            'allowed': {
                'MOMENTUM': regime_gate.is_strategy_allowed('MOMENTUM'),
                'MEAN_REVERSION': regime_gate.is_strategy_allowed('MEAN_REVERSION'),
                'SWEEP_RETEST': regime_gate.is_strategy_allowed('SWEEP_RETEST'),
                'STRUCTURE': regime_gate.is_strategy_allowed('STRUCTURE')
            }
        }
    return regime_map

def process_single_symbol(args):
    symbol, start_date, end_date, regime_map = args
    print(f"Analyzing {symbol}...")
    sys.stdout.flush()
    
    mom_engine = MomentumBreakoutEngine()
    mr_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    sr_engine = SweepRetestEngine(config_path="config/sweep_retest.yaml")
    struct_engine = StructureStrategyEngine(config_path="config/structure_strategy.yaml")
    selector = StrategySelector()
    selector.register("MOMENTUM", mom_engine, momentum_adapter)
    selector.register("MEAN_REVERSION", mr_engine, mean_reversion_adapter)
    selector.register("SWEEP_RETEST", sr_engine, sweep_retest_adapter)
    selector.register("STRUCTURE", struct_engine, structure_strategy_adapter)

    trades = []
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    if not os.path.exists(data_path): return []

    try:
        # Load Symbol Data
        df_raw = pd.read_csv(data_path)
        df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
        df_raw.set_index('Timestamp', inplace=True)
        df_raw.sort_index(inplace=True)

        start_ist = pd.Timestamp(start_date).tz_localize('Asia/Kolkata')
        end_ist = pd.Timestamp(end_date).tz_localize('Asia/Kolkata')
        
        warmup_start = start_ist - timedelta(days=10)
        df_full = df_raw[(df_raw.index >= warmup_start) & (df_raw.index <= end_ist)]
        df_full.columns = [c.lower() for c in df_full.columns]
        
        if df_full.empty: return []

        df = df_full.resample('5min').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
        df.columns = [c.lower() for c in df.columns]
        
        start_idx = 0

        for i, ts in enumerate(df.index):
            if ts >= start_ist:
                start_idx = i; break
        
        if start_idx < 50: start_idx = 50

        for i in range(start_idx, len(df)):
            ts = df.index[i]
            df_slice = df.iloc[:i+1]
            
            # Get Regime from pre-calculated map
            r_info = regime_map.get(ts)
            
            best_sig = selector.select_best(df_slice, symbol, df_1m=df_full[df_full.index <= ts])
            if best_sig and best_sig.confidence_pct >= 52:
                # REGIME GATE CHECK (Temporarily disabled for debugging)
                # if r_info and not r_info['allowed'].get(best_sig.strategy_name, True):
                #     continue
                
                trade = simulate_trade(df, i, best_sig)

                if trade:
                    trade['symbol'] = symbol
                    trades.append(trade)
                    
        return trades
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    start_dt = datetime(2025, 12, 1, 9, 15)
    end_dt = datetime(2025, 12, 12, 15, 30)
    
    # 12 Verified stocks with Dec 2025 history
    symbols = ['RELIANCE', 'ADANIPORTS', 'ASIANPAINT', 'AXISBANK', 'BAJFINANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'KOTAKBANK', 'MARUTI', 'SBIN', 'TCS']
    
    print("=" * 115)
    print(f"DECEMBER FINAL BACKTEST | 10 Days | {len(symbols)} Stocks | COMBINED")
    print("=" * 115 + "\n")

    regime_map = get_regime_series(start_dt, end_dt)

    args = [(s, start_dt, end_dt, regime_map) for s in symbols]
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(process_single_symbol, args))
        
    all_trades = [t for res in results for t in res]
    if not all_trades:
        print("No trades found."); return

    df = pd.DataFrame(all_trades)
    
    # 1. PER-TRADE DETAILED TABLE
    print("DETAILED TRADE LOG")
    print("-" * 115)
    header = f"{'Date':<12} | {'Symbol':<10} | {'Strat':<12} | {'Dir':<3} | {'Entry':<6} | {'Exit':<6} | {'PnL (INR)':<10} | {'RR':<5} | {'Outcome'}"
    print(header)
    print("-" * 115)
    
    for _, t in df.sort_values(['date', 'entry_time']).iterrows():
        print(f"{t['date']:<12} | {t['symbol']:<10} | {t['strategy']:<12} | {t['direction']:<3} | {t['entry_time']:<6} | {t['exit_time']:<6} | {t['pnl']:<10.2f} | {t['r_multiple']:<5.2f} | {t['outcome']}")

    # 2. PER-DAY AGGREGATED SUMMARY
    print("\n" + "=" * 115)
    print("DAILY AGGREGATED PERFORMANCE SUMMARY")
    print("-" * 115)
    print(f"{'Date':<12} | {'Strategy':<10} | {'Trades':<6} | {'Wins':<4} | {'Loss':<4} | {'Win%':<8} | {'PnL (INR)':<12} | {'Profit%'}")
    print("-" * 115)
    
    for d in sorted(df['date'].unique()):
        day_df = df[df['date'] == d]
        total = len(day_df)
        wins = len(day_df[day_df['outcome'] == 'WIN'])
        losses = len(day_df[day_df['outcome'] == 'LOSE'])
        win_rate = (wins/total*100) if total > 0 else 0
        pnl = day_df['pnl'].sum()
        profit_pct = (pnl / 1000000.0) * 100
        print(f"{d:<12} | {'COMBINED':<10} | {total:<6} | {wins:<4} | {losses:<4} | {win_rate:<8.1f} | {pnl:<12.2f} | {profit_pct:.2f}%")

    print("=" * 115)

if __name__ == "__main__":
    main()
