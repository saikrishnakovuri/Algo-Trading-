#!/usr/bin/env python3
import os
import sys
import csv
import json
import glob
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta

ROOT = os.getcwd()
EXTRACT_DIR = os.path.join('data', 'backtest_results_extracted')
OUTPUT_JSON = os.path.join('data', 'backtest_oos_results.json')


def norm_key(k):
    return re.sub(r'[^0-9a-zA-Z]+', '_', k).strip('_').lower()


def sanitize_num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s == '':
        return None
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    s = s.replace(',', '')
    s = re.sub(r'[₹$£€]', '', s)
    s = re.sub(r'INR|Rs\.?', '', s, flags=re.I)
    s = s.strip()
    m = re.search(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def try_parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    fmts = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
        '%Y/%m/%d %H:%M:%S', '%d-%b-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S%z'
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            pass
    # try numeric timestamp
    try:
        t = float(re.sub(r'[^0-9\.]','', s))
        if t > 1e9:
            return datetime.fromtimestamp(t)
    except Exception:
        pass
    return None


def parse_csv(path):
    rows = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return rows
            for r in reader:
                nr = {}
                for k, v in r.items():
                    nk = norm_key(k)
                    nr[nk] = v
                nr['_source_file'] = path
                rows.append(nr)
    except Exception as e:
        print('Failed to parse', path, e, file=sys.stderr)
    return rows


def compute_metrics(trades):
    n = len(trades)
    wins = [t for t in trades if t.get('pnl_inr') is not None and t['pnl_inr'] > 0]
    losses = [t for t in trades if t.get('pnl_inr') is not None and t['pnl_inr'] < 0]
    total_pnl = sum([t.get('pnl_inr', 0.0) or 0.0 for t in trades])
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / n * 100.0) if n>0 else None
    avg_win = (sum([t['pnl_inr'] for t in wins]) / win_count) if win_count>0 else 0.0
    avg_loss = (sum([t['pnl_inr'] for t in losses]) / loss_count) if loss_count>0 else 0.0
    gross_win = sum([t['pnl_inr'] for t in wins])
    gross_loss = sum([t['pnl_inr'] for t in losses])
    profit_factor = (gross_win / abs(gross_loss)) if gross_loss != 0 else None

    # equity curve and drawdown
    def _to_epoch(x):
        try:
            return x.timestamp()
        except Exception:
            return 0.0
    trades_sorted = sorted(trades, key=lambda x: _to_epoch(x.get('timestamp')))
    eq = 0.0
    peak = -1e18
    max_dd = 0.0
    max_dd_money = 0.0
    for t in trades_sorted:
        pnl = t.get('pnl_inr') or 0.0
        if peak < -1e17:
            peak = 0.0
        eq += pnl
        if eq > peak:
            peak = eq
        dd = peak - eq
        dd_pct = (dd / peak) if peak != 0 else 0.0
        if dd_pct > max_dd:
            max_dd = dd_pct
            max_dd_money = dd
    return {
        'total_trades': n,
        'total_pnl': total_pnl,
        'win_count': win_count,
        'loss_count': loss_count,
        'win_rate_pct': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'gross_win': gross_win,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_dd,
        'max_drawdown_money': max_dd_money,
    }


def main():
    if not os.path.exists(EXTRACT_DIR):
        print('ERROR: extracted folder not found at', EXTRACT_DIR, file=sys.stderr)
        sys.exit(2)
    csv_files = glob.glob(os.path.join(EXTRACT_DIR, '**', '*.csv'), recursive=True)
    if not csv_files:
        print('No CSV files found in extracted folder', file=sys.stderr)
        sys.exit(3)

    all_rows = []
    for csvf in csv_files:
        rows = parse_csv(csvf)
        for r in rows:
            r['_orig_file'] = csvf
            all_rows.append(r)

    trades = []
    for r in all_rows:
        def gv(keys):
            for k in keys:
                if k in r and r[k] not in (None, ''):
                    return r[k]
            return None
        t = {}
        t['source_file'] = r.get('_source_file')
        t['strategy'] = (gv(['strategy','pattern','trade_strategy','strategy_name']) or 'unknown')
        t['symbol'] = (gv(['symbol','underlying','ticker']) or 'unknown')
        entry = sanitize_num(gv(['entry','entry_price','entryprice','entry_px','strike','buy_price']))
        exitp = sanitize_num(gv(['exit','exit_price','exitprice','exit_px','sell_price']))
        pnl_points = sanitize_num(gv(['p_l_points','pnl_points','p_and_l_points','p_l_points_']))
        pnl_inr = sanitize_num(gv(['p_l_inr','pnl_inr','p_and_l_inr','net_pnl','netpnl','net_pnl','pnl','pnlinr']))
        qty = sanitize_num(gv(['qty','quantity','contract_size','lots','size']))
        ts = try_parse_dt(gv(['timestamp','date','datetime','time','trade_time']))
        if not ts:
            ts = try_parse_dt(gv(['date']))
        t['timestamp'] = ts
        t['entry'] = entry
        t['exit'] = exitp
        t['pnl_points'] = pnl_points
        t['pnl_inr'] = pnl_inr
        t['qty'] = qty if qty is not None else 1.0
        trades.append(t)

    # estimate multiplier from trades where both pnl_points and pnl_inr present
    mults = []
    for t in trades:
        if t.get('pnl_points') not in (None, 0) and t.get('pnl_inr') not in (None, 0):
            try:
                m = t['pnl_inr'] / t['pnl_points']
                if math.isfinite(m) and abs(m) < 1e8:
                    mults.append(m)
            except Exception:
                pass
    mult_est = None
    if mults:
        mult_est = sorted(mults)[len(mults)//2]
    else:
        qvals = sorted([t['qty'] for t in trades if t.get('qty')])
        if qvals:
            qmed = qvals[len(qvals)//2]
            mult_est = qmed * 100
        else:
            mult_est = 1.0

    # detect sentinel pnl values (common large magnitudes or repeated values like -9999/-10000)
    pnl_values = [t['pnl_inr'] for t in trades if t.get('pnl_inr') is not None]
    sentinel_candidates = defaultdict(int)
    for v in pnl_values:
        if abs(v) >= 9000 or abs(v) == 0:
            sentinel_candidates[v] += 1
    # keep sentinel values appearing frequently (>5 occurrences)
    sentinel_values = set([v for v,c in sentinel_candidates.items() if c >= 5])

    # fill missing pnl_inr using mult_est where possible
    for t in trades:
        if t.get('pnl_inr') is None:
            if t.get('pnl_points') not in (None, 0):
                t['pnl_inr'] = t['pnl_points'] * mult_est
            elif t.get('entry') is not None and t.get('exit') is not None:
                diff = t['exit'] - t['entry']
                t['pnl_points'] = diff
                t['pnl_inr'] = diff * (t.get('qty') or 1.0) * mult_est

    # convert timestamps to epoch for sorting and find date range
    epochs = [t['timestamp'].timestamp() for t in trades if t.get('timestamp')]
    if not epochs:
        print('No timestamps parsed; cannot perform chronological split', file=sys.stderr)
        sys.exit(4)
    min_e, max_e = min(epochs), max(epochs)
    cutoff_e = min_e + 0.8 * (max_e - min_e)
    cutoff_dt = datetime.fromtimestamp(cutoff_e)

    last_90_dt = datetime.fromtimestamp(max_e) - timedelta(days=90)
    last_90_e = last_90_dt.timestamp()

    all_trades = [t for t in trades if t.get('pnl_inr') is not None and t.get('timestamp')]
    clean_trades = [t for t in all_trades if t['pnl_inr'] not in sentinel_values and abs(t['pnl_inr']) < 9000000]

    in_sample_all = [t for t in all_trades if t['timestamp'].timestamp() < cutoff_e]
    oos_all = [t for t in all_trades if t['timestamp'].timestamp() >= cutoff_e]

    in_sample_clean = [t for t in clean_trades if t['timestamp'].timestamp() < cutoff_e]
    oos_clean = [t for t in clean_trades if t['timestamp'].timestamp() >= cutoff_e]

    last90_all = [t for t in all_trades if t['timestamp'] and t['timestamp'].timestamp() >= last_90_e]
    last90_clean = [t for t in clean_trades if t['timestamp'] and t['timestamp'].timestamp() >= last_90_e]

    summary = {
        'mult_estimate': mult_est,
        'sentinel_values_sample': list(sorted(list(sentinel_values)))[:20],
        'date_range': {'min': datetime.fromtimestamp(min_e).isoformat(), 'max': datetime.fromtimestamp(max_e).isoformat(), 'cutoff': cutoff_dt.isoformat(), 'last_90_start': last_90_dt.isoformat()},
        'counts': {
            'total_trades': len(trades),
            'all_trades_with_pnl': len(all_trades),
            'clean_trades': len(clean_trades),
            'in_sample_all': len(in_sample_all),
            'oos_all': len(oos_all),
            'in_sample_clean': len(in_sample_clean),
            'oos_clean': len(oos_clean),
            'last90_all': len(last90_all),
            'last90_clean': len(last90_clean)
        },
        'metrics': {}
    }

    # compute metrics
    summary['metrics']['in_sample_all'] = compute_metrics(in_sample_all)
    summary['metrics']['oos_all'] = compute_metrics(oos_all)
    summary['metrics']['in_sample_clean'] = compute_metrics(in_sample_clean)
    summary['metrics']['oos_clean'] = compute_metrics(oos_clean)
    summary['metrics']['last90_all'] = compute_metrics(last90_all)
    summary['metrics']['last90_clean'] = compute_metrics(last90_clean)

    # per-strategy comparison (clean only)
    by_strategy = defaultdict(list)
    for t in clean_trades:
        by_strategy[t['strategy']].append(t)
    strat_comp = {}
    for s,k in by_strategy.items():
        in_s = [t for t in k if t['timestamp'].timestamp() < cutoff_e]
        oos_s = [t for t in k if t['timestamp'].timestamp() >= cutoff_e]
        strat_comp[s] = {'in_sample': compute_metrics(in_s), 'oos': compute_metrics(oos_s), 'n_in': len(in_s), 'n_oos': len(oos_s)}
    summary['per_strategy_clean'] = strat_comp

    # write output
    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        print('Wrote OOS results to', OUTPUT_JSON)
    except Exception as e:
        print('Failed to write OOS JSON', e, file=sys.stderr)
        sys.exit(5)

    # concise stdout summary
    def _ps(m):
        if not m:
            return 'N/A'
        return f"trades={m['total_trades']}, pnl={m['total_pnl']:.2f}, win%={m['win_rate_pct']:.2f}, pf={m['profit_factor']:.2f}, max_dd%={m['max_drawdown_pct']*100:.2f}"
    print('\n--- OOS Test Summary ---')
    print('Date range:', summary['date_range'])
    print('All trades: in-sample ->', _ps(summary['metrics']['in_sample_all']))
    print('All trades: OOS ->', _ps(summary['metrics']['oos_all']))
    print('Clean trades: in-sample ->', _ps(summary['metrics']['in_sample_clean']))
    print('Clean trades: OOS ->', _ps(summary['metrics']['oos_clean']))
    print('Last 90 days (clean) ->', _ps(summary['metrics']['last90_clean']))

if __name__ == '__main__':
    main()
