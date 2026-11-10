import os
import yaml
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger('live_trader')

class PortfolioManager:
    """
    Central portfolio risk manager.
    Checks correlation, sector exposure, directional bias, and circuit breakers.
    """
    def __init__(self, config_path="config/portfolio_limits.yaml", universe_path="config/universe_full.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)['portfolio_limits']
        
        with open(universe_path, "r") as f:
            self.universe = yaml.safe_load(f)['universe']
            
        self.open_positions: Dict[str, dict] = {} # {trade_key: {symbol, sector, direction, capital, beta}}
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_paused = False
        self.pause_until: Optional[datetime] = None
        
        # Load correlation matrix if enabled
        self.correlation_matrix = {}
        if self.config['correlation']['enabled']:
            corr_file = self.config['correlation']['correlation_matrix_file']
            if os.path.exists(corr_file):
                try:
                    with open(corr_file, 'r') as f:
                        data = json.load(f)
                        self.correlation_matrix = data.get('matrix', {})
                except Exception as e:
                    logger.error(f"Error loading correlation matrix: {e}")

    def can_take_trade(self, symbol: str, direction: str, capital_required: float) -> Tuple[bool, str]:
        """
        Main entry gate for new trades. Returns (allowed, reason).
        """
        if not self.config['enabled']:
            return True, "PM_DISABLED"

        # 1. Circuit Breaker Check
        allowed, reason = self._check_circuit_breaker()
        if not allowed: return False, reason

        # 2. Sector Limit Check
        allowed, reason = self._check_sector_limit(symbol)
        if not allowed: return False, reason

        # 3. Directional Limit Check
        allowed, reason = self._check_directional_limit(direction)
        if not allowed: return False, reason

        # 4. Single Stock Limit Check
        allowed, reason = self._check_single_stock_limit(symbol, capital_required)
        if not allowed: return False, reason

        # 5. Beta Exposure Check
        allowed, reason = self._check_beta_exposure(symbol, direction)
        if not allowed: return False, reason

        # 6. Correlation Check
        allowed, reason = self._check_correlation(symbol)
        if not allowed: return False, reason

        return True, "ALL_CHECKS_PASSED"

    def _check_circuit_breaker(self) -> Tuple[bool, str]:
        # Daily Loss Limit (approximate based on closed trades pnl)
        # Note: capital would ideally come from config or be passed in
        total_capital = 1000000.0 # Placeholder
        loss_limit = total_capital * (self.config['circuit_breaker']['daily_loss_limit_pct'] / 100.0)
        
        if self.daily_pnl <= -loss_limit:
            return False, "DAILY_LOSS_LIMIT_HIT"
            
        if self.is_paused:
            if datetime.now() < self.pause_until:
                return False, f"PAUSED_UNTIL_{self.pause_until.strftime('%H:%M')}"
            else:
                self.is_paused = False
                
        return True, ""

    def _check_sector_limit(self, symbol: str) -> Tuple[bool, str]:
        mapping = self.universe['mappings'].get(symbol, {})
        sector = mapping.get('sector', 'UNKNOWN')
        
        if sector == 'UNKNOWN': return True, "" # Don't block unknowns
        
        count = sum(1 for p in self.open_positions.values() if p['sector'] == sector)
        if count >= self.config['sector_limits']['max_per_sector']:
            return False, f"SECTOR_FULL:{sector}({count})"
            
        return True, ""

    def _check_directional_limit(self, direction: str) -> Tuple[bool, str]:
        longs = sum(1 for p in self.open_positions.values() if p['direction'] == 'CE')
        shorts = sum(1 for p in self.open_positions.values() if p['direction'] == 'PE')
        
        if direction == 'CE' and longs >= self.config['directional']['max_long_positions']:
            return False, "MAX_LONGS_REACHED"
        if direction == 'PE' and shorts >= self.config['directional']['max_short_positions']:
            return False, "MAX_SHORTS_REACHED"
            
        return True, ""

    def _check_single_stock_limit(self, symbol: str, capital: float) -> Tuple[bool, str]:
        total_capital = 1000000.0 # Placeholder
        max_cap = total_capital * (self.config['single_stock']['max_capital_per_stock_pct'] / 100.0)
        
        if capital > max_cap:
            return False, f"CAPITAL_LIMIT_EXCEEDED:{capital:.0f}>{max_cap:.0f}"
            
        return True, ""

    def _check_beta_exposure(self, symbol: str, direction: str) -> Tuple[bool, str]:
        if not self.config['beta_exposure']['enabled']: return True, ""
        
        # Calculate current portfolio beta
        # This is complex without real-time capital weights, so we'll simplify
        current_beta = sum(p['beta'] for p in self.open_positions.values()) / max(1, len(self.open_positions))
        
        new_stock_beta = self.universe['mappings'].get(symbol, {}).get('beta_base', 1.0)
        # If short, beta is negative
        if direction == 'PE': new_stock_beta = -new_stock_beta
        
        new_total_beta = (sum(p['beta'] for p in self.open_positions.values()) + new_stock_beta) / (len(self.open_positions) + 1)
        
        if abs(new_total_beta) > self.config['beta_exposure']['max_portfolio_beta']:
            return False, f"BETA_EXCEEDED:{new_total_beta:.2f}"
            
        return True, ""

    def _check_correlation(self, symbol: str) -> Tuple[bool, str]:
        if not self.config['correlation']['enabled'] or not self.correlation_matrix:
            return True, ""
            
        current_symbols = [p['symbol'] for p in self.open_positions.values()]
        if not current_symbols: return True, ""
        
        correlations = []
        for s in current_symbols:
            # Check pairwise correlation
            corr = self.correlation_matrix.get(symbol, {}).get(s, 0.0)
            correlations.append(corr)
            
        avg_corr = sum(correlations) / len(correlations)
        if avg_corr > self.config['correlation']['max_portfolio_correlation']:
            return False, f"HIGH_CORRELATION:{avg_corr:.2f}"
            
        return True, ""

    def on_trade_opened(self, trade_key: str, symbol: str, direction: str, capital: float):
        mapping = self.universe['mappings'].get(symbol, {})
        sector = mapping.get('sector', 'UNKNOWN')
        beta = mapping.get('beta_base', 1.0)
        if direction == 'PE': beta = -beta
        
        self.open_positions[trade_key] = {
            'symbol': symbol,
            'sector': sector,
            'direction': direction,
            'capital': capital,
            'beta': beta
        }
        logger.info(f"[PORTFOLIO] Position Added: {symbol} | Sector: {sector} | Beta: {beta:.2f}")

    def on_trade_closed(self, trade_key: str, pnl: float):
        if trade_key in self.open_positions:
            pos = self.open_positions.pop(trade_key)
            self.daily_pnl += pnl
            
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
                
            # Circuit Breaker Check
            if self.consecutive_losses >= self.config['circuit_breaker']['consecutive_loss_limit']:
                self.is_paused = True
                self.pause_until = datetime.now() + timedelta(minutes=self.config['circuit_breaker']['pause_duration_minutes'])
                logger.warning(f"[PORTFOLIO] CIRCUIT BREAKER: {self.consecutive_losses} losses. Pausing until {self.pause_until.strftime('%H:%M')}")
                
            logger.info(f"[PORTFOLIO] Position Removed: {pos['symbol']} | PnL: {pnl:+.2f} | Daily: {self.daily_pnl:+.2f}")

    def on_day_reset(self):
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_paused = False
        self.pause_until = None
        self.open_positions = {}
        logger.info("[PORTFOLIO] Daily metrics reset.")

    def get_portfolio_summary(self) -> dict:
        longs = sum(1 for p in self.open_positions.values() if p['direction'] == 'CE')
        shorts = sum(1 for p in self.open_positions.values() if p['direction'] == 'PE')
        return {
            'open_positions': len(self.open_positions),
            'long_count': longs,
            'short_count': shorts,
            'daily_pnl': self.daily_pnl,
            'is_paused': self.is_paused,
            'consecutive_losses': self.consecutive_losses
        }
