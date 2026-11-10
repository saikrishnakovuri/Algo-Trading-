
import pandas as pd
from engine.unified_strategy_engine import UnifiedStrategyEngine
from engine.signal import SignalType

DATA_FILE = "../data/nifty50_5m.csv"

def sanity_check():
    engine = UnifiedStrategyEngine()
    df = pd.read_csv(DATA_FILE)
    df.index = pd.to_datetime(df['Datetime'])
    df.index.name = 'index_datetime'
    df.columns = [c.lower() for c in df.columns]
    
    # 1 week: Feb 4 to Feb 11
    df_week = df[(df.index >= '2026-02-04') & (df.index <= '2026-02-11')]
    print(f"Sanity check data: {len(df_week)} bars.")
    
    trades_count = 0
    strategies_found = set()
    
    for i in range(50, len(df_week), 3):
        current_window = df_week.iloc[:i+1]
        signals = engine.get_signals(current_window, backtest_mode=True)
        if signals:
            best_sig = max(signals, key=lambda x: x.confidence)
            trades_count += 1
            strategies_found.add(best_sig.strategy_name)
            
    print(f"Trades in 1 week: {trades_count}")
    print(f"Strategies used: {strategies_found}")

if __name__ == "__main__":
    sanity_check()
