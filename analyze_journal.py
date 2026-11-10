import pandas as pd

df = pd.read_csv("trade_journal_unified_20260423_181729.csv")

# 1. Trades per setup_type
setup_counts = df['setup'].value_counts()

# 2. Win rate per setup_type
# We define a win as pnl > 0 for this analysis
df['is_win'] = df['pnl'] > 0
win_rate_per_setup = df.groupby('setup')['is_win'].mean() * 100

# 3. "TARGET HIT" positive P&L count
target_hits = df[df['outcome'] == 'TARGET HIT']
positive_target_hits = target_hits[target_hits['pnl'] > 0]

# 4. Outcome counts
outcome_counts = df['outcome'].value_counts()

# 5. Average hold time (if possible)
# 'time' is entry time, we don't have exit time in the journal CSV directly in a single column
# but we have the bars_passed in the logs. The journal doesn't have hold time.
# I will check if 'bars_passed' or similar was added to journal.
# Let's check columns.
print("Columns:", df.columns.tolist())

print("\n--- Setup Counts ---")
print(setup_counts)

print("\n--- Win Rate per Setup (%) ---")
print(win_rate_per_setup)

print("\n--- Target Hit Analysis ---")
print(f"Total Target Hits: {len(target_hits)}")
print(f"Positive PnL Target Hits: {len(positive_target_hits)}")

print("\n--- Outcome Counts ---")
print(outcome_counts)
