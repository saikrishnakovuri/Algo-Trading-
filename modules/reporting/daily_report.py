import os
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger('live_trader')

class DailyReportGenerator:
    """
    Generates performance reports from trade journals.
    """
    def __init__(self, journal_path="trade_journal_v3_ws.csv"):
        self.journal_path = journal_path

    def generate_daily_report(self, date_str: Optional[str] = None, regime_logs: Optional[list] = None) -> dict:
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        if not os.path.exists(self.journal_path):
            return {}
            
        try:
            df = pd.read_csv(self.journal_path)
            day_df = df[df['date'] == date_str]
            
            if day_df.empty:
                return {'date': date_str, 'total_trades': 0}
                
            trades_closed = day_df[day_df['exit_type'].notna()]
            trades_opened = day_df[day_df['exit_type'].isna()]
            
            wins = trades_closed[trades_closed['pnl'] > 0]
            total_pnl = trades_closed['pnl'].sum()
            win_rate = (len(wins) / len(trades_closed) * 100) if not trades_closed.empty else 0
            
            # Strategy Breakdown
            strat_stats = {}
            for strat in day_df['strategy'].unique():
                s_df = day_df[day_df['strategy'] == strat]
                s_closed = s_df[s_df['exit_type'].notna()]
                strat_stats[strat] = {
                    'count': len(s_df),
                    'pnl': s_closed['pnl'].sum(),
                    'win_rate': (len(s_closed[s_closed['pnl'] > 0]) / len(s_closed) * 100) if not s_closed.empty else 0
                }
            
            # Regime Distribution
            regime_dist = {}
            if regime_logs:
                total_logs = len(regime_logs)
                for r in set(regime_logs):
                    regime_dist[r] = (regime_logs.count(r) / total_logs) * 100

            # Portfolio Metrics
            # Peak positions can be estimated from journal if we had entry/exit times
            # Here we just count total symbols traded
            total_symbols = day_df['symbol'].nunique()
            
            # Sharpe Approximation (Simplified: Daily PnL / Volatility of PnL)
            # Hard to do with 1 day of data, but we can do PnL per trade variability
            trade_std = trades_closed['pnl'].std() if len(trades_closed) > 1 else 0
            sharpe_approx = (total_pnl / trade_std) if trade_std > 0 else 0

            best_trade = trades_closed.loc[trades_closed['pnl'].idxmax()] if not trades_closed.empty else None
            worst_trade = trades_closed.loc[trades_closed['pnl'].idxmin()] if not trades_closed.empty else None
            
            return {
                'date': date_str,
                'total_trades': len(day_df),
                'opened': len(trades_opened),
                'closed': len(trades_closed),
                'net_pnl': total_pnl,
                'win_rate': win_rate,
                'strat_stats': strat_stats,
                'regime_dist': regime_dist,
                'total_symbols': total_symbols,
                'sharpe_approx': sharpe_approx,
                'best': best_trade.to_dict() if best_trade is not None else None,
                'worst': worst_trade.to_dict() if worst_trade is not None else None
            }
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return {}

    def format_telegram_message(self, report: dict) -> str:
        if not report or report.get('total_trades', 0) == 0:
            return f"DAILY REPORT | {report.get('date')} | No trades found."
            
        msg = f"══════════════════════════════\n"
        msg += f"DAILY REPORT | {report['date']}\n"
        msg += f"══════════════════════════════\n\n"
        
        msg += f"NET P&L: {report['net_pnl']:+.2f} INR\n"
        msg += f"Win Rate: {report['win_rate']:.1f}%\n"
        msg += f"Trades: {report['closed']} Closed | {report['opened']} Open\n"
        msg += f"Sharpe (Daily): {report['sharpe_approx']:.2f}\n\n"
        
        msg += f"── Strategy Breakdown ──\n"
        for strat, stats in report['strat_stats'].items():
            msg += f"{strat}: {stats['count']} tr | {stats['pnl']:+.2f} | {stats['win_rate']:.0f}% W\n"
            
        if report['regime_dist']:
            msg += f"\n── Regime Distribution ──\n"
            for regime, pct in report['regime_dist'].items():
                msg += f"{regime}: {pct:.0f}%\n"

        if report['best']:
            msg += f"\n── Best & Worst ──\n"
            msg += f"Best: {report['best']['symbol']} {report['best']['pnl']:+.2f} ({report['best']['strategy']})\n"
            msg += f"Worst: {report['worst']['symbol']} {report['worst']['pnl']:+.2f} ({report['worst']['strategy']})\n"
            
        msg += f"\n══════════════════════════════"
        return msg
