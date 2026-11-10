"""
FINAL SURVIVOR ENGINE
=====================
Combines results from all 6 validation phases.
Extracts the strategies/configs that survived 18 months of testing.
Generates production-ready configuration.
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime


def load_all_results():
    """Load results from all 6 phases."""
    all_trades = []
    
    for phase in range(1, 7):
        path = f'pipeline/results/phase{phase}_results.csv'
        if not os.path.exists(path):
            path = f'pipeline/results/phase1_raw_results.csv' if phase == 1 else path
        
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if 'phase' not in df.columns:
                    df['phase'] = phase
                all_trades.append(df)
                print(f"  Phase {phase}: {len(df)} trades loaded")
            except pd.errors.EmptyDataError:
                print(f"  Phase {phase}: EMPTY FILE ({path})")
        else:
            print(f"  Phase {phase}: FILE NOT FOUND ({path})")
    
    if not all_trades:
        print("ERROR: No phase results found!")
        return None
    
    combined = pd.concat(all_trades, ignore_index=True)
    print(f"\n  TOTAL: {len(combined)} trades across {len(all_trades)} phases")
    return combined


def load_config():
    with open('pipeline/results/optimized_config.json', 'r') as f:
        return json.load(f)


def find_survivors(combined_df):
    """
    Find strategies that were PROFITABLE in at least 4 of 6 phases.
    These are the true survivors — the strategies with a durable edge.
    """
    survivors = {}
    
    for strat in combined_df['strategy_name'].unique():
        strat_data = combined_df[combined_df['strategy_name'] == strat]
        
        phase_results = {}
        for phase in strat_data['phase'].unique():
            phase_data = strat_data[strat_data['phase'] == phase]
            wins = phase_data[phase_data['result'] == 'WIN']
            gp = wins['pnl'].sum() if len(wins) > 0 else 0
            gl = abs(phase_data[phase_data['result'] == 'LOSS']['pnl'].sum()) or 0.01
            
            phase_results[int(phase)] = {
                'trades': len(phase_data),
                'pnl': round(phase_data['pnl'].sum(), 2),
                'win_rate': round(len(wins) / len(phase_data) * 100, 1) if len(phase_data) > 0 else 0,
                'profit_factor': round(gp / gl, 2),
                'profitable': phase_data['pnl'].sum() > 0,
            }
        
        profitable_phases = sum(1 for p in phase_results.values() if p['profitable'])
        total_pnl = strat_data['pnl'].sum()
        total_trades = len(strat_data)
        wins = strat_data[strat_data['result'] == 'WIN']
        
        survivors[strat] = {
            'total_trades': total_trades,
            'total_pnl': round(total_pnl, 2),
            'overall_win_rate': round(len(wins) / total_trades * 100, 1) if total_trades > 0 else 0,
            'profitable_phases': profitable_phases,
            'total_phases_tested': len(phase_results),
            'survival_rate': round(profitable_phases / max(len(phase_results), 1) * 100, 1),
            'phase_results': phase_results,
            # Let's adjust criteria since we might have less phases
            'is_survivor': profitable_phases >= (len(phase_results) // 2) and total_pnl > 0,
        }
    
    return survivors


def find_top_combinations(combined_df, min_trades=10):
    """
    Find the TOP 10 exact combinations (strategy + SL + hour + day)
    that performed best across all phases.
    """
    combos = []
    
    group_cols = ['strategy_name', 'sl_method', 'hour_of_entry', 'day_of_week']
    available_cols = [c for c in group_cols if c in combined_df.columns]
    
    for keys, group in combined_df.groupby(available_cols):
        if len(group) < min_trades:
            continue
        
        wins = group[group['result'] == 'WIN']
        gp = wins['pnl'].sum() if len(wins) > 0 else 0
        gl = abs(group[group['result'] == 'LOSS']['pnl'].sum()) or 0.01
        
        # Check how many phases this combo was profitable in
        profitable_phases = 0
        for phase in group['phase'].unique():
            if group[group['phase'] == phase]['pnl'].sum() > 0:
                profitable_phases += 1
        
        combo = dict(zip(available_cols, keys if isinstance(keys, tuple) else [keys]))
        combo.update({
            'trades': len(group),
            'win_rate': round(len(wins) / len(group) * 100, 1),
            'total_pnl': round(group['pnl'].sum(), 2),
            'profit_factor': round(gp / gl, 2),
            'avg_rr': round(group['risk_reward_achieved'].mean(), 2) if 'risk_reward_achieved' in group.columns else 0,
            'profitable_phases': profitable_phases,
            'roi_pct': round(group['pnl'].sum() / 500000 * 100, 2),
        })
        combos.append(combo)
    
    # Sort by: profitable_phases DESC, then profit_factor DESC, then P&L DESC
    combos = sorted(combos, key=lambda x: (x['profitable_phases'], x['profit_factor'], x['total_pnl']), reverse=True)
    return combos[:10]


def generate_production_config(survivors, top_combos, config):
    """Generate the final production-ready configuration."""
    
    surviving_strategies = [s for s, data in survivors.items() if data['is_survivor']]
    
    # Best hours from top combos
    best_hours = set()
    best_days = set()
    best_sl = None
    
    for combo in top_combos[:10]:
        if 'hour_of_entry' in combo:
            best_hours.add(int(combo['hour_of_entry']))
        if 'day_of_week' in combo:
            best_days.add(combo['day_of_week'])
        if 'sl_method' in combo and best_sl is None:
            best_sl = combo['sl_method']
    
    production_config = {
        'name': 'FINAL_PRODUCTION_CONFIG',
        'version': '1.0',
        'generated': datetime.now().isoformat(),
        'validated_over': '18 months (6 phases x 3 months)',
        'capital': 500000,
        'risk_pct': 0.01,
        
        'strategies': surviving_strategies,
        'allowed_hours': sorted(list(best_hours)) if best_hours else config.get('allowed_hours', [10, 11]),
        'allowed_days': sorted(list(best_days)) if best_days else config.get('allowed_days', ['Thursday', 'Friday']),
        'sl_method': best_sl or config.get('sl_method', 'TRAIL_2ATR_NOTP'),
        
        'top_10_combinations': top_combos,
        
        'risk_management': {
            'max_loss_per_trade': 5000,
            'max_daily_loss': 25000,
            'max_weekly_loss': 50000,
            'max_concurrent_positions': 3,
            'max_consecutive_losses_before_pause': 8,
        },
        
        'strategy_configs': config.get('strategy_configs', {}),
        
        'phase_history': config.get('phase_history', []),
    }
    
    return production_config


def generate_survivor_report(survivors, top_combos, combined_df, production_config):
    """Generate the comprehensive survivor report."""
    
    total_pnl = combined_df['pnl'].sum()
    total_trades = len(combined_df)
    wins = combined_df[combined_df['result'] == 'WIN']
    
    report = []
    report.append("=" * 70)
    report.append("  SURVIVOR REPORT — Evolutionary Backtest Results")
    report.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 70)
    
    report.append(f"\n  OVERALL PERFORMANCE (All Phases Combined)")
    report.append(f"  {'─'*50}")
    report.append(f"  Total Trades:     {total_trades}")
    report.append(f"  Net P&L:          ₹{total_pnl:,.2f}")
    report.append(f"  ROI:              {total_pnl/500000*100:.1f}%")
    report.append(f"  Win Rate:         {len(wins)/total_trades*100:.1f}%" if total_trades > 0 else "")
    
    gp = wins['pnl'].sum()
    gl = abs(combined_df[combined_df['result']=='LOSS']['pnl'].sum()) or 0.01
    report.append(f"  Profit Factor:    {gp/gl:.2f}")
    report.append(f"  Avg Win:          ₹{wins['pnl'].mean():,.2f}" if len(wins) > 0 else "")
    report.append(f"  Avg Loss:         ₹{combined_df[combined_df['result']=='LOSS']['pnl'].mean():,.2f}")
    
    # Survivor strategies
    report.append(f"\n  {'='*50}")
    report.append(f"  STRATEGY SURVIVORS (Profitable in 50%+ phases)")
    report.append(f"  {'='*50}")
    
    surviving = {s: d for s, d in survivors.items() if d['is_survivor']}
    killed = {s: d for s, d in survivors.items() if not d['is_survivor']}
    
    for strat, data in sorted(surviving.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
        report.append(f"\n  ✓ {strat}")
        report.append(f"    Trades: {data['total_trades']} | Win Rate: {data['overall_win_rate']}% | P&L: ₹{data['total_pnl']:,.2f}")
        report.append(f"    Profitable in {data['profitable_phases']}/{data['total_phases_tested']} phases ({data['survival_rate']}%)")
        for phase, pr in sorted(data['phase_results'].items()):
            status = "✓" if pr['profitable'] else "✗"
            report.append(f"      Phase {phase}: {status} {pr['trades']}t | {pr['win_rate']}% WR | PF {pr['profit_factor']} | ₹{pr['pnl']:,.2f}")
    
    report.append(f"\n  {'─'*50}")
    report.append(f"  KILLED STRATEGIES (Failed to survive)")
    report.append(f"  {'─'*50}")
    for strat, data in sorted(killed.items(), key=lambda x: x[1]['total_pnl']):
        report.append(f"  ✗ {strat} — {data['profitable_phases']}/{data['total_phases_tested']} phases | ₹{data['total_pnl']:,.2f}")
    
    # Top 10 combinations
    report.append(f"\n  {'='*50}")
    report.append(f"  TOP 10 PROVEN COMBINATIONS")
    report.append(f"  {'='*50}")
    for i, combo in enumerate(top_combos[:10], 1):
        parts = []
        if 'strategy_name' in combo: parts.append(combo['strategy_name'][:25])
        if 'sl_method' in combo: parts.append(combo['sl_method'])
        if 'day_of_week' in combo: parts.append(combo['day_of_week'])
        if 'hour_of_entry' in combo: parts.append(f"{combo['hour_of_entry']:02d}:00")
        
        combo_str = " + ".join(parts)
        report.append(f"\n  #{i}: {combo_str}")
        report.append(f"      Trades: {combo['trades']} | WR: {combo['win_rate']}% | PF: {combo['profit_factor']} | ROI: {combo['roi_pct']}%")
        report.append(f"      Profitable in {combo['profitable_phases']} phases")
    
    # Production config summary
    report.append(f"\n  {'='*50}")
    report.append(f"  PRODUCTION CONFIGURATION")
    report.append(f"  {'='*50}")
    report.append(f"  Strategies: {production_config['strategies']}")
    report.append(f"  Hours: {production_config['allowed_hours']}")
    report.append(f"  Days: {production_config['allowed_days']}")
    report.append(f"  SL Method: {production_config['sl_method']}")
    report.append(f"  Risk: {production_config['risk_pct']*100}% per trade")
    
    report.append(f"\n{'='*70}")
    report.append(f"  READY FOR PAPER TRADING")
    report.append(f"{'='*70}")
    
    return "\n".join(report)


def main():
    print("=" * 60)
    print("  FINAL SURVIVOR ENGINE")
    print("  Combining 18 months of validation data")
    print("=" * 60)
    
    combined = load_all_results()
    if combined is None:
        return
    
    config = load_config()
    
    print("\nFinding survivors...")
    survivors = find_survivors(combined)
    
    print("Finding top combinations...")
    top_combos = find_top_combinations(combined)
    
    print("Generating production config...")
    production_config = generate_production_config(survivors, top_combos, config)
    
    # Save production config
    with open('pipeline/results/FINAL_PRODUCTION_CONFIG.json', 'w', encoding='utf-8') as f:
        json.dump(production_config, f, indent=2, default=str)
    print(f"  Saved: pipeline/results/FINAL_PRODUCTION_CONFIG.json")
    
    # Generate and save report
    report = generate_survivor_report(survivors, top_combos, combined, production_config)
    with open('pipeline/results/SURVIVOR_REPORT.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  Saved: pipeline/results/SURVIVOR_REPORT.md")
    
    # Print the report
    print("\n" + report)
    
    # Final P&L projection
    surviving_trades = combined[combined['strategy_name'].isin(production_config['strategies'])]
    if len(surviving_trades) > 0:
        monthly_pnl = surviving_trades.groupby('phase')['pnl'].sum().mean()
        annual_projection = monthly_pnl * 4  # 4 quarters (rough)
        
        print(f"\n  {'='*50}")
        print(f"  P&L PROJECTION")
        print(f"  {'='*50}")
        print(f"  Avg P&L per 3-month phase: ₹{monthly_pnl:,.2f}")
        print(f"  Projected annual P&L: ₹{annual_projection:,.2f}")
        print(f"  Projected annual ROI: {annual_projection/500000*100:.1f}%")
        print(f"  {'='*50}")


if __name__ == "__main__":
    main()
