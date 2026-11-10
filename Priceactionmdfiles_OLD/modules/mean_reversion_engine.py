"""
Mean Reversion Engine (Option 3)
═══════════════════════════════════
Fades overextended moves at statistical extremes.
"""

import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class MeanReversionSignal:
    """Output of mean reversion signal detection."""
    symbol: str
    timestamp: pd.Timestamp
    signal_type: str           # e.g., "BB_REVERSION", "VWAP_REVERSION", "RSI_EXTREME", "CONFLUENCE"
    direction: str             # "LONG" (fade down-move) or "SHORT" (fade up-move)
    score: float               # composite confluence score
    confidence: float          # score / max_possible_score (0.0 to 1.0)
    entry_price: float         # current price (enter at market)
    sl_price: float            # beyond the extreme band
    target_price: float        # the MEAN (VWAP or BB midline)
    target_r: float            # R-multiple
    signal_details: Dict = field(default_factory=dict)  # which signals fired
    indicator_state: Dict = field(default_factory=dict)  # BB, VWAP, RSI values


class MeanReversionEngine:
    """
    Scans 5m candle data for mean reversion setups.
    """

    def __init__(self, config_path: str = "config/mean_reversion.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Indicator params
        ind = self.config['indicators']
        self.bb_period = ind['bb_period']            # 20
        self.rsi_oversold = ind['rsi_oversold']      # 30
        self.rsi_overbought = ind['rsi_overbought']  # 70
        self.rsi_extreme_os = ind['rsi_extreme_oversold']    # 20
        self.rsi_extreme_ob = ind['rsi_extreme_overbought']  # 80
        self.ema_flat_pct = ind['ema_flat_threshold_pct']    # 0.15

        # Signal configs
        self.signal_configs = self.config['signals']

        # Scoring
        self.scoring = self.config['scoring']
        self.min_score = self.scoring['min_score_threshold']  # 6

        # Risk
        self.risk = self.config['risk']
        self.max_sl_points = self.risk['max_sl_points']       # 5.0
        self.sl_atr_mult = self.risk['sl_atr_multiplier']     # 0.5
        self.default_target_r = self.risk['default_target_r'] # 1.5

        # Anti-trend filter
        self.anti_trend = self.config['anti_trend_filter']

    def _compute_indicators(self, df_5m: pd.DataFrame) -> pd.DataFrame:
        """Indicators pre-computed globally for O(1) access."""
        return df_5m

    def _check_anti_trend_filter(self, row: pd.Series) -> Tuple[bool, Dict]:
        if not self.anti_trend.get('enabled', True):
            return (True, {'filter': 'disabled'})

        details = {}
        blocked = False

        ema_spread = abs(row.get('ema_spread_pct', 0))
        max_spread = self.anti_trend['ema_spread_max_pct']
        if ema_spread > max_spread:
            blocked = True
            details['block_reason'] = 'EMA_SPREAD_TOO_WIDE'

        atr_exp = row.get('atr_expansion', 1.0)
        atr_limit = self.anti_trend['atr_expansion_threshold']
        if not np.isnan(atr_exp) and atr_exp > atr_limit:
            blocked = True
            details['block_reason'] = details.get('block_reason', '') + '+ATR_EXPANDING'

        rsi = row.get('rsi', 50)
        trending_zone = self.anti_trend['rsi_trending_zone']
        if trending_zone[0] <= rsi <= trending_zone[1]:
            blocked = True
            details['block_reason'] = details.get('block_reason', '') + '+RSI_NOT_EXTREME'

        return (not blocked, details)

    def _check_bb_reversion(self, row: pd.Series, settings: dict) -> Optional[Dict]:
        if not self.signal_configs['bollinger_reversion']['enabled']: return None
        close = row['close']
        rsi = row.get('rsi', 50)
        
        if close <= row.get('bb_lower_2', -1):
            score = self.scoring['bb_touch_3sigma'] if close <= row.get('bb_lower_3', -1) else self.scoring['bb_touch_2sigma']
            if self.signal_configs['bollinger_reversion']['require_rsi_confirm'] and rsi > settings['rsi_oversold']: return None
            logger.debug(f"MR_TELEM:BB_FIRE direction=LONG close={close}")
            return {'signal_type': 'BB_REVERSION', 'direction': 'LONG', 'score': score, 'details': {'rsi': rsi}}
            
        if close >= row.get('bb_upper_2', 1e9):
            score = self.scoring['bb_touch_3sigma'] if close >= row.get('bb_upper_3', 1e9) else self.scoring['bb_touch_2sigma']
            if self.signal_configs['bollinger_reversion']['require_rsi_confirm'] and rsi < settings['rsi_overbought']: return None
            logger.debug(f"MR_TELEM:BB_FIRE direction=SHORT close={close}")
            return {'signal_type': 'BB_REVERSION', 'direction': 'SHORT', 'score': score, 'details': {'rsi': rsi}}
        return None

    def _check_vwap_reversion(self, row: pd.Series, settings: dict) -> Optional[Dict]:
        if not self.signal_configs['vwap_reversion']['enabled']: return None
        close = row['close']
        vwap = row.get('vwap', close)
        rsi = row.get('rsi', 50)
        
        if close <= row.get('vwap_lower_1_5', -1):
            score = self.scoring['vwap_touch_2_5std'] if close <= row.get('vwap_lower_2_5', -1) else self.scoring['vwap_touch_1_5std']
            if self.signal_configs['vwap_reversion']['require_rsi_confirm'] and rsi > settings['rsi_oversold']: return None
            logger.debug(f"MR_TELEM:VWAP_FIRE direction=LONG close={close} vwap={vwap}")
            return {'signal_type': 'VWAP_REVERSION', 'direction': 'LONG', 'score': score, 'details': {'vwap': vwap}}

        if close >= row.get('vwap_upper_1_5', 1e9):
            score = self.scoring['vwap_touch_2_5std'] if close >= row.get('vwap_upper_2_5', 1e9) else self.scoring['vwap_touch_1_5std']
            if self.signal_configs['vwap_reversion']['require_rsi_confirm'] and rsi < settings['rsi_overbought']: return None
            logger.debug(f"MR_TELEM:VWAP_FIRE direction=SHORT close={close} vwap={vwap}")
            return {'signal_type': 'VWAP_REVERSION', 'direction': 'SHORT', 'score': score, 'details': {'vwap': vwap}}
        return None

    def _check_rsi_extreme(self, row: pd.Series, settings: dict) -> Optional[Dict]:
        if not self.signal_configs['rsi_extreme']['enabled']: return None
        rsi = row.get('rsi', 50)
        close = row['close']
        
        if rsi <= settings['rsi_oversold']:
            score = self.scoring['rsi_extreme'] if rsi <= self.rsi_extreme_os else self.scoring['rsi_oversold_overbought']
            if self.signal_configs['rsi_extreme']['require_band_confirm']:
                if not (close <= row.get('bb_lower_2', -1)*1.005 or close <= row.get('vwap_lower_1_5', -1)*1.005): return None
            logger.debug(f"MR_TELEM:RSI_FIRE direction=LONG rsi={rsi}")
            return {'signal_type': 'RSI_EXTREME', 'direction': 'LONG', 'score': score, 'details': {'rsi': rsi}}

        if rsi >= settings['rsi_overbought']:
            score = self.scoring['rsi_extreme'] if rsi >= self.rsi_extreme_ob else self.scoring['rsi_oversold_overbought']
            if self.signal_configs['rsi_extreme']['require_band_confirm']:
                if not (close >= row.get('bb_upper_2', 1e9)*0.995 or close >= row.get('vwap_upper_1_5', 1e9)*0.995): return None
            logger.debug(f"MR_TELEM:RSI_FIRE direction=SHORT rsi={rsi}")
            return {'signal_type': 'RSI_EXTREME', 'direction': 'SHORT', 'score': score, 'details': {'rsi': rsi}}
        return None

    def _calculate_sl_target(self, row: pd.Series, direction: str, settings: dict) -> Tuple[float, float, float]:
        close = row['close']
        atr = row.get('tr_atr', row.get('atr', 1.0))
        sl_dist = max(0.5, min(self.max_sl_points, settings['sl_atr_mult'] * atr))
        
        if direction == "LONG":
            sl = close - sl_dist
            target = max(row.get('vwap', close), row.get('bb_mid', close))
            if target <= close: target = close + sl_dist * self.default_target_r
        else:
            sl = close + sl_dist
            target = min(row.get('vwap', close), row.get('bb_mid', close))
            if target >= close: target = close - sl_dist * self.default_target_r
            
        r_mult = abs(target - close) / sl_dist
        return (round(sl, 2), round(target, 2), round(r_mult, 2))

    def scan(self, df_5m: pd.DataFrame, symbol: str,
             scan_last_n: int = 1, config: Optional[dict] = None) -> List[MeanReversionSignal]:
        if df_5m is None or len(df_5m) < 25: return []
        
        settings = {
            'rsi_oversold': config.get('rsi_oversold', self.rsi_oversold) if config else self.rsi_oversold,
            'rsi_overbought': config.get('rsi_overbought', self.rsi_overbought) if config else self.rsi_overbought,
            'sl_atr_mult': config.get('atr_sl_multiplier', self.sl_atr_mult) if config else self.sl_atr_mult,
            'min_score': config.get('min_score_threshold', self.min_score) if config else self.min_score
        }

        df = df_5m # No copy
        if 'bb_mid' not in df.columns:
            from modules.indicator_cache import precompute_indicators
            df = precompute_indicators(df)

        signals = []
        for idx in range(max(20, len(df) - scan_last_n), len(df)):
            row = df.iloc[idx]
            allowed, _ = self._check_anti_trend_filter(row)
            if not allowed: continue
            
            bb = self._check_bb_reversion(row, settings)
            vwap = self._check_vwap_reversion(row, settings)
            rsi = self._check_rsi_extreme(row, settings)
            
            fired = [s for s in [bb, vwap, rsi] if s]
            if not fired: continue
            
            # Simple consensus
            direction = fired[0]['direction']
            aligned = [s for s in fired if s['direction'] == direction]
            if not aligned: continue
            
            base_score = sum(s['score'] for s in aligned)
            if base_score < settings['min_score']: continue
            
            sl, tp, r = self._calculate_sl_target(row, direction, settings)
            signals.append(MeanReversionSignal(
                symbol=symbol, timestamp=df.index[idx], signal_type='CONFLUENCE' if len(aligned)>1 else aligned[0]['signal_type'],
                direction=direction, score=base_score, confidence=min(1.0, base_score/15.0),
                entry_price=round(row['close'], 2), sl_price=sl, target_price=tp, target_r=r
            ))
            
        return sorted(signals, key=lambda x: x.score, reverse=True)

    def generate_signal(self, df, symbol, config=None):
        res = self.scan(df, symbol, scan_last_n=1, config=config)
        return res[0] if res else None
