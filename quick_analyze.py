import pandas as pd

def analyze(filename, label):
    df = pd.read_csv(filename)
    total = len(df)
    wins = len(df[df['pnl'] > 0])
    win_rate = (wins / total * 100) if total > 0 else 0
    
    # RR = Avg Win / Avg Loss
    avg_win = df[df['pnl'] > 0]['pnl'].mean() if wins > 0 else 0
    avg_loss = abs(df[df['pnl'] < 0]['pnl'].mean()) if (total - wins) > 0 else 1
    rr = avg_win / avg_loss
    
    outcomes = df['outcome'].value_counts().to_dict()
    
    print(f"\n--- {label} ---")
    print(f"Trades: {total} | Win%: {win_rate:.2f}% | RR: {rr:.2f} | PnL: {df['pnl'].sum():.2f}")
    print(f"Outcomes: {outcomes}")

analyze("trade_journal_unified_20260423_185455.csv", "TEST 1 (10st)")
analyze("trade_journal_unified_20260423_190903.csv", "TEST 2 (3st)")
