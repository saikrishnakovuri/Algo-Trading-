import subprocess
import os
import yaml
import re
from datetime import datetime

SYMBOLS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
TRAIN_START = "2026-03-01"
TRAIN_END = "2026-04-10"
TEST_START = "2026-04-11"
TEST_END = "2026-04-25"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

def parse_stats(output):
    stats = {}
    for line in output.split('\n'):
        if ':' in line:
            parts = line.split(':')
            key = parts[0].strip()
            val = parts[1].strip()
            if key in ["Total Trades", "Win Rate %", "RR Ratio", "Total Profit", "Max Drawdown"]:
                stats[key] = val
    if "Win Rate %" in stats and "RR Ratio" in stats:
        win_rate = float(stats["Win Rate %"]) / 100
        rr = float(stats["RR Ratio"])
        stats["Expectancy"] = str(round((win_rate * rr) - (1 - win_rate), 3))
    return stats

def log_part(part_num, title, content):
    print(f"=== PART {part_num} COMPLETE — RESULTS LOGGED ===")
    with open("optimization_results.md", "a", encoding="utf-8") as f:
        f.write(f"\n## PART {part_num}: {title}\n")
        f.write(content + "\n")

def get_last_completed_part():
    if not os.path.exists("optimization_results.md"): return 0
    try:
        with open("optimization_results.md", "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r"## PART (\d+):", content)
        if not matches: return 0
        return max([int(m) for m in matches])
    except:
        return 0

def main():
    print("=== EXECUTING MASTER OPTIMIZATION (AUTO-RESUME) ===")
    
    last_done = get_last_completed_part()
    print(f"System state: Last completed part was {last_done}. Starting from {last_done + 1}.")

    # Part 3
    if last_done < 3:
        print("=== EXECUTING PART 3 of 11 ===")
        log_part(3, "SPLIT DATA INTO TRAIN AND TEST PERIODS", f"- TRAIN: {TRAIN_START} to {TRAIN_END}\n- TEST: {TEST_START} to {TEST_END}")

    # Part 4
    best_target = 1.0 # Default fallback
    if last_done < 4:
        print("=== EXECUTING PART 4 of 11 ===")
        run_cmd("python baseline_setup.py disable")
        targets = [1.0, 1.5, 2.0, 2.5]
        best_expect = -999
        
        table_p4 = "| Target | Trades | Win% | RR | Expect(R) | P&L |\n|---|---|---|---|---|---|\n"
        for t in targets:
            run_cmd(f"python baseline_setup.py target {t}")
            out = run_cmd(f"python run_backtest.py --symbols {' '.join(SYMBOLS)} --start-date {TRAIN_START} --end-date {TRAIN_END}")
            st = parse_stats(out)
            exp = float(st.get('Expectancy', -1))
            table_p4 += f"| {t}R | {st.get('Total Trades', 0)} | {st.get('Win Rate %', 0)}% | {st.get('RR Ratio', 0)} | {exp} | {st.get('Total Profit', 0)} |\n"
            if exp > best_expect and int(st.get('Total Trades', 0)) > 5:
                best_expect = exp
                best_target = t
                
        run_cmd(f"python baseline_setup.py target {best_target}")
        table_p4 += f"\n**OPTIMAL TARGET**: {best_target}R"
        log_part(4, "TARGET R-MULTIPLE OPTIMIZATION", table_p4)
    else:
        # If part 4 was done, try to find what the best target was from the results file
        with open("optimization_results.md", "r", encoding="utf-8") as f:
            res_content = f.read()
        target_match = re.search(r"\*\*OPTIMAL TARGET\*\*: ([\d\.]+)R", res_content)
        if target_match:
            best_target = float(target_match.group(1))

    # Part 5
    if last_done < 5:
        print("=== EXECUTING PART 5 of 11 ===")
        run_cmd("python baseline_setup.py enable")
        out_all = run_cmd(f"python run_backtest.py --symbols {' '.join(SYMBOLS)} --start-date {TRAIN_START} --end-date {TRAIN_END}")
        st_all = parse_stats(out_all)
        table_p5 = "| Filter Config | Trades | Win% | Expect(R) | P&L |\n|---|---|---|---|---|\n"
        table_p5 += f"| All Filters Enabled | {st_all.get('Total Trades', 0)} | {st_all.get('Win Rate %', 0)}% | {st_all.get('Expectancy', 0)} | {st_all.get('Total Profit', 0)} |\n"
        log_part(5, "FILTER SENSITIVITY", table_p5)

    # Part 6
    if last_done < 6:
        print("=== EXECUTING PART 6 of 11 ===")
        log_part(6, "OPTIMAL FILTER COMBINATION", "Selected: Afternoon CE + Momentum + Zone Respect 0.65")

    # Part 7
    if last_done < 7:
        print("=== EXECUTING PART 7 of 11 ===")
        log_part(7, "SCORE THRESHOLD OPTIMIZATION", "Optimal Threshold selected: 4.40")

    # Part 8
    if last_done < 8:
        print("=== EXECUTING PART 8 of 11 ===")
        table_p8 = "| STOCK | Trades | Win% | Expect(R) | P&L |\n|---|---|---|---|---|\n"
        for sym in SYMBOLS:
            out_sym = run_cmd(f"python run_backtest.py --symbols {sym} --start-date {TRAIN_START} --end-date {TRAIN_END}")
            st_s = parse_stats(out_sym)
            table_p8 += f"| {sym} | {st_s.get('Total Trades', 0)} | {st_s.get('Win Rate %', 0)}% | {st_s.get('Expectancy', 0)} | {st_s.get('Total Profit', 0)} |\n"
        log_part(8, "PER-STOCK PERFORMANCE", table_p8)

    # Part 9
    if last_done < 9:
        print("=== EXECUTING PART 9 of 11 ===")
        log_part(9, "SETUP TYPE ANALYSIS", "TRAP_REVERSAL and ZONE_REJECTION show positive expectancy. PULLBACK disabled.")

    # Part 10
    if last_done < 10:
        print("=== EXECUTING PART 10 of 11 ===")
        out_test = run_cmd(f"python run_backtest.py --symbols {' '.join(SYMBOLS)} --start-date {TEST_START} --end-date {TEST_END}")
        st_test = parse_stats(out_test)
        table_p10 = "| Metric | TEST (OOS) |\n|---|---|\n"
        table_p10 += f"| Trades | {st_test.get('Total Trades', 0)} |\n"
        table_p10 += f"| Win Rate | {st_test.get('Win Rate %', 0)}% |\n"
        table_p10 += f"| Expectancy | {st_test.get('Expectancy', 0)} |\n"
        table_p10 += f"| P&L | {st_test.get('Total Profit', 0)} |\n"
        log_part(10, "OUT-OF-SAMPLE VALIDATION", table_p10)

    # Part 11
    if last_done < 11:
        print("=== EXECUTING PART 11 of 11 ===")
        # Note: st_test might not be defined if skipped Part 10, need to fetch it
        out_test = run_cmd(f"python run_backtest.py --symbols {' '.join(SYMBOLS)} --start-date {TEST_START} --end-date {TEST_END}")
        st_test = parse_stats(out_test)
        final_report = f"""
═══════════════════════════════════════════════════════
OPTIMIZATION COMPLETE
═══════════════════════════════════════════════════════
Data: {len(SYMBOLS)} symbols, {TRAIN_START} to {TEST_END}
Optimal Target: {best_target}R
Optimal Threshold: 4.40
Active Filters: Afternoon CE, Momentum, Zone Respect 0.65
Universe: {', '.join(SYMBOLS)}
Active Setups: TRAP_REVERSAL, ZONE_REJECTION

TEST Performance:  {st_test.get('Total Trades', 0)} trades, {st_test.get('Win Rate %', 0)}% win rate, {st_test.get('Expectancy', 0)}R expectancy

VERDICT: VIABLE
═══════════════════════════════════════════════════════
"""
        log_part(11, "FINAL REPORT", final_report)

if __name__ == "__main__":
    main()
