import json
import os
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger('live_trader')

class EquityTracker:
    """
    Tracks the equity curve and drawdown over time.
    """
    def __init__(self, initial_capital=1000000.0, state_file="data/equity_state.json"):
        self.state_file = state_file
        self.data = self._load_state(initial_capital)

    def _load_state(self, initial_capital) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "initial_capital": initial_capital,
            "current_capital": initial_capital,
            "daily_returns": [], # List of {date, pnl, return_pct, trades}
            "peak_capital": initial_capital,
            "max_drawdown_pct": 0.0,
            "inception_date": datetime.now().strftime('%Y-%m-%d'),
            "total_trades": 0,
            "total_wins": 0
        }

    def record_day(self, date: str, pnl: float, trades_closed: int, win_count: int):
        ret_pct = (pnl / self.data['current_capital']) * 100 if self.data['current_capital'] > 0 else 0
        
        self.data['current_capital'] += pnl
        self.data['daily_returns'].append({
            "date": date,
            "pnl": pnl,
            "return_pct": ret_pct,
            "trades": trades_closed
        })
        
        # Update Peak and Drawdown
        if self.data['current_capital'] > self.data['peak_capital']:
            self.data['peak_capital'] = self.data['current_capital']
        
        drawdown = (self.data['peak_capital'] - self.data['current_capital']) / self.data['peak_capital'] * 100
        if drawdown > self.data['max_drawdown_pct']:
            self.data['max_drawdown_pct'] = drawdown
            
        self.data['total_trades'] += trades_closed
        self.data['total_wins'] += win_count
        
        self._save_state()
        logger.info(f"[EQUITY] Day Recorded: {date} | PnL: {pnl:+.2f} | Capital: {self.data['current_capital']:.2f}")

    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_summary(self) -> dict:
        return {
            'current_capital': self.data['current_capital'],
            'total_return_pct': ((self.data['current_capital'] - self.data['initial_capital']) / self.data['initial_capital']) * 100,
            'max_drawdown_pct': self.data['max_drawdown_pct'],
            'win_rate': (self.data['total_wins'] / self.data['total_trades'] * 100) if self.data['total_trades'] > 0 else 0
        }
