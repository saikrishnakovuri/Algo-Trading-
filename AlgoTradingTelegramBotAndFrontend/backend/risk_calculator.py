"""
Risk calculation utilities for algorithmic trading analytics.
All functions are pure (no I/O) and accept lists of PnL values.
"""
import math
import random
from typing import List, Optional


def compute_equity_curve(pnl_series: List[float]) -> List[float]:
    """Cumulative PnL curve starting from 0."""
    curve, total = [], 0.0
    for p in pnl_series:
        total += p
        curve.append(round(total, 2))
    return curve


def compute_drawdown_series(equity_curve: List[float]) -> List[float]:
    """Absolute drawdown ($ below peak) at each step. Always <= 0."""
    if not equity_curve:
        return []
    peak = equity_curve[0]
    result = []
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        result.append(round(eq - peak, 2))
    return result


def compute_max_drawdown(equity_curve: List[float]) -> float:
    """Maximum absolute drawdown (negative number)."""
    series = compute_drawdown_series(equity_curve)
    return round(min(series), 2) if series else 0.0


def compute_max_drawdown_pct(equity_curve: List[float]) -> float:
    """Maximum drawdown as % of peak equity (negative %)."""
    if not equity_curve:
        return 0.0
    peak, max_dd_pct = equity_curve[0], 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (eq - peak) / peak * 100
            if dd < max_dd_pct:
                max_dd_pct = dd
    return round(max_dd_pct, 2)


def _annualization_factor(pnl_series: List[float], dates: Optional[List[str]] = None) -> float:
    """Estimate trades per year for annualizing Sharpe/Sortino/Calmar."""
    n = len(pnl_series)
    if dates and len(dates) >= 2:
        try:
            from datetime import datetime
            d1 = datetime.fromisoformat(dates[0][:10])
            d2 = datetime.fromisoformat(dates[-1][:10])
            days = max((d2 - d1).days, 1)
            return round(n * 365 / days, 2)
        except Exception:
            pass
    return 252.0  # default: ~252 trading days/year


def compute_sharpe(pnl_series: List[float], dates: Optional[List[str]] = None) -> float:
    if len(pnl_series) < 2:
        return 0.0
    n = len(pnl_series)
    mean = sum(pnl_series) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in pnl_series) / (n - 1))
    if std == 0:
        return 0.0
    ann = _annualization_factor(pnl_series, dates)
    return round((mean / std) * math.sqrt(ann), 2)


def compute_sortino(pnl_series: List[float], dates: Optional[List[str]] = None) -> float:
    if len(pnl_series) < 2:
        return 0.0
    mean = sum(pnl_series) / len(pnl_series)
    negatives = [x for x in pnl_series if x < 0]
    if not negatives:
        return 9.99  # effectively infinite — no losing trades
    d_std = math.sqrt(sum(x ** 2 for x in negatives) / len(negatives))
    if d_std == 0:
        return 0.0
    ann = _annualization_factor(pnl_series, dates)
    return round((mean / d_std) * math.sqrt(ann), 2)


def compute_calmar(pnl_series: List[float], equity_curve: List[float],
                   dates: Optional[List[str]] = None) -> float:
    max_dd = abs(compute_max_drawdown(equity_curve))
    if max_dd == 0 or not pnl_series:
        return 0.0
    ann = _annualization_factor(pnl_series, dates)
    annual_return = (sum(pnl_series) / len(pnl_series)) * ann
    return round(annual_return / max_dd, 2)


def compute_kelly(pnl_series: List[float]) -> float:
    """Kelly Criterion as a percentage (0–100). Cap at 50% (half-Kelly safe zone)."""
    wins = [p for p in pnl_series if p > 0]
    losses = [p for p in pnl_series if p < 0]
    if not wins or not losses:
        return 0.0
    W = len(wins) / len(pnl_series)
    R = (sum(wins) / len(wins)) / abs(sum(losses) / len(losses))
    kelly = W - (1 - W) / R if R > 0 else 0.0
    return round(max(0.0, min(kelly, 1.0)) * 100, 2)


def compute_profit_factor(pnl_series: List[float]) -> float:
    gross_profit = sum(p for p in pnl_series if p > 0)
    gross_loss = abs(sum(p for p in pnl_series if p < 0))
    if gross_loss == 0:
        return round(gross_profit, 2) if gross_profit else 0.0
    return round(gross_profit / gross_loss, 2)


def compute_expectancy(pnl_series: List[float]) -> float:
    """Average expected PnL per trade."""
    if not pnl_series:
        return 0.0
    return round(sum(pnl_series) / len(pnl_series), 2)


def compute_consecutive_streaks(pnl_series: List[float]) -> dict:
    if not pnl_series:
        return {"max_wins": 0, "max_losses": 0, "current_streak": 0, "current_type": "none"}
    max_wins = max_losses = current = 0
    current_sign = None
    for p in pnl_series:
        sign = 1 if p > 0 else -1
        if sign == current_sign:
            current += 1
        else:
            current, current_sign = 1, sign
        if sign == 1:
            max_wins = max(max_wins, current)
        else:
            max_losses = max(max_losses, current)
    return {
        "max_wins": max_wins,
        "max_losses": max_losses,
        "current_streak": current,
        "current_type": "win" if current_sign == 1 else "loss",
    }


def compute_monte_carlo(pnl_series: List[float], n_simulations: int = 500) -> dict:
    """
    Monte Carlo simulation via bootstrap resampling.
    Returns 5 percentile equity curves (P5, P25, P50, P75, P95),
    probability of profit, and final equity distribution stats.
    """
    if len(pnl_series) < 5:
        return {
            "percentiles": {}, "prob_profit": 0,
            "final_p5": 0, "final_p50": 0, "final_p95": 0, "n": 0,
        }
    rng = random.Random(42)
    n = len(pnl_series)
    all_finals = []
    all_curves = []

    for _ in range(n_simulations):
        sample = [rng.choice(pnl_series) for _ in range(n)]
        curve, total = [], 0.0
        for p in sample:
            total += p
            curve.append(round(total, 2))
        all_curves.append(curve)
        all_finals.append(total)

    # Sort curve indices by final value to pick representative percentiles
    sorted_idx = sorted(range(n_simulations), key=lambda i: all_finals[i])
    pct_map = {
        "5": sorted_idx[int(0.05 * n_simulations)],
        "25": sorted_idx[int(0.25 * n_simulations)],
        "50": sorted_idx[int(0.50 * n_simulations)],
        "75": sorted_idx[int(0.75 * n_simulations)],
        "95": sorted_idx[min(int(0.95 * n_simulations), n_simulations - 1)],
    }
    percentiles = {k: all_curves[v] for k, v in pct_map.items()}

    all_finals.sort()
    return {
        "percentiles": percentiles,
        "prob_profit": round(sum(1 for f in all_finals if f > 0) / n_simulations * 100, 1),
        "final_p5": round(all_finals[int(0.05 * n_simulations)], 2),
        "final_p50": round(all_finals[int(0.50 * n_simulations)], 2),
        "final_p95": round(all_finals[min(int(0.95 * n_simulations), n_simulations - 1)], 2),
        "n": n,
        "n_simulations": n_simulations,
    }


def compute_all_metrics(pnl_series: List[float], dates: Optional[List[str]] = None) -> dict:
    """Compute the full risk metric suite in one call."""
    if not pnl_series:
        return {}
    equity = compute_equity_curve(pnl_series)
    dd_series = compute_drawdown_series(equity)
    wins = [p for p in pnl_series if p > 0]
    losses = [p for p in pnl_series if p < 0]
    win_rate = round(len(wins) / len(pnl_series) * 100, 1) if pnl_series else 0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
    return {
        "sharpe": compute_sharpe(pnl_series, dates),
        "sortino": compute_sortino(pnl_series, dates),
        "calmar": compute_calmar(pnl_series, equity, dates),
        "max_drawdown": compute_max_drawdown(equity),
        "max_drawdown_pct": compute_max_drawdown_pct(equity),
        "profit_factor": compute_profit_factor(pnl_series),
        "expectancy": compute_expectancy(pnl_series),
        "kelly_pct": compute_kelly(pnl_series),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "streaks": compute_consecutive_streaks(pnl_series),
        "equity_curve": equity,
        "drawdown_series": dd_series,
    }
