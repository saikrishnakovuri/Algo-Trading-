"""
Candlestick Pattern Recognition Engine (Option 2)
═══════════════════════════════════════════════════
Detects 5 proven candlestick patterns with VWAP + RSI + EMA context.
Returns scored signals compatible with StrategySelector.

Patterns:
  1. Engulfing (Primary) — best overall win rate
  2. Hammer / Shooting Star — best risk:reward
  3. Inside Bar — best breakout/trap play
  4. Morning Star / Evening Star — trend reversal confirmation
  5. Doji — warning signal, confirmation only

Each pattern is validated against:
  - VWAP alignment (price relative to VWAP)
  - RSI slope (momentum direction)
  - EMA crossover (9/20 trend alignment)

Scoring: Each context factor adds points. Trade only if score >= pattern threshold.
"""

import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple


@dataclass
class CandlestickSignal:
    """Output of candlestick pattern detection."""
    symbol: str
    timestamp: pd.Timestamp
    pattern_name: str          # e.g., "BULLISH_ENGULFING", "HAMMER", "INSIDE_BAR_TRAP"
    direction: str             # "LONG" or "SHORT"
    score: float               # composite score (pattern + context)
    confidence: float          # score / max_possible_score (0.0 to 1.0)
    entry_price: float         # suggested entry level
    sl_price: float            # suggested stop loss
    target_price: float        # suggested target
    target_r: float            # R-multiple for this pattern
    pattern_details: Dict = field(default_factory=dict)  # debug info
    context_details: Dict = field(default_factory=dict)  # VWAP/RSI/EMA state


class CandlestickEngine:
    """
    Scans 5m candle data for candlestick patterns with contextual validation.
    
    Usage:
        engine = CandlestickEngine(config_path="config/candlestick.yaml")
        signals = engine.scan(df_5m, symbol="RELIANCE")
        # Returns list of CandlestickSignal, sorted by score descending
        # Top signal (if any) is the recommended trade
    """

    def __init__(self, config_path: str = "config/candlestick.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Indicator params
        ind = self.config['indicators']
        self.ema_fast = ind['ema_fast']          # 9
        self.ema_slow = ind['ema_slow']          # 20
        self.rsi_period = ind['rsi_period']      # 14
        self.rsi_bull_zone = ind['rsi_bullish_zone']   # [40, 60]
        self.rsi_bear_zone = ind['rsi_bearish_zone']   # [40, 60]
        self.vwap_proximity_pct = ind['vwap_proximity_pct']  # 0.5
        
        # Master filter params
        mf = self.config['master_filter']
        self.require_vwap = mf['require_vwap_alignment']
        self.require_rsi = mf['require_rsi_slope']
        self.require_ema = mf['require_ema_alignment']
        self.max_bars_in_trade = mf['max_bars_in_trade']
        self.rsi_flat_threshold = mf['no_trade_rsi_flat_threshold']
        self.rsi_slope_lookback = mf['rsi_slope_lookback']
        self.vwap_max_dist_pct = mf['vwap_max_distance_pct']
        
        # Risk params
        self.max_sl_points = self.config['risk']['max_sl_points']
        
        # Pattern configs
        self.pattern_configs = self.config['patterns']

    # ══════════════════════════════════════════════════════════════
    # INDICATOR CALCULATIONS
    # ══════════════════════════════════════════════════════════════

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add EMA, RSI, VWAP, ATR columns to DataFrame. Modifies in-place."""
        df = df.copy()
        
        # EMA 9 and EMA 20
        df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
        
        # RSI (Wilder's smoothing)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1.0/self.rsi_period, min_periods=self.rsi_period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0/self.rsi_period, min_periods=self.rsi_period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
        
        # RSI slope (change over lookback bars)
        df['rsi_slope'] = df['rsi'] - df['rsi'].shift(self.rsi_slope_lookback)
        
        # VWAP (cumulative from session start, resets daily)
        if 'volume' in df.columns and df['volume'].sum() > 0:
            typical_price = (df['high'] + df['low'] + df['close']) / 3.0
            
            # Using groupby(date) to reset cumulative sum each day
            vol_price = typical_price * df['volume']
            if hasattr(df.index, 'date'):
                grouped = df.groupby(df.index.date)
                df['vwap'] = grouped[vol_price.name].cumsum() / grouped['volume'].cumsum()
            else:
                # Fallback if index is not datetime
                df['vwap'] = vol_price.cumsum() / df['volume'].cumsum()
        else:
            # Fallback: use rolling mean as pseudo-VWAP
            df['vwap'] = df['close'].rolling(window=20, min_periods=1).mean()
        
        # VWAP distance (percentage)
        df['vwap_dist_pct'] = ((df['close'] - df['vwap']) / df['vwap']) * 100.0
        
        # ATR (14-period)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14, min_periods=1).mean()
        
        # Body and wick calculations for each candle
        df['body'] = (df['close'] - df['open']).abs()
        df['range'] = df['high'] - df['low']
        df['body_ratio'] = df['body'] / df['range'].replace(0, np.nan)
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_bullish'] = df['close'] > df['open']
        
        return df

    # ══════════════════════════════════════════════════════════════
    # CONTEXT VALIDATION (MASTER FILTER)
    # ══════════════════════════════════════════════════════════════

    def _check_vwap_alignment(self, row: pd.Series, direction: str) -> Tuple[bool, int]:
        """
        Check if price is aligned with VWAP for the trade direction.
        Returns (is_aligned, score_points).
        
        LONG: price > VWAP (or within proximity)
        SHORT: price < VWAP (or within proximity)
        """
        vwap_dist = row.get('vwap_dist_pct', 0.0)
        
        # Too far from VWAP — no trade
        if abs(vwap_dist) > self.vwap_max_dist_pct:
            return (False, 0)
        
        if direction == "LONG":
            aligned = vwap_dist >= -self.vwap_proximity_pct  # price at or above VWAP
            score = 2 if vwap_dist > 0 else 1  # bonus if clearly above
        else:  # SHORT
            aligned = vwap_dist <= self.vwap_proximity_pct   # price at or below VWAP
            score = 2 if vwap_dist < 0 else 1
        
        return (aligned, score)

    def _check_rsi_slope(self, row: pd.Series, direction: str) -> Tuple[bool, int]:
        """
        Check RSI slope aligns with direction.
        LONG: RSI sloping UP (rsi_slope > 0) and RSI in 40-60 zone
        SHORT: RSI sloping DOWN (rsi_slope < 0) and RSI in 40-60 zone
        
        Returns (is_valid, score_points).
        """
        rsi = row.get('rsi', 50.0)
        rsi_slope = row.get('rsi_slope', 0.0)
        
        # RSI flat = no trade
        if abs(rsi_slope) < self.rsi_flat_threshold:
            return (False, 0)
        
        if direction == "LONG":
            zone = self.rsi_bull_zone
            slope_ok = rsi_slope > 0
            in_zone = zone[0] <= rsi <= zone[1]
            # Allow RSI turning up from below zone (reversal at 30-40)
            turning_up = rsi_slope > self.rsi_flat_threshold and rsi >= 30
            valid = slope_ok and (in_zone or turning_up)
        else:  # SHORT
            zone = self.rsi_bear_zone
            slope_ok = rsi_slope < 0
            in_zone = zone[0] <= rsi <= zone[1]
            turning_down = rsi_slope < -self.rsi_flat_threshold and rsi <= 70
            valid = slope_ok and (in_zone or turning_down)
        
        score = 2 if valid else 0
        return (valid, score)

    def _check_ema_alignment(self, row: pd.Series, direction: str) -> Tuple[bool, int]:
        """
        Check EMA 9/20 crossover alignment.
        LONG: EMA 9 > EMA 20 (or crossing above)
        SHORT: EMA 9 < EMA 20 (or crossing below)
        
        Returns (is_aligned, score_points).
        """
        ema_f = row.get('ema_fast', 0)
        ema_s = row.get('ema_slow', 0)
        
        if direction == "LONG":
            aligned = ema_f > ema_s
        else:
            aligned = ema_f < ema_s
        
        score = 2 if aligned else 0
        return (aligned, score)

    def _validate_context(self, row: pd.Series, direction: str) -> Tuple[bool, int, Dict]:
        """
        Run all 3 context checks. Returns (pass, total_context_score, details).
        If master filter requires all 3 and any fails → overall fail.
        """
        vwap_ok, vwap_score = self._check_vwap_alignment(row, direction)
        rsi_ok, rsi_score = self._check_rsi_slope(row, direction)
        ema_ok, ema_score = self._check_ema_alignment(row, direction)
        
        details = {
            'vwap_aligned': vwap_ok, 'vwap_score': vwap_score,
            'vwap_dist_pct': round(row.get('vwap_dist_pct', 0), 3),
            'rsi_valid': rsi_ok, 'rsi_score': rsi_score,
            'rsi': round(row.get('rsi', 0), 2),
            'rsi_slope': round(row.get('rsi_slope', 0), 3),
            'ema_aligned': ema_ok, 'ema_score': ema_score,
            'ema_fast': round(row.get('ema_fast', 0), 2),
            'ema_slow': round(row.get('ema_slow', 0), 2),
        }
        
        # Master filter: all required checks must pass
        passed = True
        if self.require_vwap and not vwap_ok:
            passed = False
        if self.require_rsi and not rsi_ok:
            passed = False
        if self.require_ema and not ema_ok:
            passed = False
        
        total_score = vwap_score + rsi_score + ema_score
        return (passed, total_score, details)

    # ══════════════════════════════════════════════════════════════
    # PATTERN 1: ENGULFING (PRIMARY SETUP — HIGHEST PRIORITY)
    # ══════════════════════════════════════════════════════════════

    def _detect_engulfing(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        Detect Bullish/Bearish Engulfing at index idx.
        
        BULLISH ENGULFING:
          - Previous candle: bearish (close < open)
          - Current candle: bullish (close > open)
          - Current body fully engulfs previous body
          - Current body ratio >= min_body_ratio (0.6)
          - Volume: current > previous (if volume_confirm enabled)
        
        BEARISH ENGULFING:
          - Previous candle: bullish
          - Current candle: bearish
          - Current body fully engulfs previous body
        
        SCORING (max 8 from pattern):
          - Strong engulfing body: +2
          (Context adds: VWAP +2, RSI +2, EMA +2 = max 14 total)
        
        ENTRY: Break of engulfing candle high (LONG) / low (SHORT)
        SL: Below engulfing low (LONG) / above high (SHORT), max 5 points
        TARGET: 2.0R
        """
        if not self.pattern_configs['engulfing']['enabled']:
            return None
        if idx < 1:
            return None
        
        cfg = self.config['engulfing']
        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # Skip if range is zero (doji-like candles)
        if curr['range'] == 0 or prev['range'] == 0:
            return None
        
        curr_bullish = curr['is_bullish']
        prev_bullish = prev['is_bullish']
        
        result = None
        
        # ── BULLISH ENGULFING ──
        if curr_bullish and not prev_bullish:
            # Current body must fully engulf previous body
            curr_body_low = curr['open']
            curr_body_high = curr['close']
            prev_body_low = prev['close']   # bearish: close < open
            prev_body_high = prev['open']
            
            if cfg['must_fully_engulf']:
                engulfs = (curr_body_low <= prev_body_low) and (curr_body_high >= prev_body_high)
            else:
                engulfs = curr['body'] > prev['body']
            
            if not engulfs:
                return None
            
            # Body ratio check
            if curr['body_ratio'] < cfg['min_body_ratio']:
                return None
            
            # Volume confirmation
            if cfg['volume_confirm'] and 'volume' in df.columns:
                if curr['volume'] <= prev['volume']:
                    return None
            
            # Pattern score: strong body
            pattern_score = 2  # strong engulfing body
            
            result = {
                'pattern_name': 'BULLISH_ENGULFING',
                'direction': 'LONG',
                'pattern_score': pattern_score,
                'entry_price': curr['high'],       # enter on break of engulfing high
                'sl_price': curr['low'],            # SL below engulfing low
                'target_r': self.config['risk']['engulfing_target_r'],
                'details': {
                    'curr_body': round(curr['body'], 2),
                    'prev_body': round(prev['body'], 2),
                    'body_ratio': round(curr['body_ratio'], 3),
                    'volume_ratio': round(curr['volume'] / max(prev['volume'], 1), 2) if 'volume' in df.columns else None,
                }
            }
        
        # ── BEARISH ENGULFING ──
        elif not curr_bullish and prev_bullish:
            curr_body_low = curr['close']
            curr_body_high = curr['open']
            prev_body_low = prev['open']
            prev_body_high = prev['close']
            
            if cfg['must_fully_engulf']:
                engulfs = (curr_body_low <= prev_body_low) and (curr_body_high >= prev_body_high)
            else:
                engulfs = curr['body'] > prev['body']
            
            if not engulfs:
                return None
            
            if curr['body_ratio'] < cfg['min_body_ratio']:
                return None
            
            if cfg['volume_confirm'] and 'volume' in df.columns:
                if curr['volume'] <= prev['volume']:
                    return None
            
            pattern_score = 2
            
            result = {
                'pattern_name': 'BEARISH_ENGULFING',
                'direction': 'SHORT',
                'pattern_score': pattern_score,
                'entry_price': curr['low'],
                'sl_price': curr['high'],
                'target_r': self.config['risk']['engulfing_target_r'],
                'details': {
                    'curr_body': round(curr['body'], 2),
                    'prev_body': round(prev['body'], 2),
                    'body_ratio': round(curr['body_ratio'], 3),
                    'volume_ratio': round(curr['volume'] / max(prev['volume'], 1), 2) if 'volume' in df.columns else None,
                }
            }
        
        return result

    # ══════════════════════════════════════════════════════════════
    # PATTERN 2: HAMMER / SHOOTING STAR (TRAP SETUP)
    # ══════════════════════════════════════════════════════════════

    def _detect_hammer_shooting_star(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        HAMMER (LONG):
          - Long lower wick (>= 2x body)
          - Small upper wick (<= 30% of body)
          - Near VWAP or support level
          - RSI turning UP from ~40
        
        SHOOTING STAR (SHORT):
          - Long upper wick (>= 2x body)
          - Small lower wick (<= 30% of body)
          - Near VWAP or resistance
          - RSI turning DOWN from ~60
        
        ENTRY: After NEXT candle confirmation break (not immediate)
        SL: Below wick (hammer) / above wick (shooting star), max 5 points
        TARGET: 2.5R (best RR pattern)
        
        SCORING (max from pattern):
          - Location (VWAP/SR): +3
          - Wick size (2x body): +2
          - RSI reversal: +2
          (scored via context validator separately for RSI/EMA)
        """
        if not self.pattern_configs['hammer_shooting_star']['enabled']:
            return None
        if idx < 1:
            return None
        
        cfg = self.config['hammer_shooting_star']
        curr = df.iloc[idx]
        
        if curr['body'] == 0 or curr['range'] == 0:
            return None
        
        result = None
        
        # ── HAMMER (bullish reversal at bottom) ──
        lower_wick_ratio = curr['lower_wick'] / max(curr['body'], 0.01)
        upper_wick_ratio = curr['upper_wick'] / max(curr['body'], 0.01)
        
        is_hammer = (
            lower_wick_ratio >= cfg['min_wick_body_ratio'] and     # long lower wick
            upper_wick_ratio <= cfg['max_opposite_wick_ratio']      # small upper wick
        )
        
        is_shooting_star = (
            upper_wick_ratio >= cfg['min_wick_body_ratio'] and     # long upper wick
            lower_wick_ratio <= cfg['max_opposite_wick_ratio']      # small lower wick
        )
        
        if is_hammer:
            # Location score: near VWAP or at swing low
            vwap_dist = abs(curr.get('vwap_dist_pct', 999))
            location_score = 3 if vwap_dist <= self.vwap_proximity_pct else 1
            
            # Wick quality score
            wick_score = 2 if lower_wick_ratio >= cfg['min_wick_body_ratio'] else 1
            
            pattern_score = location_score + wick_score  # max 5 from pattern
            
            result = {
                'pattern_name': 'HAMMER',
                'direction': 'LONG',
                'pattern_score': pattern_score,
                'entry_price': curr['high'],       # enter on break of hammer high (next candle confirms)
                'sl_price': curr['low'],            # SL below hammer wick
                'target_r': self.config['risk']['hammer_target_r'],
                'details': {
                    'lower_wick_ratio': round(lower_wick_ratio, 2),
                    'upper_wick_ratio': round(upper_wick_ratio, 2),
                    'location_score': location_score,
                    'needs_confirmation': True,     # wait for next candle to break high
                }
            }
        
        elif is_shooting_star:
            vwap_dist = abs(curr.get('vwap_dist_pct', 999))
            location_score = 3 if vwap_dist <= self.vwap_proximity_pct else 1
            wick_score = 2 if upper_wick_ratio >= cfg['min_wick_body_ratio'] else 1
            pattern_score = location_score + wick_score
            
            result = {
                'pattern_name': 'SHOOTING_STAR',
                'direction': 'SHORT',
                'pattern_score': pattern_score,
                'entry_price': curr['low'],
                'sl_price': curr['high'],
                'target_r': self.config['risk']['hammer_target_r'],
                'details': {
                    'upper_wick_ratio': round(upper_wick_ratio, 2),
                    'lower_wick_ratio': round(lower_wick_ratio, 2),
                    'location_score': location_score,
                    'needs_confirmation': True,
                }
            }
        
        return result

    # ══════════════════════════════════════════════════════════════
    # PATTERN 3: INSIDE BAR (BREAKOUT + FALSE BREAKOUT TRAP)
    # ══════════════════════════════════════════════════════════════

    def _detect_inside_bar(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        INSIDE BAR:
          - Current candle's high < previous candle's high
          - Current candle's low > previous candle's low
          - Previous candle (mother bar) must be meaningful (>= 0.8x ATR)
        
        TWO TRADE TYPES:
          A) Breakout: Enter on break above mother high (LONG) or below mother low (SHORT)
          B) False Breakout Trap (BEST): Wait for breakout → FAIL → reverse entry
             - If price breaks above mother high then closes back inside → SHORT
             - If price breaks below mother low then closes back inside → LONG
             - False breakout gets +3 bonus score
        
        CONTEXT:
          - Low volatility (small candles, EMA 9 & 20 tight)
          - Price near VWAP consolidation
        
        ENTRY: Buy above mother high / sell below mother low
        SL: Opposite side of inside candle, max 5 points
        TARGET: Breakout 1.5R, Trap 2.0R
        
        SCORING:
          - VWAP compression: +2
          - EMA tight: +2
          - False breakout: +3
        """
        if not self.pattern_configs['inside_bar']['enabled']:
            return None
        if idx < 2:  # need at least 2 bars history for false breakout detection
            return None
        
        cfg = self.config['inside_bar']
        curr = df.iloc[idx]
        mother = df.iloc[idx - 1]  # previous candle = mother bar
        
        # Inside bar check: current range fully inside mother range
        is_inside = (curr['high'] < mother['high']) and (curr['low'] > mother['low'])
        if not is_inside:
            return None
        
        # Mother bar must be meaningful (>= 0.8x ATR)
        atr = curr.get('atr', 0)
        if atr > 0 and mother['range'] < cfg['min_mother_bar_atr_ratio'] * atr:
            return None
        
        # Check if EMA is tight (consolidation indicator)
        ema_gap = abs(curr.get('ema_fast', 0) - curr.get('ema_slow', 0))
        ema_tight = ema_gap < (atr * 0.3) if atr > 0 else False
        ema_score = 2 if ema_tight else 0
        
        # VWAP compression: price very close to VWAP
        vwap_dist = abs(curr.get('vwap_dist_pct', 999))
        vwap_score = 2 if vwap_dist <= self.vwap_proximity_pct else 0
        
        # ── Check for FALSE BREAKOUT (look at bar BEFORE mother) ──
        # If idx-2 broke above/below the bar before it, and then idx-1 (mother) reversed back
        # This is a simplified false-breakout detection
        false_breakout_detected = False
        false_breakout_direction = None
        
        if idx >= 3:
            pre_mother = df.iloc[idx - 2]
            pre_pre = df.iloc[idx - 3]
            
            # False breakout UP: pre_mother broke above pre_pre high, mother reversed down
            if pre_mother['high'] > pre_pre['high'] and mother['close'] < pre_pre['high']:
                false_breakout_detected = True
                false_breakout_direction = "SHORT"  # fade the failed breakout
            
            # False breakout DOWN: pre_mother broke below pre_pre low, mother reversed up
            elif pre_mother['low'] < pre_pre['low'] and mother['close'] > pre_pre['low']:
                false_breakout_detected = True
                false_breakout_direction = "LONG"
        
        if false_breakout_detected:
            # TRAP trade — higher probability
            fb_bonus = cfg['false_breakout_bonus']  # +3
            pattern_score = vwap_score + ema_score + fb_bonus
            direction = false_breakout_direction
            
            if direction == "LONG":
                entry = mother['high']
                sl = curr['low']
            else:
                entry = mother['low']
                sl = curr['high']
            
            return {
                'pattern_name': 'INSIDE_BAR_TRAP',
                'direction': direction,
                'pattern_score': pattern_score,
                'entry_price': entry,
                'sl_price': sl,
                'target_r': 2.0,  # trap gets better target
                'details': {
                    'is_false_breakout': True,
                    'mother_range': round(mother['range'], 2),
                    'inside_range': round(curr['range'], 2),
                    'ema_tight': ema_tight,
                    'vwap_compression': vwap_dist <= self.vwap_proximity_pct,
                }
            }
        else:
            # Standard breakout — trade in direction of breakout
            # Direction determined by where current candle closes relative to mother midpoint
            mother_mid = (mother['high'] + mother['low']) / 2
            direction = "LONG" if curr['close'] >= mother_mid else "SHORT"
            
            pattern_score = vwap_score + ema_score
            
            if direction == "LONG":
                entry = mother['high']
                sl = mother['low']  # opposite side of mother bar
            else:
                entry = mother['low']
                sl = mother['high']
            
            return {
                'pattern_name': 'INSIDE_BAR_BREAKOUT',
                'direction': direction,
                'pattern_score': pattern_score,
                'entry_price': entry,
                'sl_price': sl,
                'target_r': self.config['risk']['inside_bar_target_r'],
                'details': {
                    'is_false_breakout': False,
                    'mother_range': round(mother['range'], 2),
                    'inside_range': round(curr['range'], 2),
                    'ema_tight': ema_tight,
                    'vwap_compression': vwap_dist <= self.vwap_proximity_pct,
                }
            }

    # ══════════════════════════════════════════════════════════════
    # PATTERN 4: MORNING STAR / EVENING STAR (3-CANDLE REVERSAL)
    # ══════════════════════════════════════════════════════════════

    def _detect_morning_evening_star(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        MORNING STAR (LONG — bottom reversal):
          Candle 1 (idx-2): Strong bearish candle (body >= 50% of range)
          Candle 2 (idx-1): Small body (indecision, body <= 30% of range)
          Candle 3 (idx):   Strong bullish candle, closes past midpoint of Candle 1's body
        
        EVENING STAR (SHORT — top reversal):
          Candle 1 (idx-2): Strong bullish candle
          Candle 2 (idx-1): Small body (indecision)
          Candle 3 (idx):   Strong bearish candle, closes past midpoint of Candle 1's body
        
        CONTEXT:
          - Occurs after strong trend
          - Near VWAP or key level
          - RSI divergence (bonus)
        
        ENTRY: After 3rd candle confirmation close
        SL: Below pattern low (morning star) / above pattern high (evening star)
        TARGET: 2.0R (strong moves possible)
        
        SCORING:
          - Trend exhaustion: +2
          - VWAP/SR proximity: +2
          - Strong 3rd candle: +2
        """
        if not self.pattern_configs['morning_evening_star']['enabled']:
            return None
        if idx < 2:
            return None
        
        cfg = self.config['morning_evening_star']
        c1 = df.iloc[idx - 2]   # first candle (trend candle)
        c2 = df.iloc[idx - 1]   # middle candle (indecision)
        c3 = df.iloc[idx]       # third candle (reversal)
        
        # All candles must have non-zero range
        if c1['range'] == 0 or c2['range'] == 0 or c3['range'] == 0:
            return None
        
        result = None
        
        # ── MORNING STAR (bullish reversal) ──
        c1_bearish = not c1['is_bullish']
        c1_strong = c1['body_ratio'] >= cfg['min_first_candle_body']
        c2_small = c2['body_ratio'] <= cfg['max_middle_candle_body']
        c3_bullish = c3['is_bullish']
        c3_strong = c3['body_ratio'] >= cfg['min_third_candle_body']
        
        if c1_bearish and c1_strong and c2_small and c3_bullish and c3_strong:
            # Check: 3rd candle closes past midpoint of 1st candle body
            c1_body_mid = (c1['open'] + c1['close']) / 2  # c1 is bearish: open > close
            if cfg['third_candle_must_close_past_midpoint']:
                if c3['close'] < c1_body_mid:
                    return None  # 3rd candle didn't recover enough
            
            # Scoring
            exhaustion_score = 2  # we already confirmed strong c1 + small c2
            vwap_dist = abs(c3.get('vwap_dist_pct', 999))
            location_score = 2 if vwap_dist <= self.vwap_proximity_pct * 2 else 0
            c3_body_strength = 2 if c3['body_ratio'] >= 0.65 else 1
            
            pattern_score = exhaustion_score + location_score + c3_body_strength
            
            # Entry at c3 close, SL at pattern low
            pattern_low = min(c1['low'], c2['low'], c3['low'])
            
            result = {
                'pattern_name': 'MORNING_STAR',
                'direction': 'LONG',
                'pattern_score': pattern_score,
                'entry_price': c3['close'],       # enter at 3rd candle close
                'sl_price': pattern_low,
                'target_r': self.config['risk']['morning_star_target_r'],
                'details': {
                    'c1_body_ratio': round(c1['body_ratio'], 3),
                    'c2_body_ratio': round(c2['body_ratio'], 3),
                    'c3_body_ratio': round(c3['body_ratio'], 3),
                    'c3_past_midpoint': c3['close'] >= c1_body_mid,
                }
            }
        
        # ── EVENING STAR (bearish reversal) ──
        c1_bullish = c1['is_bullish']
        c1_strong_bull = c1['body_ratio'] >= cfg['min_first_candle_body']
        c3_bearish = not c3['is_bullish']
        c3_strong_bear = c3['body_ratio'] >= cfg['min_third_candle_body']
        
        if c1_bullish and c1_strong_bull and c2_small and c3_bearish and c3_strong_bear:
            c1_body_mid = (c1['open'] + c1['close']) / 2  # c1 is bullish: close > open
            if cfg['third_candle_must_close_past_midpoint']:
                if c3['close'] > c1_body_mid:
                    return None
            
            exhaustion_score = 2
            vwap_dist = abs(c3.get('vwap_dist_pct', 999))
            location_score = 2 if vwap_dist <= self.vwap_proximity_pct * 2 else 0
            c3_body_strength = 2 if c3['body_ratio'] >= 0.65 else 1
            
            pattern_score = exhaustion_score + location_score + c3_body_strength
            
            pattern_high = max(c1['high'], c2['high'], c3['high'])
            
            result = {
                'pattern_name': 'EVENING_STAR',
                'direction': 'SHORT',
                'pattern_score': pattern_score,
                'entry_price': c3['close'],
                'sl_price': pattern_high,
                'target_r': self.config['risk']['morning_star_target_r'],
                'details': {
                    'c1_body_ratio': round(c1['body_ratio'], 3),
                    'c2_body_ratio': round(c2['body_ratio'], 3),
                    'c3_body_ratio': round(c3['body_ratio'], 3),
                    'c3_past_midpoint': c3['close'] <= c1_body_mid,
                }
            }
        
        return result

    # ══════════════════════════════════════════════════════════════
    # PATTERN 5: DOJI (WARNING — CONFIRMATION ONLY)
    # ══════════════════════════════════════════════════════════════

    def _detect_doji(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        DOJI:
          - Body <= 10% of total range (open ~ close)
          - NEVER trade doji alone — wait for NEXT candle to confirm direction
          - At top: bearish warning → SHORT if next candle breaks below doji low
          - At bottom: bullish warning → LONG if next candle breaks above doji high
        
        CONTEXT:
          - At top or bottom of move
          - Near VWAP
          - After big move (trend exhaustion)
        
        ENTRY: Trade NEXT candle breakout (not the doji itself)
        SL: Inside doji range (tight)
        TARGET: 1.2R (conservative)
        
        SCORING:
          - Location (top/bottom): +2
          - Trend exhaustion: +2
          - Confirmation candle: +3
        """
        if not self.pattern_configs['doji']['enabled']:
            return None
        if idx < 2:  # need history for trend context
            return None
        
        cfg = self.config['doji']
        curr = df.iloc[idx]
        
        if curr['range'] == 0:
            return None
        
        # Doji check: body <= 10% of range
        is_doji = curr['body_ratio'] <= cfg['max_body_range_ratio']
        if not is_doji:
            return None
        
        # Determine if at top or bottom of recent move
        # Look back 5 bars to see trend direction
        lookback = min(5, idx)
        recent_closes = df['close'].iloc[idx - lookback:idx].values
        
        if len(recent_closes) < 2:
            return None
        
        trend_change = recent_closes[-1] - recent_closes[0]
        atr = curr.get('atr', 1)
        trend_strength = abs(trend_change) / max(atr, 0.01)
        
        # Need trend exhaustion — trend must be at least 1.0 ATR
        if trend_strength < 1.0:
            return None
        
        # At TOP of uptrend → bearish doji → SHORT on confirmation
        # At BOTTOM of downtrend → bullish doji → LONG on confirmation
        if trend_change > 0:
            # Price went UP → doji at TOP → SHORT signal
            direction = "SHORT"
        else:
            # Price went DOWN → doji at BOTTOM → LONG signal
            direction = "LONG"
        
        # Location score
        vwap_dist = abs(curr.get('vwap_dist_pct', 999))
        location_score = 2 if vwap_dist <= self.vwap_proximity_pct * 2 else 0
        exhaustion_score = 2 if trend_strength >= 1.5 else 1
        
        # Confirmation: if require_confirmation, we flag this signal as needing
        # the NEXT bar to break above doji high (LONG) or below doji low (SHORT)
        # The backtest engine should handle this via the needs_confirmation flag
        confirmation_score = 0  # will be 3 when confirmed by next bar
        
        pattern_score = location_score + exhaustion_score + confirmation_score
        
        if direction == "LONG":
            entry = curr['high']   # enter on break above doji high
            sl = curr['low']       # SL below doji low (tight)
        else:
            entry = curr['low']
            sl = curr['high']
        
        return {
            'pattern_name': 'DOJI',
            'direction': direction,
            'pattern_score': pattern_score,
            'entry_price': entry,
            'sl_price': sl,
            'target_r': self.config['risk']['doji_target_r'],
            'details': {
                'body_ratio': round(curr['body_ratio'], 4),
                'trend_strength_atr': round(trend_strength, 2),
                'trend_direction': 'UP' if trend_change > 0 else 'DOWN',
                'needs_confirmation': cfg['require_confirmation'],
                'confirmation_type': cfg['confirmation_break_type'],
            }
        }

    # ══════════════════════════════════════════════════════════════
    # MAIN SCAN METHOD
    # ══════════════════════════════════════════════════════════════

    def scan(self, df_5m: pd.DataFrame, symbol: str, 
             scan_last_n: int = 5) -> List[CandlestickSignal]:
        """
        Scan the last N candles of 5m data for candlestick patterns.
        
        Args:
            df_5m: DataFrame with columns [open, high, low, close, volume, timestamp/datetime]
            symbol: Stock symbol (e.g., "RELIANCE")
            scan_last_n: Number of recent candles to scan (default 5)
        
        Returns:
            List of CandlestickSignal objects, sorted by score descending.
            Empty list if no valid signals found.
        
        Flow:
            1. Compute indicators (EMA, RSI, VWAP, ATR)
            2. For each of last N candles, run all 5 pattern detectors
            3. For each detected pattern, validate context (VWAP + RSI + EMA)
            4. Score = pattern_score + context_score
            5. Filter by min_score threshold per pattern type
            6. Clamp SL to max 5 points
            7. Sort by score descending, return list
        """
        if df_5m is None or len(df_5m) < 20:
            return []
        
        # Standardize column names to lowercase
        df = df_5m.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # Ensure required columns exist
        required = ['open', 'high', 'low', 'close']
        if not all(c in df.columns for c in required):
            return []
        
        # Compute indicators
        df = self._compute_indicators(df)
        
        signals = []
        
        # Scan last N candles
        start_idx = max(3, len(df) - scan_last_n)
        end_idx = len(df)
        
        for idx in range(start_idx, end_idx):
            row = df.iloc[idx]
            
            # Run all pattern detectors
            pattern_detectors = [
                self._detect_engulfing,
                self._detect_hammer_shooting_star,
                self._detect_inside_bar,
                self._detect_morning_evening_star,
                self._detect_doji,
            ]
            
            for detector in pattern_detectors:
                result = detector(df, idx)
                if result is None:
                    continue
                
                # Validate context (VWAP + RSI + EMA)
                context_passed, context_score, context_details = self._validate_context(
                    row, result['direction']
                )
                
                if not context_passed:
                    continue  # master filter blocked this signal
                
                # Total score
                total_score = result['pattern_score'] + context_score
                
                # Check minimum score for this pattern type
                pattern_type = result['pattern_name']
                # Map pattern name to config key
                config_key_map = {
                    'BULLISH_ENGULFING': 'engulfing',
                    'BEARISH_ENGULFING': 'engulfing',
                    'HAMMER': 'hammer_shooting_star',
                    'SHOOTING_STAR': 'hammer_shooting_star',
                    'INSIDE_BAR_BREAKOUT': 'inside_bar',
                    'INSIDE_BAR_TRAP': 'inside_bar',
                    'MORNING_STAR': 'morning_evening_star',
                    'EVENING_STAR': 'morning_evening_star',
                    'DOJI': 'doji',
                }
                config_key = config_key_map.get(pattern_type, 'engulfing')
                min_score = self.pattern_configs[config_key]['min_score']
                
                if total_score < min_score:
                    continue
                
                # Clamp SL to max 5 points
                entry_price = result['entry_price']
                sl_price = result['sl_price']
                sl_distance = abs(entry_price - sl_price)
                
                if sl_distance > self.max_sl_points:
                    # Clamp SL
                    if result['direction'] == "LONG":
                        sl_price = entry_price - self.max_sl_points
                    else:
                        sl_price = entry_price + self.max_sl_points
                    sl_distance = self.max_sl_points
                
                # Calculate target price
                target_r = result['target_r']
                if result['direction'] == "LONG":
                    target_price = entry_price + (sl_distance * target_r)
                else:
                    target_price = entry_price - (sl_distance * target_r)
                
                # Confidence = score / max possible score (14 for most patterns)
                max_possible = 14  # pattern(8) + context(6) — generous estimate
                confidence = min(total_score / max_possible, 1.0)
                
                # Get timestamp
                if 'timestamp' in df.columns:
                    ts = df['timestamp'].iloc[idx]
                elif 'datetime' in df.columns:
                    ts = df['datetime'].iloc[idx]
                elif isinstance(df.index, pd.DatetimeIndex):
                    ts = df.index[idx]
                else:
                    ts = pd.Timestamp.now()
                
                signal = CandlestickSignal(
                    symbol=symbol,
                    timestamp=ts,
                    pattern_name=pattern_type,
                    direction=result['direction'],
                    score=total_score,
                    confidence=confidence,
                    entry_price=round(entry_price, 2),
                    sl_price=round(sl_price, 2),
                    target_price=round(target_price, 2),
                    target_r=target_r,
                    pattern_details=result.get('details', {}),
                    context_details=context_details,
                )
                signals.append(signal)
        
        # Sort by score descending (best signal first)
        signals.sort(key=lambda s: s.score, reverse=True)
        
        return signals

    def get_best_signal(self, df_5m: pd.DataFrame, symbol: str) -> Optional[CandlestickSignal]:
        """Convenience method: return the single best signal or None."""
        signals = self.scan(df_5m, symbol)
        return signals[0] if signals else None

    def generate_signal(self, df, symbol, config=None):
        """Standard interface for multi-strategy selector."""
        return self.get_best_signal(df, symbol)
