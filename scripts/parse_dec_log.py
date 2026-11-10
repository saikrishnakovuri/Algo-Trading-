import pandas as pd
import re

def parse_log(filepath):
    trades = []
    # Try different encodings
    for encoding in ['utf-8', 'utf-16', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
                if not content: continue
                # Reset trades for each encoding attempt
                trades = []
                for line in content.splitlines():
                    if '|' not in line: continue
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) < 9: continue
                    if not re.match(r'\d{4}-\d{2}-\d{2}', parts[0]): continue
                    
                    try:
                        pnl = float(parts[6].replace(',', ''))
                        rr = float(parts[7].replace(',', ''))
                        trades.append({
                            'date': parts[0],
                            'symbol': parts[1],
                            'strategy': parts[2],
                            'direction': parts[3],
                            'entry_time': parts[4],
                            'exit_time': parts[5],
                            'pnl': pnl,
                            'r_multiple': rr,
                            'outcome': parts[8]
                        })
                    except ValueError:
                        continue
                if trades:
                    return pd.DataFrame(trades)
        except Exception:
            continue
    return pd.DataFrame(trades)

def main():
    df = parse_log('dec_final_fixed_mr.log')
    if df.empty:
        print("No trades parsed from log.")
        return
    
    print("=" * 100)
    print(f"{'STRATEGY':<20} | {'TRADES':<8} | {'WIN%':<8} | {'AVG R':<8} | {'PnL (INR)':<12}")
    print("-" * 100)
    
    for strat in sorted(df['strategy'].unique()):
        sdf = df[df['strategy'] == strat]
        total = len(sdf)
        wins = len(sdf[sdf['outcome'] == 'WIN'])
        win_rate = (wins / total * 100) if total > 0 else 0
        avg_r = sdf['r_multiple'].mean()
        pnl = sdf['pnl'].sum()
        print(f"{strat:<20} | {total:<8} | {win_rate:<8.1f} | {avg_r:<8.2f} | {pnl:<12.2f}")
    
    print("-" * 100)
    total = len(df)
    wins = len(df[df['outcome'] == 'WIN'])
    win_rate = (wins / total * 100) if total > 0 else 0
    avg_r = df['r_multiple'].mean()
    pnl = df['pnl'].sum()
    print(f"{'COMBINED':<20} | {total:<8} | {win_rate:<8.1f} | {avg_r:<8.2f} | {pnl:<12.2f}")
    print("=" * 100)

if __name__ == "__main__":
    main()
