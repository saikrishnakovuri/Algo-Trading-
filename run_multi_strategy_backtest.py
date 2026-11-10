#!/usr/bin/env python3
"""
Multi-Strategy Backtest — reads from data/cache/ only. No API calls.
"""
import argparse
import pandas as pd
from modules.cached_data_loader import CachedDataLoader
from modules.strategy_selector import StrategySelector
from modules.strategy_adapters import momentum_adapter, candlestick_adapter, mean_reversion_adapter
from modules.momentum_engine import MomentumBreakoutEngine
from modules.candlestick_engine import CandlestickEngine
from modules.mean_reversion_engine import MeanReversionEngine

def execute_trade(df, idx, sig, interval_min=5):
    entry, sl, target = sig.entry, sig.sl, sig.target1
    d = sig.direction
    if not all([entry, sl, target]): return None
    dist = abs(entry - sl)
    if dist == 0: return None
    
    hit_be = False
    rr_trig = entry + dist if d == 'CE' else entry - dist
    
    for j in range(idx+1, min(idx+200, len(df))):
        mins = (j - idx) * interval_min
        h, l, c = df.iloc[j]['High'], df.iloc[j]['Low'], df.iloc[j]['Close']
        cur_r = ((c - entry) if d == 'CE' else (entry - c)) / dist
        
        if mins >= 20 and cur_r < 0:
            return trade_result(sig, entry, c, "TIME_CUT_20M", d)
        if mins >= 45 and not hit_be:
            if cur_r <= 0:
                return trade_result(sig, entry, c, "TIME_CUT_45M", d)
            elif cur_r < 0.5:
                sl, hit_be = entry, True
        if mins >= 90 and cur_r < 1.0:
            return trade_result(sig, entry, c, "TIME_CUT_90M", d)
        if mins >= 150:
            return trade_result(sig, entry, c, "TIME_CUT_EOD", d)
        
        if not hit_be:
            if (d=='CE' and h>=rr_trig) or (d=='PE' and l<=rr_trig):
                sl, hit_be = entry, True
        
        if d == 'CE':
            if l <= sl: return trade_result(sig, entry, sl, "BE" if hit_be else "SL", d)
            if h >= target: return trade_result(sig, entry, target, "TARGET", d)
        else:
            if h >= sl: return trade_result(sig, entry, sl, "BE" if hit_be else "SL", d)
            if l <= target: return trade_result(sig, entry, target, "TARGET", d)
    
    return trade_result(sig, entry, df.iloc[min(idx+199, len(df)-1)]['Close'], "EXPIRED", d)

def trade_result(sig, entry, exit_p, outcome, d):
    qty = max(1, int(100000 / entry))
    pnl = ((exit_p - entry) if d == 'CE' else (entry - exit_p)) * qty
    return {
        'symbol': '', 'strategy': sig.strategy_name, 
        'setup': sig.setup_type, 'direction': d,
        'score': sig.score, 'confidence': sig.confidence_pct,
        'entry': round(entry,2), 'sl': round(sig.sl,2),
        'target': round(sig.target1,2), 'exit': round(exit_p,2),
        'outcome': outcome, 'pnl': round(pnl,2),
        'reasons': '|'.join(sig.reasons[:3])
    }

def show(label, df):
    t = len(df); w = len(df[df['pnl']>0]); l = t - w
    pnl = df['pnl'].sum()
    aw = df[df['pnl']>0]['pnl'].mean() if w else 0
    al = abs(df[df['pnl']<0]['pnl'].mean()) if l else 1
    rr = aw/al if al else 0; wp = w/t*100 if t else 0
    exp = (wp/100*rr) - ((100-wp)/100) if t else 0
    oc = df['outcome'].value_counts().to_dict()
    print(f"\n{'='*55}\n{label}\n{'='*55}")
    print(f"  Trades:{t} Win%:{wp:.1f} RR:{rr:.2f} Exp:{exp:.3f}R P&L:{pnl:,.0f}")
    print(f"  Outcomes: {oc}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=None)
    p.add_argument("--interval", default="5m")
    p.add_argument("--max-symbols", type=int, default=50)
    p.add_argument("--step", type=int, default=3)
    a = p.parse_args()
    
    loader = CachedDataLoader()
    sel = StrategySelector()
    
    # ══════ REGISTER STRATEGIES ══════
    # OPTION 1: Momentum (ALREADY EXISTS)
    sel.register("MOMENTUM", MomentumBreakoutEngine(), momentum_adapter)
    
    # OPTION 2: Candlestick Pattern Recognition
    candlestick_engine = CandlestickEngine(config_path="config/candlestick.yaml")
    sel.register("CANDLESTICK", candlestick_engine, candlestick_adapter)
    
    # OPTION 3: Mean Reversion
    mean_reversion_engine = MeanReversionEngine(config_path="config/mean_reversion.yaml")
    sel.register("MEAN_REVERSION", mean_reversion_engine, mean_reversion_adapter)
    # ═════════════════════════════════
    
    syms = a.symbols or loader.get_available_symbols(a.interval)[:a.max_symbols]
    print(f"Scanning {len(syms)} symbols from cache (step={a.step})...")
    
    trades = []
    for i, sym in enumerate(syms):
        df = loader.load(sym, a.interval)
        if df is None or len(df) < 50: continue
        n = 0
        for j in range(30, len(df), a.step):
            best = sel.select_best(df.iloc[:j+1], sym)
            if best:
                tr = execute_trade(df, j, best, 5 if '5' in a.interval else 1)
                if tr: tr['symbol'] = sym; trades.append(tr); n += 1
        print(f"  [{i+1}/{len(syms)}] {sym}: {len(df)} bars → {n} trades")
    
    if not trades:
        print("\nNo trades triggered."); return
    
    dt = pd.DataFrame(trades)
    show("COMBINED", dt)
    for s in dt['strategy'].unique(): show(f"Strategy: {s}", dt[dt['strategy']==s])
    for s in dt['setup'].unique(): show(f"Setup: {s}", dt[dt['setup']==s])
    
    stats = sel.get_stats()
    print(f"\n{'='*40}\nSELECTION FREQUENCY\n{'='*40}")
    for n, d in stats.items(): print(f"  {n}: {d['count']} ({d['pct']}%)")
    
    dt.to_csv("trade_journal_multi_strategy.csv", index=False)
    print(f"\nSaved: trade_journal_multi_strategy.csv")

if __name__ == "__main__":
    main()
