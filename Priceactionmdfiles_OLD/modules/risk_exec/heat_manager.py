import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from modules.risk_exec.schemas import HeatCheckResult, ApprovedSignal, OpenPosition

class CorrelationAwareHeatManager:
    """
    Manages portfolio risk caps by sector and correlation.
    """
    
    def __init__(self, config: Dict[str, Any], correlation_matrix_path: Path):
        self.config = config['heat']
        self.matrix_path = correlation_matrix_path
        self.matrix = None
        if self.matrix_path.exists():
            self.matrix = pd.read_parquet(self.matrix_path)
            
    def check_heat(self, signal: ApprovedSignal, current_equity: float, 
                   open_positions: List[OpenPosition], new_risk: float) -> HeatCheckResult:
        
        # 1. Total Open Risk Cap (2.5%)
        current_total_risk = sum([p.metadata.get('risk_amount', 0) for p in open_positions])
        total_heat_pct = (current_total_risk + new_risk) / current_equity * 100
        
        if total_heat_pct > self.config['total_cap_pct']:
            return self._veto("TOTAL_HEAT_EXCEEDED", total_heat_pct)

        # 2. Sector concentration (1.5%)
        # For simplicity, assume signal.metadata includes 'sector'
        sector = signal.metadata.get('sector', 'UNKNOWN')
        sector_risk = sum([p.metadata.get('risk_amount', 0) for p in open_positions if p.metadata.get('sector') == sector])
        sector_heat_pct = (sector_risk + new_risk) / current_equity * 100
        
        if sector_heat_pct > self.config['sector_cap_pct']:
            return self._veto("SECTOR_HEAT_EXCEEDED", total_heat_pct, sector_heat_pct)

        # 3. Single-stock concurrency (Max 1)
        if any(p.symbol == signal.symbol for p in open_positions):
            return self._veto("SINGLE_STOCK_CONCURRENCY", total_heat_pct)

        # 4. Correlation-adjusted heat
        max_rho = 0.0
        if self.matrix is not None and signal.symbol in self.matrix.index:
            for p in open_positions:
                if p.symbol in self.matrix.columns:
                    rho = self.matrix.loc[signal.symbol, p.symbol]
                    max_rho = max(max_rho, abs(rho))
                    
        effective_inc = new_risk * (1.0 + max_rho)
        effective_total_heat = (current_total_risk + effective_inc) / current_equity * 100
        
        if effective_total_heat > self.config['total_cap_pct']:
            return self._veto("CORRELATION_HEAT_EXCEEDED", total_heat_pct, sector_heat_pct, max_rho, effective_total_heat)

        return HeatCheckResult(
            allow=True,
            total_heat_after=round(total_heat_pct, 2),
            sector_heat_after=round(sector_heat_pct, 2),
            max_correlation=round(max_rho, 2),
            effective_heat_after=round(effective_total_heat, 2),
            veto_reason=None
        )

    def _veto(self, reason: str, total: float, sector: float = 0, rho: float = 0, effective: float = 0) -> HeatCheckResult:
        return HeatCheckResult(False, total, sector, rho, effective, reason)
