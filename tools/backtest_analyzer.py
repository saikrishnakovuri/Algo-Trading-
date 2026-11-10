#!/usr/bin/env python3
import os
import sys
import csv
import json
import zipfile
import glob
import math
import re
from collections import defaultdict
from datetime import datetime

ROOT = os.getcwd()
ZIP_NAME_GLOB = "*backtest_results_archive*.zip"
EXTRACT_DIR = os.path.join("data", "backtest_results_extracted")
OUTPUT_JSON = os.path.join("data", "backtest_analysis_summary.json")

def find_zip(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if re.search(r'backtest_results_archive', fn, re.I) and fn.lower().endswith('.zip'):
                return os.path.join(dirpath, fn)
    return None


def sanitize_num(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if s == "":
        return None
    # handle parentheses for negative
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    # remove common currency symbols and words
    s = s.replace(',', '')
    s = re.sub(r'[₹$£€]', '', s)
    s = re.sub(r'INR|Rs\.?', '', s, flags=re.I)
    s = s.strip()
    # extract first numeric token
    m = re.search(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def norm_key(k):
    return re.sub(r'[^0-9a-zA-Z]+', '_', k).strip('_').lower()


def parse_csv(path):
    rows = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return rows
            for r in reader:
                # normalize keys
                nr = {}
                for k, v in r.items():
                    nk = norm_key(k)
                    nr[nk] = v
                nr['_source_file'] = path
                rows.append(nr)
    except Exception as e:
        print(f"Failed to parse CSV {path}: {e}", file=sys.stderr)
    return rows


def parse_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read JSON {path}: {e}", file=sys.stderr)
        return None


def try_parse_dt(s):
    if not s:
        return None
    s = str(s).strip()
    # try iso
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    fmts = [
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %H:%M:%S',
        '%Y/%m/%d %H:%M:%S', '%d-%b-%Y %H:%M:%S'
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            pass
    # try numeric timestamp
    try:
        t = float(re.sub(r'[^0-9\.]','', s))
        # heuristics: if it's > 1e9 it's likely unix
        if t > 1e9:
            return datetime.fromtimestamp(t)
    except Exception:
        pass
    return None


def compute_metrics(trades):
    # trades: list of dicts with numeric fields: pnl_inr, pnl_points, entry, exit, qty, timestamp
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
    def _ts_to_num(t):
        if not t:
            return -1.0
        try:
            return t.timestamp()
        except Exception:
            try:
                return float(str(t))
            except Exception:
                return -1.0

    trades_sorted = sorted(trades, key=lambda x: _ts_to_num(x.get('timestamp')))
    eq = 0.0
    peak = 0.0
    max_dd = 0.0
    max_dd_money = 0.0
    eq_series = []
    for t in trades_sorted:
        pnl = t.get('pnl_inr') or 0.0
        eq += pnl
        eq_series.append(eq)
        if eq > peak:
            peak = eq
        dd = (peak - eq)
        if peak != 0:
            dd_pct = dd / peak
        else:
            dd_pct = 0.0
        if dd_pct > max_dd:
            max_dd = dd_pct
            max_dd_money = dd
    stats = {
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
    return stats, eq_series


def main():
    print('Analyzer start. Root:', ROOT)
    zip_path = find_zip(ROOT)
    if not zip_path:
        print('ERROR: backtest_results_archive.zip not found in workspace', file=sys.stderr)
        sys.exit(2)
    print('Found zip:', zip_path)

    # extract read-only to EXTRACT_DIR
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(EXTRACT_DIR)
    except Exception as e:
        print('Failed to extract zip:', e, file=sys.stderr)
        sys.exit(3)

    # gather files
    csv_files = glob.glob(os.path.join(EXTRACT_DIR, '**', '*.csv'), recursive=True)
    json_files = glob.glob(os.path.join(EXTRACT_DIR, '**', '*.json'), recursive=True)

    print(f'Parsed {len(csv_files)} CSV files and {len(json_files)} JSON files from the archive.')

    all_rows = []
    for csvf in csv_files:
        rows = parse_csv(csvf)
        for r in rows:
            r['_orig_file'] = csvf
            all_rows.append(r)

    # convert rows to normalized trade dicts
    trades = []
    for r in all_rows:
        t = {}
        # common fields
        t['source_file'] = r.get('_source_file')
        t['strategy'] = r.get('strategy') or r.get('pattern') or r.get('trade_strategy') or r.get('strategy_name')
        t['symbol'] = r.get('symbol') or r.get('underlying') or r.get('ticker')
        # numeric fields
        # try multiple keys
        def gv(keys):
            for k in keys:
                if k in r and r[k] not in (None, ''):
                    return r[k]
            return None
        # entry/exit
        entry = sanitize_num(gv(['entry','entry_price','entryprice','entry_px','strike','buy_price']))
        exitp = sanitize_num(gv(['exit','exit_price','exitprice','exit_px','sell_price']))
        pnl_points = sanitize_num(gv(['p_l_points','pnl_points','p_and_l_points','p_l_points_','p_l_points_']))
        pnl_inr = sanitize_num(gv(['p_l_inr','pnl_inr','p_and_l_inr','net_pnl','netpnl','net_pnl','pnl_inr','pnlinr','pnl']))
        qty = sanitize_num(gv(['qty','quantity','contract_size','lots','size']))
        r_mult = sanitize_num(gv(['r_multiple','r_multiple_','r_multiple']))
        bars_held = sanitize_num(gv(['bars_held','barsheld','bars']))
        ts_raw = gv(['timestamp','date','datetime','time','trade_time'])
        ts = try_parse_dt(ts_raw)
        # fallback: maybe date column present
        if not ts:
            ts = try_parse_dt(gv(['date']))
        t['timestamp'] = ts
        t['entry'] = entry
        t['exit'] = exitp
        t['pnl_points'] = pnl_points
        t['pnl_inr'] = pnl_inr
        t['qty'] = qty if qty is not None else 1.0
        t['r_multiple'] = r_mult
        t['bars_held'] = bars_held
        t['raw'] = r
        trades.append(t)

    # detect multiplier from trades where both pnl_points and pnl_inr are present and pnl_points != 0
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
        try:
            mult_est = sorted(mults)[len(mults)//2]  # median
        except Exception:
            mult_est = sum(mults)/len(mults)
    # fallback: check if qty*100 is a likely multiplier
    if not mult_est:
        # check typical qty
        qvals = [t['qty'] for t in trades if t.get('qty')]
        if qvals:
            qmed = sorted(qvals)[len(qvals)//2]
            if qmed >= 1:
                mult_est = qmed * 100
    if not mult_est:
        mult_est = 1.0

    # fill missing pnl_inr where possible
    for t in trades:
        if t.get('pnl_inr') is None:
            if t.get('pnl_points') not in (None, 0):
                t['pnl_inr'] = t['pnl_points'] * mult_est
            elif t.get('entry') not in (None,) and t.get('exit') not in (None,):
                # use price diff * qty * multiplier assumption
                diff = (t['exit'] - t['entry']) if (t['exit'] is not None and t['entry'] is not None) else None
                if diff is not None:
                    t['pnl_points'] = diff
                    t['pnl_inr'] = diff * (t.get('qty') or 1.0) * (mult_est or 1.0)

    # compute overall metrics
    # only consider trades that have pnl_inr now
    trades_with_pnl = [t for t in trades if t.get('pnl_inr') is not None]
    global_stats, eq_series = compute_metrics(trades_with_pnl)

    # per-strategy and per-symbol
    by_strategy = defaultdict(list)
    by_symbol = defaultdict(list)
    for t in trades_with_pnl:
        s = (t.get('strategy') or 'unknown').strip()
        by_strategy[s].append(t)
        sym = (t.get('symbol') or 'unknown').strip()
        by_symbol[sym].append(t)

    strat_stats = {}
    for s,k in by_strategy.items():
        stats, _ = compute_metrics(k)
        # compute median win/loss in points
        win_points = [tt['pnl_points'] for tt in k if tt.get('pnl_points') and tt.get('pnl_points')>0]
        loss_points = [abs(tt['pnl_points']) for tt in k if tt.get('pnl_points') and tt.get('pnl_points')<0]
        median_win = sorted(win_points)[len(win_points)//2] if win_points else None
        median_loss = sorted(loss_points)[len(loss_points)//2] if loss_points else None
        # suggest SL/Target and qty
        suggested = {}
        if median_loss:
            suggested['suggested_sl_points'] = round(median_loss * 1.05, 3)
        if median_win:
            suggested['suggested_target_points'] = round(median_win * 0.9, 3)
        # quantity suggestion = median quantity
        qvals = sorted([tt['qty'] for tt in k if tt.get('qty')])
        if qvals:
            suggested['suggested_qty'] = qvals[len(qvals)//2]
        else:
            suggested['suggested_qty'] = 1
        stats['median_win_points'] = median_win
        stats['median_loss_points'] = median_loss
        stats['suggested'] = suggested
        strat_stats[s] = stats

    # per-symbol suggestions (top symbols)
    sym_stats = {}
    for sym,k in by_symbol.items():
        stats, _ = compute_metrics(k)
        qvals = sorted([tt['qty'] for tt in k if tt.get('qty')])
        stats['suggested_qty'] = qvals[len(qvals)//2] if qvals else 1
        sym_stats[sym] = stats

    # top wins and losses
    top_wins = sorted(trades_with_pnl, key=lambda x: x['pnl_inr'], reverse=True)[:10]
    top_losses = sorted(trades_with_pnl, key=lambda x: x['pnl_inr'])[:10]

    # collect OOS files metrics if present
    oos_summary = {}
    for jf in json_files:
        name = os.path.basename(jf).lower()
        if 'oos' in name or 'out_of_sample' in name or 'summary_oos' in name:
            j = parse_json(jf)
            oos_summary[os.path.basename(jf)] = j

    # mismatches where reported pnl_inr existed but differs from calculated using pnl_points*mult_est
    mismatches = []
    for t in trades:
        if t.get('pnl_points') not in (None, 0) and t.get('pnl_inr') not in (None,):
            calc = (t['pnl_points'] * mult_est)
            if abs(calc - t['pnl_inr']) > max(0.01, abs(calc)*0.02):
                mismatches.append({'symbol': t.get('symbol'), 'strategy': t.get('strategy'), 'pnl_points': t.get('pnl_points'), 'pnl_inr': t.get('pnl_inr'), 'calc_with_mult': calc, 'source': t.get('source_file')})

    summary = {
        'global_stats': global_stats,
        'mult_estimate': mult_est,
        'num_csv_files': len(csv_files),
        'num_json_files': len(json_files),
        'strategy_stats': strat_stats,
        'symbol_stats_sample': {k: sym_stats[k] for k in list(sym_stats.keys())[:20]},
        'top_wins': [{'symbol': t.get('symbol'), 'strategy': t.get('strategy'), 'pnl_inr': t.get('pnl_inr'), 'timestamp': str(t.get('timestamp'))} for t in top_wins],
        'top_losses': [{'symbol': t.get('symbol'), 'strategy': t.get('strategy'), 'pnl_inr': t.get('pnl_inr'), 'timestamp': str(t.get('timestamp'))} for t in top_losses],
        'mismatches_sample': mismatches[:50],
        'oos_summary_files': oos_summary,
        'total_trades_parsed': len(trades),
    }

    # save json
    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        print('Wrote analysis to', OUTPUT_JSON)
    except Exception as e:
        print('Failed to write output JSON:', e, file=sys.stderr)

    # print concise summary to stdout
    print('\n--- Summary ---')
    gs = global_stats
    print(f"Total trades parsed with PnL: {gs.get('total_trades')}")
    print(f"Total PnL (INR): {gs.get('total_pnl'):.2f}")
    print(f"Win rate: {gs.get('win_rate_pct'):.2f}% ({gs.get('win_count')} wins)")
    pf = gs.get('profit_factor')
    print(f"Profit factor: {pf:.2f}" if pf is not None else "Profit factor: N/A")
    print(f"Max drawdown: {gs.get('max_drawdown_pct')*100:.2f}%")
    print(f"Estimated multiplier (Pnl_INR / Pnl_points): {mult_est:.3f}")
    print(f"Number of CSV files: {len(csv_files)}, JSON files: {len(json_files)}")
    print('\nTop 3 wins:')
    for t in summary['top_wins'][:3]:
        print(' ', t)
    print('\nTop 3 losses:')
    for t in summary['top_losses'][:3]:
        print(' ', t)
    print('\nSample mismatches (first 5):')
    for m in summary['mismatches_sample'][:5]:
        print(' ', m)

if __name__ == '__main__':
    main()
