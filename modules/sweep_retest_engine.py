import os
import yaml
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from modules.smc.liquidity_sweep import LiquiditySweepDetector
from modules.smc.order_block import OrderBlockDetector
from modules.smc.fair_value_gap import FairValueGapDetector
from modules.smc.structure import StructureTracker
from modules.indicator_engine import IndicatorEngine
from modules.charting.structure_detector import StructureDetector

logger = logging.getLogger('live_trader')

@dataclass
class SweepState:
    status: str                # "IDLE", "SWEEP_DETECTED", "WAITING_FOR_RETEST", "CONFIRMATION", "EXPIRED"
    sweep_type: str            # "BULLISH_SWEEP" or "BEARISH_SWEEP"
    sweep_level: float         # The exact price level that was swept
    sweep_extreme: float       # The wick extreme (used for SL placement)
    sweep_bar_index: int       # Which bar the sweep occurred on (in 5m df)
    entry_zone_high: float     # Upper bound of retest zone
    entry_zone_low: float      # Lower bound of retest zone
    zone_source: str           # "ORDER_BLOCK", "FVG", "BREAKOUT_LEVEL"
    bars_since_sweep: int = 0  # Counter for expiry logic
    bars_in_zone: int = 0      # Counter for confirmation window
    direction: str = ""        # "CE" (bullish) or "PE" (bearish)
    confidence: float = 0      # Accumulated confidence score
    confirmations_found: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    cooldown_until: int = 0    # Bar index until which this setup is on cooldown

class SweepRetestEngine:
    def __init__(self, config_path="config/sweep_retest.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        # Detectors
        smc_cfg = {'smc': {'liquidity_sweep': self.config.get('sweep', {}), 
                           'order_block': {}, 
                           'fvg': {},
                           'structure': {}}}
        
        self.sweep_detector = LiquiditySweepDetector(smc_cfg, timeframe="5m")
        self.ob_detector = OrderBlockDetector(smc_cfg, timeframe="5m")
        self.fvg_detector = FairValueGapDetector(smc_cfg, timeframe="5m")
        self.structure_detector = StructureTracker(smc_cfg)
        self.indicator_engine = IndicatorEngine()
        self.struct_detector = StructureDetector()
        
        self.states: Dict[str, SweepState] = {} # {symbol: SweepState}

    def reset(self):
        """Reset state and sub-detectors for a new session/symbol."""
        self.states = {}
        self.sweep_detector.sweeps = []
        self.sweep_detector.pools = []
        self.ob_detector.reset()
        self.fvg_detector.reset()
        self.structure_detector.state.current_state = "TRANSITIONING"
        self.structure_detector.state.last_BOS = None
        self.structure_detector.state.last_CHoCH = None
        self.structure_detector.state.last_MSS = None
        self.structure_detector.swings = []

    def generate_signal(self, df_5m: pd.DataFrame, symbol: str, df_1m: pd.DataFrame = None, config=None) -> Optional[Dict]:
        # Merge runtime config with static config
        run_cfg = self.config.copy()
        if config:
            if 'max_bars_sweep_to_retest' in config:
                run_cfg['state_machine']['max_bars_sweep_to_retest'] = config['max_bars_sweep_to_retest']
            if 'min_wick_body_ratio' in config:
                run_cfg['confirmation']['rejection_candle']['min_wick_to_body'] = config['min_wick_body_ratio']
            if 'min_confidence_pct' in config:
                run_cfg['entry']['min_confidence_pct'] = config['min_confidence_pct']

        if not run_cfg.get('enabled', True):
            return None

        if df_5m is None or df_5m.empty or len(df_5m) < 30:
            return None

        current_bar_idx = len(df_5m) - 1
        state = self.states.get(symbol)

        # 0. Cooldown Check
        if state and state.status == "EXPIRED" and current_bar_idx < state.cooldown_until:
            return None
        
        # 1. State Machine Transitions
        if not state or state.status == "IDLE" or (state.status == "EXPIRED" and current_bar_idx >= state.cooldown_until):
            return self._handle_idle(df_5m, symbol, current_bar_idx, config=run_cfg)
        
        elif state.status == "WAITING_FOR_RETEST":
            return self._handle_waiting(df_5m, symbol, current_bar_idx, config=run_cfg)
        
        elif state.status == "CONFIRMATION":
            return self._handle_confirmation(df_5m, symbol, current_bar_idx, df_1m, config=run_cfg)

        return None

    def _handle_idle(self, df: pd.DataFrame, symbol: str, current_idx: int, config=None) -> Optional[Dict]:
        cfg = config if config else self.config
        atr = self.indicator_engine.calculate_atr(df).iloc[-1]
        sweeps = self.sweep_detector.update(df, atr, {}, {})
        
        if not sweeps: return None
        
        sweep = sweeps[-1]
        # FILTER: Reject sweeps where the sweep wick is < 0.10% beyond the level
        sweep_depth_pct = abs(sweep.sweep_price - sweep.pool_level) / sweep.pool_level * 100
        if sweep_depth_pct < 0.10:
            logger.info(f"[SWEEP_RETEST] {symbol} | NOISE REJECTED | Depth={sweep_depth_pct:.2f}% < 0.10%")
            return None
        
        is_bullish = any(x in sweep.pool_type for x in ["L", "SL"])
        setup_type = "BULLISH_SWEEP" if is_bullish else "BEARISH_SWEEP"
        direction = "CE" if is_bullish else "PE"
        
        zone_low, zone_high, source = self._find_entry_zone(df, is_bullish, sweep.pool_level, atr, config=cfg)
        
        new_state = SweepState(
            status="WAITING_FOR_RETEST", sweep_type=setup_type, sweep_level=sweep.pool_level,
            sweep_extreme=sweep.sweep_price, sweep_bar_index=sweep.sweep_candle_idx,
            entry_zone_high=zone_high, entry_zone_low=zone_low, zone_source=source,
            direction=direction, timestamp=datetime.now()
        )
        self.states[symbol] = new_state
        logger.info(f"[SWEEP_RETEST] {symbol} | IDLE → SWEEP_DETECTED | {setup_type} at {sweep.pool_level:.2f} | Zone=[{zone_low:.2f}-{zone_high:.2f}] ({source})")
        return None

    def _handle_waiting(self, df: pd.DataFrame, symbol: str, current_idx: int, config=None) -> Optional[Dict]:
        cfg = config if config else self.config
        state = self.states[symbol]
        state.bars_since_sweep += 1
        
        if state.bars_since_sweep > cfg['state_machine']['max_bars_sweep_to_retest']:
            state.status = "EXPIRED"
            state.cooldown_until = current_idx + cfg['state_machine']['cooldown_bars_after_expire']
            logger.info(f"[SWEEP_RETEST] {symbol} | WAITING → EXPIRED | Timeout {state.bars_since_sweep} bars")
            return None

        low, high = df.iloc[-1]['low'], df.iloc[-1]['high']
        if (low <= state.entry_zone_high and high >= state.entry_zone_low):
            state.status = "CONFIRMATION"
            state.bars_in_zone = 0
            logger.info(f"[SWEEP_RETEST] {symbol} | WAITING → CONFIRMATION | Price inside zone")
        return None

    def _handle_confirmation(self, df: pd.DataFrame, symbol: str, current_idx: int, df_1m: pd.DataFrame = None, config=None) -> Optional[Dict]:
        cfg = config if config else self.config
        state = self.states[symbol]
        state.bars_in_zone += 1
        
        if state.bars_in_zone > cfg['state_machine']['max_bars_retest_to_confirm']:
            state.status = "EXPIRED"
            state.cooldown_until = current_idx + cfg['state_machine']['cooldown_bars_after_expire']
            logger.info(f"[SWEEP_RETEST] {symbol} | CONFIRMATION → EXPIRED | No confirmation in {state.bars_in_zone} bars")
            return None

        confirmations = []
        if self._check_rejection_candle(df, state.direction, config=cfg): confirmations.append("rejection_candle")
        
        vol_mean = df['volume'].rolling(20).mean().iloc[-1]
        if df.iloc[-1]['volume'] > vol_mean * cfg['confirmation']['volume_spike_multiplier']:
            confirmations.append("volume_spike")
            
        atr = self.indicator_engine.calculate_atr(df).iloc[-1]
        recent_structure = self.structure_detector.update(df, atr, [])
        if recent_structure and recent_structure.last_BOS:
            bos = recent_structure.last_BOS
            bos_dir = "BULLISH" if state.direction == "CE" else "BEARISH"
            if bos['direction'] == bos_dir and (current_idx - bos['bar_idx'] <= 5):
                confirmations.append("bos_in_direction")

        rsi = self.indicator_engine.calculate_rsi(df, period=14).iloc[-1]
        if (state.direction == "CE" and rsi > 50) or (state.direction == "PE" and rsi < 50):
            confirmations.append("momentum_shift")

        if not confirmations:
            return None

        base_score = 50
        bonuses = len(confirmations) * 10
        if state.zone_source == "ORDER_BLOCK": bonuses += 10
        if state.zone_source == "FVG": bonuses += 5
        if "volume_spike" in confirmations: bonuses += 5
        
        if df_1m is not None and cfg['multi_timeframe']['enabled']:
            if self._check_rejection_candle(df_1m, state.direction, config=cfg):
                bonuses += 10
                confirmations.append("multi_tf_rejection")

        confidence = min(100, base_score + bonuses)
        state.confirmations_found = list(set(confirmations))
        state.confidence = confidence
        
        entry_cfg = cfg['confirmation']['entry']
        if confidence >= entry_cfg['min_confidence_pct']:
            entry = df.iloc[-1]['close']
            sl = 0
            sl_mode = cfg['risk']['sl_placement']
            if confidence > 80 and cfg['risk'].get('tight_sl_points'):
                sl = entry - cfg['risk']['tight_sl_points'] if state.direction == "CE" else entry + cfg['risk']['tight_sl_points']
                sl_mode = "TIGHT"
            elif sl_mode == "beyond_sweep_extreme":
                buffer = cfg['risk']['sl_buffer_points']
                sl = state.sweep_extreme - buffer if state.direction == "CE" else state.sweep_extreme + buffer
            else:
                atr = self.indicator_engine.calculate_atr(df).iloc[-1]
                sl = entry - (atr * 1.5) if state.direction == "CE" else entry + (atr * 1.5)
            
            atr = self.indicator_engine.calculate_atr(df).iloc[-1]
            min_sl_dist = atr * 0.5
            if abs(entry - sl) < min_sl_dist:
                sl = entry - min_sl_dist if state.direction == "CE" else entry + min_sl_dist

            risk = abs(entry - sl)
            
            structure = self.struct_detector.detect_all(df, symbol)
            nearest = self.struct_detector.get_nearest_levels(entry, structure)
            
            if state.direction == "CE":
                target1 = nearest['nearest_resistance']['price'] if nearest['nearest_resistance'] else entry + (risk * 2.5)
            else:
                target1 = nearest['nearest_support']['price'] if nearest['nearest_support'] else entry - (risk * 2.5)

            rr = abs(target1 - entry) / risk if risk > 0 else 0
            if rr < 2.0:
                logger.info(f"[SWEEP_RETEST] {symbol} | REJECTED | RR={rr:.1f} < 2.0 (Target: {target1:.2f})")
                state.status = "EXPIRED"
                return None
            
            signal_dict = {
                'signal': 'BUY' if state.direction == 'CE' else 'SELL',
                'direction': state.direction, 'entry': entry, 'sl': sl,
                'target1': target1, 'target2': entry + (risk * 3.0) if state.direction == 'CE' else entry - (risk * 3.0),
                'score': confidence / 10.0, 'setup_type': f"SWEEP_RETEST_{'BULLISH' if state.direction=='CE' else 'BEARISH'}",
                'sweep_type': state.sweep_type, 'zone_source': state.zone_source,
                'confirmations': state.confirmations_found, 'confidence': confidence,
                'reasons': [f"Sweep: {state.sweep_type}", f"Zone: {state.zone_source}", f"Confirmations: {len(state.confirmations_found)}"]
            }
            logger.info(f"[SWEEP_RETEST] {symbol} | ENTRY SIGNAL | {state.direction} | Entry={entry:.2f} | SL={sl:.2f}")
            state.status = "IDLE"
            return signal_dict
        return None

    def _find_entry_zone(self, df: pd.DataFrame, is_bullish: bool, sweep_level: float, atr: float, config=None) -> (float, float, str):
        cfg = config if config else self.config
        obs = self.ob_detector.update(df, atr)
        if obs:
            target_dir = "BULL" if is_bullish else "BEAR"
            filtered_obs = [ob for ob in obs if ob.direction == target_dir]
            if filtered_obs:
                current_price = df.iloc[-1]['close']
                best_ob = min(filtered_obs, key=lambda x: abs(x.ob_high - current_price))
                return best_ob.ob_low, best_ob.ob_high, "ORDER_BLOCK"
        fvgs = self.fvg_detector.update(df, atr)
        if fvgs:
            target_dir = "BULL" if is_bullish else "BEAR"
            filtered_fvgs = [fvg for fvg in fvgs if fvg.direction == target_dir]
            if filtered_fvgs:
                current_price = df.iloc[-1]['close']
                best_fvg = min(filtered_fvgs, key=lambda x: abs((x.fvg_high + x.fvg_low)/2 - current_price))
                return best_fvg.fvg_low, best_fvg.fvg_high, "FVG"
        buffer = atr * cfg['retest_zone']['fallback_zone_atr_multiple']
        return sweep_level - buffer, sweep_level + buffer, "BREAKOUT_LEVEL"

    def _check_rejection_candle(self, df: pd.DataFrame, direction: str, config=None) -> bool:
        if len(df) < 2: return False
        cfg = config if config else self.config
        candle = df.iloc[-1]
        body = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        
        ratio_cfg = cfg['confirmation']['rejection_candle']['min_wick_to_body']
        
        if direction == "CE":
            if body > 0 and lower_wick >= body * ratio_cfg: return True
            prev = df.iloc[-2]
            if candle['close'] > candle['open'] and prev['close'] < prev['open']:
                if body > abs(prev['close'] - prev['open']) * cfg['confirmation']['rejection_candle']['engulfing_body_ratio']:
                    return True
        else:
            if body > 0 and upper_wick >= body * ratio_cfg: return True
            prev = df.iloc[-2]
            if candle['close'] < candle['open'] and prev['close'] > prev['open']:
                if body > abs(prev['close'] - prev['open']) * cfg['confirmation']['rejection_candle']['engulfing_body_ratio']:
                    return True
        return False
