
Action: file_editor create /app/GEMINI_EDGE_MONITOR.md --file-text "# EDGE STRENGTH MONITOR — Statistical Validation & Decay Detection
## Know EXACTLY when your edge is real, weakening, or dead

---

## WHAT THIS DOES

This module sits alongside your strategy engine and continuously answers 3 questions:

1. **\"Is my edge statistically real?\"** — Not just profitable by luck, but provably different from random
2. **\"Is my edge decaying?\"** — Catching degradation BEFORE it turns into losses  
3. **\"When should I stop trading and re-optimize?\"** — Hard quantitative triggers, no guesswork

---

## PART 1: BUILD THE EDGE MONITOR

### File: `edge_monitor.py`

Create this file in your engine directory. It should be importable and runnable standalone.

```python
\"\"\"
EDGE STRENGTH MONITOR
=====================
Statistical validation and real-time decay detection for trading edges.

Usage:
    from edge_monitor import EdgeMonitor
    
    monitor = EdgeMonitor(trades_csv='backtest_detailed_results.csv', capital=500000)
    report = monitor.full_report()
    print(report)
    
    # Real-time check during paper trading:
    should_trade = monitor.is_edge_alive()
\"\"\"

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class EdgeMonitor:
    
    def __init__(self, trades_csv: str = None, trades_df: pd.DataFrame = None, capital: float = 500000):
        \"\"\"
        Initialize with either a CSV path or a DataFrame of trades.
        Expected columns: entry_time, exit_time, result, pnl, pnl_pct, strategy, confidence
        \"\"\"
        if trades_df is not None:
            self.trades = trades_df.copy()
        elif trades_csv:
            self.trades = pd.read_csv(trades_csv)
        else:
            raise ValueError(\"Provide either trades_csv or trades_df\")
        
        self.capital = capital
        self.trades['entry_time'] = pd.to_datetime(self.trades['entry_time'])
        self.trades['exit_time'] = pd.to_datetime(self.trades['exit_time'])
        self.pnl_series = self.trades['pnl'].values
        self.n_trades = len(self.trades)

    # ================================================================
    # SECTION 1: IS THE EDGE STATISTICALLY REAL?
    # ================================================================
    
    def t_test_vs_zero(self) -> Dict:
        \"\"\"
        One-sample t-test: Is the mean P&L significantly different from zero?
        H0: Mean P&L = 0 (no edge, random trading)
        H1: Mean P&L > 0 (edge exists)
        
        Returns dict with t-statistic, p-value, and interpretation.
        \"\"\"
        t_stat, p_value_two_tail = stats.ttest_1samp(self.pnl_series, 0)
        p_value_one_tail = p_value_two_tail / 2  # We only care about positive edge
        
        mean_pnl = np.mean(self.pnl_series)
        
        if mean_pnl > 0 and p_value_one_tail < 0.05:
            verdict = \"EDGE IS STATISTICALLY SIGNIFICANT (p < 0.05)\"
            confidence_level = \"95%+\"
        elif mean_pnl > 0 and p_value_one_tail < 0.10:
            verdict = \"EDGE IS MARGINALLY SIGNIFICANT (p < 0.10)\"
            confidence_level = \"90%\"
        else:
            verdict = \"NO STATISTICALLY SIGNIFICANT EDGE DETECTED\"
            confidence_level = \"< 90%\"
        
        return {
            \"test\": \"One-sample t-test (mean P&L vs zero)\",
            \"t_statistic\": round(t_stat, 4),
            \"p_value_one_tail\": round(p_value_one_tail, 6),
            \"mean_pnl\": round(mean_pnl, 2),
            \"n_trades\": self.n_trades,
            \"confidence_level\": confidence_level,
            \"verdict\": verdict
        }
    
    def bootstrap_confidence_interval(self, n_bootstrap: int = 10000, ci_level: float = 0.95) -> Dict:
        \"\"\"
        Bootstrap resampling to estimate the confidence interval of expected P&L per trade.
        
        This is MORE ROBUST than the t-test because:
        - Doesn't assume normal distribution
        - Works with small samples
        - Handles fat tails (which trading P&L always has)
        \"\"\"
        bootstrap_means = []
        
        for _ in range(n_bootstrap):
            sample = np.random.choice(self.pnl_series, size=self.n_trades, replace=True)
            bootstrap_means.append(np.mean(sample))
        
        bootstrap_means = np.array(bootstrap_means)
        
        alpha = 1 - ci_level
        ci_lower = np.percentile(bootstrap_means, alpha / 2 * 100)
        ci_upper = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)
        
        # What % of bootstrap samples showed positive mean?
        pct_positive = (bootstrap_means > 0).mean() * 100
        
        if ci_lower > 0:
            verdict = f\"EDGE CONFIRMED: {ci_level*100:.0f}% CI entirely above zero\"
        elif pct_positive > 90:
            verdict = f\"EDGE LIKELY: {pct_positive:.1f}% of simulations profitable\"
        elif pct_positive > 70:
            verdict = f\"EDGE UNCERTAIN: Only {pct_positive:.1f}% of simulations profitable\"
        else:
            verdict = f\"NO EDGE: Only {pct_positive:.1f}% of simulations profitable\"
        
        return {
            \"test\": f\"Bootstrap Confidence Interval ({n_bootstrap} resamples)\",
            \"mean_pnl_per_trade\": round(np.mean(self.pnl_series), 2),
            f\"ci_{ci_level*100:.0f}_lower\": round(ci_lower, 2),
            f\"ci_{ci_level*100:.0f}_upper\": round(ci_upper, 2),
            \"pct_positive_simulations\": round(pct_positive, 1),
            \"verdict\": verdict
        }
    
    def monte_carlo_equity_curves(self, n_simulations: int = 1000, n_trades_forward: int = 200) -> Dict:
        \"\"\"
        Monte Carlo simulation: Randomly reorder trades to generate 1000 possible equity curves.
        
        This answers: \"Given these trades in ANY order, what's the range of outcomes?\"
        
        Key outputs:
        - Probability of ruin (capital going to zero or below threshold)
        - Expected P&L range (5th to 95th percentile)
        - Worst-case drawdown distribution
        \"\"\"
        final_capitals = []
        max_drawdowns = []
        ruin_count = 0
        ruin_threshold = self.capital * 0.50  # Ruin = losing 50% of capital
        
        for _ in range(n_simulations):
            # Randomly sample trades WITH replacement to simulate future
            sampled_pnls = np.random.choice(self.pnl_series, size=n_trades_forward, replace=True)
            
            equity = self.capital
            peak = equity
            max_dd = 0
            
            for pnl in sampled_pnls:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd
                
                if equity <= ruin_threshold:
                    ruin_count += 1
                    break
            
            final_capitals.append(equity)
            max_drawdowns.append(max_dd * 100)
        
        final_capitals = np.array(final_capitals)
        max_drawdowns = np.array(max_drawdowns)
        
        return {
            \"test\": f\"Monte Carlo Simulation ({n_simulations} paths, {n_trades_forward} trades each)\",
            \"initial_capital\": self.capital,
            \"median_final_capital\": round(np.median(final_capitals), 2),
            \"p5_final_capital\": round(np.percentile(final_capitals, 5), 2),
            \"p25_final_capital\": round(np.percentile(final_capitals, 25), 2),
            \"p75_final_capital\": round(np.percentile(final_capitals, 75), 2),
            \"p95_final_capital\": round(np.percentile(final_capitals, 95), 2),
            \"probability_of_profit\": round((final_capitals > self.capital).mean() * 100, 1),
            \"probability_of_ruin\": round(ruin_count / n_simulations * 100, 2),
            \"median_max_drawdown_pct\": round(np.median(max_drawdowns), 1),
            \"p95_max_drawdown_pct\": round(np.percentile(max_drawdowns, 95), 1),
            \"verdict\": f\"{'VIABLE' if (final_capitals > self.capital).mean() > 0.6 else 'RISKY'}: \"
                       f\"{(final_capitals > self.capital).mean()*100:.0f}% chance of profit over {n_trades_forward} trades\"
        }
    
    def kelly_criterion(self) -> Dict:
        \"\"\"
        Calculate optimal position size using Kelly Criterion.
        
        Kelly % = W - (1-W)/R
        Where:
          W = win rate
          R = avg win / avg loss ratio
        
        Half-Kelly is recommended for real trading (less aggressive).
        \"\"\"
        wins = self.trades[self.trades['result'] == 'WIN']['pnl']
        losses = self.trades[self.trades['result'] == 'LOSS']['pnl']
        
        if len(wins) == 0 or len(losses) == 0:
            return {\"verdict\": \"INSUFFICIENT DATA: Need both wins and losses\"}
        
        win_rate = len(wins) / self.n_trades
        avg_win = wins.mean()
        avg_loss = abs(losses.mean())
        rr_ratio = avg_win / avg_loss
        
        kelly_pct = win_rate - ((1 - win_rate) / rr_ratio)
        half_kelly = kelly_pct / 2
        quarter_kelly = kelly_pct / 4
        
        if kelly_pct <= 0:
            verdict = \"KELLY SAYS DON'T TRADE: Negative expectancy\"
        elif kelly_pct < 0.05:
            verdict = \"TINY EDGE: Kelly suggests very small position sizes\"
        elif kelly_pct < 0.15:
            verdict = \"MODERATE EDGE: Use Half-Kelly for safety\"
        else:
            verdict = \"STRONG EDGE: Use Quarter-Kelly to be conservative\"
        
        return {
            \"test\": \"Kelly Criterion Position Sizing\",
            \"win_rate\": round(win_rate * 100, 1),
            \"risk_reward_ratio\": round(rr_ratio, 2),
            \"full_kelly_pct\": round(kelly_pct * 100, 2),
            \"half_kelly_pct\": round(half_kelly * 100, 2),
            \"quarter_kelly_pct\": round(quarter_kelly * 100, 2),
            \"current_risk_pct\": 1.0,  # Your current 1% risk
            \"recommended_risk_pct\": round(max(half_kelly * 100, 0.25), 2),
            \"verdict\": verdict
        }

    # ================================================================
    # SECTION 2: IS THE EDGE DECAYING?
    # ================================================================
    
    def rolling_edge_decay(self, window: int = 20) -> Dict:
        \"\"\"
        Calculate rolling statistics over the last N trades to detect decay.
        
        Compares:
        - First half of trades vs second half
        - Rolling win rate trend
        - Rolling P&L trend
        - Rolling profit factor trend
        \"\"\"
        half = self.n_trades // 2
        first_half = self.pnl_series[:half]
        second_half = self.pnl_series[half:]
        
        # Welch's t-test: Are the two halves significantly different?
        t_stat, p_value = stats.ttest_ind(first_half, second_half, equal_var=False)
        
        # Rolling metrics
        rolling_pnl = pd.Series(self.pnl_series).rolling(window).mean()
        rolling_wr = pd.Series([1 if p > 0 else 0 for p in self.pnl_series]).rolling(window).mean()
        
        # Trend: Is the rolling mean P&L declining?
        recent_trend = rolling_pnl.iloc[-window:].values
        recent_trend_clean = recent_trend[~np.isnan(recent_trend)]
        
        if len(recent_trend_clean) >= 5:
            slope, _, r_value, p_trend, _ = stats.linregress(
                range(len(recent_trend_clean)), recent_trend_clean
            )
            trend_direction = \"IMPROVING\" if slope > 0 else \"DECLINING\"
        else:
            slope = 0
            r_value = 0
            p_trend = 1
            trend_direction = \"INSUFFICIENT DATA\"
        
        first_half_mean = np.mean(first_half)
        second_half_mean = np.mean(second_half)
        
        if second_half_mean > first_half_mean * 1.1:
            decay_verdict = \"EDGE STRENGTHENING\"
        elif second_half_mean > first_half_mean * 0.7:
            decay_verdict = \"EDGE STABLE\"
        elif second_half_mean > 0:
            decay_verdict = \"EDGE WEAKENING — monitor closely\"
        else:
            decay_verdict = \"EDGE DECAYING — consider stopping\"
        
        return {
            \"test\": \"Rolling Edge Decay Analysis\",
            \"first_half_avg_pnl\": round(first_half_mean, 2),
            \"second_half_avg_pnl\": round(second_half_mean, 2),
            \"change_pct\": round((second_half_mean - first_half_mean) / abs(first_half_mean) * 100, 1) if first_half_mean != 0 else 0,
            \"halves_t_test_p_value\": round(p_value, 4),
            \"recent_trend_slope\": round(slope, 2),
            \"recent_trend_direction\": trend_direction,
            \"recent_trend_r_squared\": round(r_value**2, 4),
            \"verdict\": decay_verdict
        }
    
    def consecutive_loss_analysis(self) -> Dict:
        \"\"\"
        Analyze loss streaks to detect if something changed.
        
        Normal edge: Loss streaks of 3-5 are expected
        Decaying edge: Loss streaks of 8+ start appearing
        Dead edge: Loss streaks of 10+ with no recovery
        \"\"\"
        streaks = []
        current_streak = 0
        max_streak = 0
        
        for pnl in self.pnl_series:
            if pnl < 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
        if current_streak > 0:
            streaks.append(current_streak)
        
        # Is the current/recent streak the worst?
        recent_10 = self.pnl_series[-10:]
        recent_losses_in_row = 0
        for p in reversed(recent_10):
            if p < 0:
                recent_losses_in_row += 1
            else:
                break
        
        if max_streak <= 5:
            streak_verdict = \"NORMAL — loss streaks within expected range\"
        elif max_streak <= 8:
            streak_verdict = \"WARNING — longer-than-normal loss streaks detected\"
        elif max_streak <= 12:
            streak_verdict = \"DANGER — edge may be failing\"
        else:
            streak_verdict = \"CRITICAL — edge is likely dead, stop trading immediately\"
        
        return {
            \"test\": \"Consecutive Loss Streak Analysis\",
            \"max_loss_streak\": max_streak,
            \"avg_loss_streak\": round(np.mean(streaks), 1) if streaks else 0,
            \"current_loss_streak\": recent_losses_in_row,
            \"total_loss_streaks\": len(streaks),
            \"verdict\": streak_verdict
        }

    # ================================================================
    # SECTION 3: WHEN TO STOP AND RE-OPTIMIZE
    # ================================================================
    
    def generate_stop_triggers(self) -> Dict:
        \"\"\"
        Calculate specific quantitative triggers for when to STOP trading.
        
        Based on the edge's historical performance, set hard limits that
        mean the edge has likely decayed beyond recovery.
        \"\"\"
        mean_pnl = np.mean(self.pnl_series)
        std_pnl = np.std(self.pnl_series)
        
        wins = self.trades[self.trades['result'] == 'WIN']
        win_rate = len(wins) / self.n_trades
        
        # Calculate expected drawdown at 2 sigma
        expected_dd_2sigma = mean_pnl - 2 * std_pnl
        
        # Stop triggers
        triggers = {
            \"test\": \"Automated Stop Triggers\",
            
            # Trigger 1: Win rate drops below threshold
            \"current_win_rate\": round(win_rate * 100, 1),
            \"stop_if_win_rate_below\": round(max(win_rate * 100 - 15, 20), 1),
            
            # Trigger 2: Rolling 20-trade P&L turns negative
            \"rolling_20_pnl\": round(np.mean(self.pnl_series[-20:]) if self.n_trades >= 20 else mean_pnl, 2),
            \"stop_if_rolling_20_pnl_below\": 0,
            
            # Trigger 3: Max consecutive losses exceeds threshold
            \"stop_if_consecutive_losses_exceed\": 8,
            
            # Trigger 4: Drawdown exceeds threshold
            \"stop_if_drawdown_exceeds_pct\": 25.0,
            
            # Trigger 5: Monthly loss exceeds threshold
            \"stop_if_monthly_loss_exceeds\": round(self.capital * 0.10, 0),
            
            # Trigger 6: Weekly loss limit
            \"stop_if_weekly_loss_exceeds\": round(self.capital * 0.05, 0),
        }
        
        # Check which triggers are currently active
        active_triggers = []
        if win_rate * 100 < triggers[\"stop_if_win_rate_below\"]:
            active_triggers.append(\"WIN_RATE_TOO_LOW\")
        if triggers[\"rolling_20_pnl\"] < 0:
            active_triggers.append(\"ROLLING_PNL_NEGATIVE\")
        
        triggers[\"active_triggers\"] = active_triggers if active_triggers else [\"NONE — All clear\"]
        triggers[\"verdict\"] = \"STOP TRADING\" if active_triggers else \"CONTINUE TRADING\"
        
        return triggers

    # ================================================================
    # MASTER REPORT
    # ================================================================
    
    def is_edge_alive(self) -> bool:
        \"\"\"Quick boolean check: Should I keep trading?\"\"\"
        triggers = self.generate_stop_triggers()
        return triggers[\"verdict\"] == \"CONTINUE TRADING\"
    
    def full_report(self) -> str:
        \"\"\"Generate the complete edge strength report.\"\"\"
        
        report = []
        report.append(\"=\" * 70)
        report.append(\"  EDGE STRENGTH MONITOR — FULL REPORT\")
        report.append(f\"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\")
        report.append(f\"  Trades analyzed: {self.n_trades}\")
        report.append(f\"  Capital: ₹{self.capital:,.0f}\")
        report.append(\"=\" * 70)
        
        # 1. Statistical Significance
        report.append(\"\n\" + \"─\" * 70)
        report.append(\"  SECTION 1: IS THE EDGE STATISTICALLY REAL?\")
        report.append(\"─\" * 70)
        
        t_test = self.t_test_vs_zero()
        report.append(f\"\n  T-Test vs Zero:\")
        report.append(f\"    Mean P&L per trade: ₹{t_test['mean_pnl']:,.2f}\")
        report.append(f\"    t-statistic: {t_test['t_statistic']}\")
        report.append(f\"    p-value (one-tail): {t_test['p_value_one_tail']}\")
        report.append(f\"    Confidence: {t_test['confidence_level']}\")
        report.append(f\"    >>> {t_test['verdict']}\")
        
        bootstrap = self.bootstrap_confidence_interval()
        report.append(f\"\n  Bootstrap Confidence Interval (10,000 resamples):\")
        report.append(f\"    Mean P&L per trade: ₹{bootstrap['mean_pnl_per_trade']:,.2f}\")
        report.append(f\"    95% CI: [₹{bootstrap['ci_95_lower']:,.2f}, ₹{bootstrap['ci_95_upper']:,.2f}]\")
        report.append(f\"    Positive simulations: {bootstrap['pct_positive_simulations']}%\")
        report.append(f\"    >>> {bootstrap['verdict']}\")
        
        mc = self.monte_carlo_equity_curves()
        report.append(f\"\n  Monte Carlo Simulation (1,000 paths, 200 trades):\")
        report.append(f\"    Median final capital: ₹{mc['median_final_capital']:,.0f}\")
        report.append(f\"    5th percentile: ₹{mc['p5_final_capital']:,.0f}\")
        report.append(f\"    95th percentile: ₹{mc['p95_final_capital']:,.0f}\")
        report.append(f\"    Probability of profit: {mc['probability_of_profit']}%\")
        report.append(f\"    Probability of ruin (50% loss): {mc['probability_of_ruin']}%\")
        report.append(f\"    95th percentile max drawdown: {mc['p95_max_drawdown_pct']}%\")
        report.append(f\"    >>> {mc['verdict']}\")
        
        kelly = self.kelly_criterion()
        report.append(f\"\n  Kelly Criterion:\")
        report.append(f\"    Win rate: {kelly.get('win_rate', 'N/A')}%\")
        report.append(f\"    Risk-reward: {kelly.get('risk_reward_ratio', 'N/A')}:1\")
        report.append(f\"    Full Kelly: {kelly.get('full_kelly_pct', 'N/A')}%\")
        report.append(f\"    Half Kelly: {kelly.get('half_kelly_pct', 'N/A')}%\")
        report.append(f\"    Current risk: {kelly.get('current_risk_pct', 'N/A')}%\")
        report.append(f\"    Recommended: {kelly.get('recommended_risk_pct', 'N/A')}%\")
        report.append(f\"    >>> {kelly['verdict']}\")
        
        # 2. Decay Detection
        report.append(\"\n\" + \"─\" * 70)
        report.append(\"  SECTION 2: IS THE EDGE DECAYING?\")
        report.append(\"─\" * 70)
        
        decay = self.rolling_edge_decay()
        report.append(f\"\n  Rolling Decay Analysis:\")
        report.append(f\"    First half avg P&L: ₹{decay['first_half_avg_pnl']:,.2f}\")
        report.append(f\"    Second half avg P&L: ₹{decay['second_half_avg_pnl']:,.2f}\")
        report.append(f\"    Change: {decay['change_pct']}%\")
        report.append(f\"    Recent trend: {decay['recent_trend_direction']} (slope: {decay['recent_trend_slope']})\")
        report.append(f\"    >>> {decay['verdict']}\")
        
        streaks = self.consecutive_loss_analysis()
        report.append(f\"\n  Loss Streak Analysis:\")
        report.append(f\"    Max loss streak: {streaks['max_loss_streak']}\")
        report.append(f\"    Avg loss streak: {streaks['avg_loss_streak']}\")
        report.append(f\"    Current streak: {streaks['current_loss_streak']}\")
        report.append(f\"    >>> {streaks['verdict']}\")
        
        # 3. Stop Triggers
        report.append(\"\n\" + \"─\" * 70)
        report.append(\"  SECTION 3: STOP TRIGGERS\")
        report.append(\"─\" * 70)
        
        triggers = self.generate_stop_triggers()
        report.append(f\"\n  Current Status:\")
        report.append(f\"    Win rate: {triggers['current_win_rate']}% (stop if < {triggers['stop_if_win_rate_below']}%)\")
        report.append(f\"    Rolling 20-trade P&L: ₹{triggers['rolling_20_pnl']:,.2f} (stop if < 0)\")
        report.append(f\"    Max consecutive losses allowed: {triggers['stop_if_consecutive_losses_exceed']}\")
        report.append(f\"    Max drawdown allowed: {triggers['stop_if_drawdown_exceeds_pct']}%\")
        report.append(f\"    Max monthly loss: ₹{triggers['stop_if_monthly_loss_exceeds']:,.0f}\")
        report.append(f\"    Max weekly loss: ₹{triggers['stop_if_weekly_loss_exceeds']:,.0f}\")
        report.append(f\"    Active triggers: {triggers['active_triggers']}\")
        report.append(f\"    >>> {triggers['verdict']}\")
        
        # Final Verdict
        report.append(\"\n\" + \"=\" * 70)
        report.append(\"  FINAL VERDICT\")
        report.append(\"=\" * 70)
        
        is_alive = self.is_edge_alive()
        if is_alive and mc['probability_of_profit'] > 60 and bootstrap['pct_positive_simulations'] > 70:
            report.append(\"  STATUS: GREEN — Edge is alive. Continue trading.\")
        elif is_alive:
            report.append(\"  STATUS: YELLOW — Edge exists but weak. Trade with reduced size.\")
        else:
            report.append(\"  STATUS: RED — Edge compromised. STOP trading. Re-optimize.\")
        
        report.append(\"=\" * 70)
        
        return \"\n\".join(report)


# ================================================================
# STANDALONE EXECUTION
# ================================================================

if __name__ == \"__main__\":
    import sys
    
    csv_path = sys.argv[1] if len(sys.argv) > 1 else \"backtest_detailed_results.csv\"
    capital = float(sys.argv[2]) if len(sys.argv) > 2 else 500000
    
    print(f\"Loading trades from: {csv_path}\")
    monitor = EdgeMonitor(trades_csv=csv_path, capital=capital)
    print(monitor.full_report())
```

---

## PART 2: INTEGRATE WITH PAPER TRADING

### File: `paper_trading_with_monitor.py`

This wraps your paper trading bot with real-time edge monitoring:

```python
\"\"\"
Paper trading with real-time edge monitoring.
Automatically stops trading when edge decays.
\"\"\"

from edge_monitor import EdgeMonitor
import pandas as pd


class MonitoredPaperTrader:
    
    def __init__(self, engine, broker, config, capital=500000):
        self.engine = engine
        self.broker = broker
        self.config = config
        self.capital = capital
        self.trades = []
        self.monitor = None
        
        # Check frequency: After every N trades
        self.check_every_n = 10
        self.min_trades_for_check = 20
    
    def on_trade_complete(self, trade_result: dict):
        \"\"\"Called after every completed trade.\"\"\"
        self.trades.append(trade_result)
        
        # Run edge check every N trades
        if len(self.trades) >= self.min_trades_for_check and len(self.trades) % self.check_every_n == 0:
            self._check_edge()
    
    def _check_edge(self):
        \"\"\"Run the edge monitor and decide whether to continue.\"\"\"
        trades_df = pd.DataFrame(self.trades)
        self.monitor = EdgeMonitor(trades_df=trades_df, capital=self.capital)
        
        # Quick check
        if not self.monitor.is_edge_alive():
            print(\"\n\" + \"!\" * 60)
            print(\"  EDGE MONITOR: STOP TRADING TRIGGERED\")
            print(\"!\" * 60)
            print(self.monitor.full_report())
            self._pause_trading()
            return
        
        # Periodic status
        triggers = self.monitor.generate_stop_triggers()
        bootstrap = self.monitor.bootstrap_confidence_interval()
        
        print(f\"\n  [Edge Monitor] After {len(self.trades)} trades:\")
        print(f\"    Win rate: {triggers['current_win_rate']}%\")
        print(f\"    Rolling 20 P&L: ₹{triggers['rolling_20_pnl']:,.0f}\")
        print(f\"    Bootstrap positive: {bootstrap['pct_positive_simulations']}%\")
        print(f\"    Status: {'GREEN' if bootstrap['pct_positive_simulations'] > 70 else 'YELLOW'}\")
    
    def _pause_trading(self):
        \"\"\"Stop placing new trades until manual review.\"\"\"
        self.config['trading_paused'] = True
        print(\"  Trading PAUSED. Run edge_monitor.py for full report.\")
        print(\"  To resume: set config['trading_paused'] = False after review.\")
    
    def daily_report(self):
        \"\"\"End-of-day edge health summary.\"\"\"
        if len(self.trades) < self.min_trades_for_check:
            print(f\"  [Edge Monitor] Need {self.min_trades_for_check - len(self.trades)} more trades for analysis.\")
            return
        
        trades_df = pd.DataFrame(self.trades)
        monitor = EdgeMonitor(trades_df=trades_df, capital=self.capital)
        print(monitor.full_report())
```

---

## PART 3: HOW TO USE IT

### After Backtest
```bash
# Run on your backtest results
python edge_monitor.py backtest_detailed_results.csv 500000
```

### During Paper Trading
```python
# Initialize
trader = MonitoredPaperTrader(engine, broker, config, capital=500000)

# After each trade completes:
trader.on_trade_complete(trade_result)
# ^^^ This auto-checks edge every 10 trades

# End of day:
trader.daily_report()
```

### Interpreting the Report

```
SECTION 1: IS THE EDGE REAL?
  - T-test p-value < 0.05  →  Edge is statistically proven
  - Bootstrap > 70% positive  →  Edge is robust
  - Monte Carlo profit prob > 60%  →  Edge survives randomization
  - Kelly > 0%  →  Positive expectancy confirmed

SECTION 2: IS IT DECAYING?
  - Second half P&L > first half  →  IMPROVING (great)
  - Second half P&L > 70% of first  →  STABLE (fine)
  - Second half P&L < 50% of first  →  DECAYING (reduce size)
  - Loss streak > 8  →  WARNING
  - Loss streak > 12  →  STOP

SECTION 3: WHEN TO STOP
  - Any active trigger  →  STOP and investigate
  - All clear  →  Continue trading
```

---

## PART 4: MONTHLY RE-OPTIMIZATION SCHEDULE

Build this into your workflow:

```
Week 1-4: Paper trade with edge monitor running
  → If GREEN: Continue
  → If YELLOW: Reduce position size to half
  → If RED: Stop. Run full_report(). Investigate.

Month-end:
  → Run full_report() on the month's trades
  → Compare to backtest expectations
  → If PF dropped below 1.0: Re-run Phase 3 optimization
  → If PF > 1.3: Consider increasing to 1.5% risk per trade
  → If Monte Carlo ruin probability > 10%: Reduce risk to 0.5%

Quarter-end:
  → Full backtest re-validation with latest 3 months of data
  → Re-optimize ATR multiplier, time window, strategy list
  → Update stop triggers based on new data
```

---

## DEPENDENCIES

The edge monitor requires `scipy`. Add to requirements:
```
pip install scipy pandas numpy
```

No other external dependencies. No API keys needed. Runs locally.

---

## BUILD THIS FILE, TEST IT ON THE CURRENT `backtest_detailed_results.csv`, AND PRINT THE FULL REPORT. GO.
"
Observation: Create successful: /app/GEMINI_EDGE_MONITOR.md