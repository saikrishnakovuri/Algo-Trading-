import pandas as pd
import numpy as np
import yaml
from typing import List, Tuple, Dict, Any

try:
    from modules.pa_engine_bridge import PAEngineBridge
    PA_BRIDGE_AVAILABLE = True
except ImportError:
    PA_BRIDGE_AVAILABLE = False


class PriceActionEngine:
    """Price action utilities following the pipeline:

    RAW DATA -> MARKET STRUCTURE -> ZONES -> CANDLES -> CONFLUENCE -> DECISION
    """

    @staticmethod
    def load_strategy_filter():
        try:
            with open("config/strategy_filter.yaml") as f:
                return yaml.safe_load(f).get("strategies", {})
        except Exception:
            return {}

    @staticmethod
    def is_strategy_allowed(setup_type, symbol, score, strategy_filter):
        config = strategy_filter.get(setup_type, {})
        
        # Not in config = use default (enabled)
        if not config:
            # Default minimum conviction for ZONE_REJECTION is now 7.0
            if setup_type == "ZONE_REJECTION" and score < 7.0:
                return False
            return True
        
        if not config.get("enabled", True):
            return False
        
        allowed = config.get("allowed_symbols", "ALL")
        if allowed != "ALL" and symbol not in allowed:
            return False
        
        min_score = config.get("min_score_override")
        # If no override, still apply the 7.0 floor for ZONE_REJECTION
        if not min_score and setup_type == "ZONE_REJECTION":
            min_score = 7.0
            
        if min_score and score < min_score:
            return False
        
        return True

    @staticmethod
    def detect_market_structure(df: pd.DataFrame) -> str:
        """
        Detects market structure using sequential swing pivots.
        Returns: 'HH-HL' (Bullish), 'LH-LL' (Bearish), 'RANGE', or 'UNKNOWN'
        """
        if df is None or len(df) < 20:
            return "UNKNOWN"

        s_highs, s_lows = PriceActionEngine.detect_swings(df, window=3)
        if len(s_highs) < 2 or len(s_lows) < 2:
            return "RANGE"

        # Get last two confirmed swing points
        h2, h1 = s_highs[-1][1], s_highs[-2][1]
        l2, l1 = s_lows[-1][1], s_lows[-2][1]

        if h2 > h1 and l2 > l1:
            return "HH-HL"
        elif h2 < h1 and l2 < l1:
            return "LH-LL"
        else:
            return "RANGE"

    @staticmethod
    def get_trend(structure: str) -> str:
        if structure == "HH-HL":
            return "BULLISH"
        elif structure == "LH-LL":
            return "BEARISH"
        else:
            return "SIDEWAYS"

    @staticmethod
    def detect_swings(df: pd.DataFrame, window: int = 2) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """STEP 1: Identify Swing Points (Local Highs/Lows)"""
        swing_highs = []
        swing_lows = []

        if df is None or len(df) < (window * 2 + 1):
            return swing_highs, swing_lows

        highs = df['high'].values
        lows = df['low'].values

        for i in range(2 * window, len(df)):
            # A high is confirmed as a swing high only if it was the max of [i-2*window to i] 
            # and the actual peak occurred at i-window (confirmed by the drop in the last 'window' bars)
            window_slice = highs[i - 2*window : i + 1]
            if len(window_slice) > 0 and highs[i-window] == window_slice.max():
                swing_highs.append((i-window, PriceActionEngine._safe_float(highs[i-window])))

            window_slice_low = lows[i - 2*window : i + 1]
            if len(window_slice_low) > 0 and lows[i-window] == window_slice_low.min():
                swing_lows.append((i-window, PriceActionEngine._safe_float(lows[i-window])))

        return swing_highs, swing_lows

    @staticmethod
    def cluster_levels(levels: List[Tuple[int, float]], tolerance: float = 0.002) -> List[Dict[str, Any]]:
        """STEP 2: Cluster nearby swing points into potential zones.
        Tolerance is relative to price (default 0.2%).
        """
        if not levels:
            return []

        clusters = []
        # Sort levels by price to facilitate clustering
        sorted_levels = sorted(levels, key=lambda x: x[1])

        for idx, price in sorted_levels:
            found = False
            for cluster in clusters:
                # Use a dynamic tolerance based on price level
                dynamic_tol = cluster['center'] * tolerance
                if abs(cluster['center'] - price) <= dynamic_tol:
                    cluster['indices'].append(idx)
                    cluster['prices'].append(price)
                    cluster['center'] = sum(cluster['prices']) / len(cluster['prices'])
                    found = True
                    break

            if not found:
                clusters.append({
                    "center": price,
                    "prices": [price],
                    "indices": [idx]
                })

        return clusters

    @staticmethod
    def build_zones(df: pd.DataFrame, clusters: List[Dict[str, Any]], zone_type: str = "support") -> List[Dict[str, Any]]:
        """STEP 3: Convert clusters into rectangular zones using Body + Wick logic."""
        zones = []
        if df is None or df.empty:
            return zones

        atr = PriceActionEngine.calculate_atr(df, period=14)

        for cluster in clusters:
            indices = cluster["indices"]
            prices = cluster["prices"]
            
            # Refinement: Use average of (Open + Close) of the candles at swing points
            candle_bodies = []
            cumulative_volume = 0
            for i in indices:
                candle = df.iloc[i]
                open_p = PriceActionEngine._safe_float(candle['open'])
                close_p = PriceActionEngine._safe_float(candle['close'])
                candle_bodies.append((open_p + close_p) / 2.0)
                cumulative_volume += PriceActionEngine._safe_float(candle.get('Volume', 0))
            
            avg_body = sum(candle_bodies) / len(candle_bodies)
            touch_count = len(prices)

            if zone_type == "support":
                # Support: [lowest wick -> average body]
                lower = min(prices)
                upper = avg_body
            else:
                # Resistance: [average body -> highest wick]
                lower = avg_body
                upper = max(prices)
            
            if lower > upper: lower, upper = upper, lower

            # FIX 3: ATR-Normalized Zone Validation (with center-shift fix)
            zone_width = upper - lower
            if atr > 0:
                center_price = (lower + upper) / 2.0 # compute BEFORE modification
                if zone_width < atr * 0.3:
                    lower = center_price - atr * 0.15
                    upper = center_price + atr * 0.15
                elif zone_width > atr * 2.0:
                    lower = center_price - atr * 1.0
                    upper = center_price + atr * 1.0

            # Recency Factor: Distance of the latest touch from the current bar
            latest_idx = max(indices)
            recency = 1.0 / (len(df) - latest_idx + 1) # Higher is fresher

            # MICROSTRUCTURE: Volume at Price
            typical_prices = (df['high'] + df['low'] + df['close']) / 3.0
            volume_mask = (typical_prices >= lower) & (typical_prices <= upper)
            zone_volume = df.loc[volume_mask, 'Volume'].sum()
            avg_vol = df['volume'].mean()
            norm_vol = (zone_volume / avg_vol) if avg_vol > 0 else 0

            # FIX 1 & 7: Calculate respect_ratio
            respect = PriceActionEngine.score_zone_respect(df, (lower, upper))

            zones.append({
                "zone": (round(lower, 2), round(upper, 2)),
                "center": (lower + upper) / 2.0,
                "strength": touch_count, # Base strength
                "recency": recency,
                "volume_score": norm_vol,
                "respect_ratio": respect,
                "type": zone_type
            })

        # Return top 3 strongest, freshest, highest volume, and most respected zones
        # Final institutional sorting heuristic
        return sorted(zones, key=lambda x: (
            x["strength"]      * 0.4 +
            x["recency"]       * 0.2 +
            x["volume_score"]  * 0.2 +
            x["respect_ratio"] * 0.2
        ), reverse=True)[:3]

    @staticmethod
    def score_zone_respect(df: pd.DataFrame, zone: Tuple[float, float], lookback: int = 5) -> float:
        """
        U4 & FIX 1: Checks if price actually bounced from the zone in the past.
        Moves at least 0.5 ATR away within 'lookback' bars.
        """
        z_low, z_high = zone
        atr = PriceActionEngine.calculate_atr(df)
        min_bounce = atr * 0.5
        
        touches = 0
        respected = 0
        
        # Iterate through df to find historical touches
        for i in range(max(0, len(df) - 100), len(df) - lookback):
            candle = df.iloc[i]
            c_low = PriceActionEngine._safe_float(candle['low'])
            c_high = PriceActionEngine._safe_float(candle['high'])
            c_close = PriceActionEngine._safe_float(candle['close'])

            # Support test: price dipped into zone from above, then bounced back up
            if c_low <= z_high and c_close >= z_high:
                touches += 1
                future = df.iloc[i+1 : i+1+lookback]
                if future.empty: 
                    continue
                if (future['close'].max() - c_close) >= min_bounce:
                    respected += 1

            # Resistance test: price spiked into zone from below, then rejected back down
            elif c_high >= z_low and c_close <= z_low:
                touches += 1
                future = df.iloc[i+1 : i+1+lookback]
                if future.empty: 
                    continue
                if (c_close - future['close'].min()) >= min_bounce:
                    respected += 1
                    
        return round(respected / touches, 2) if touches > 0 else 0.0

    @staticmethod
    def classify_zone_status(df: pd.DataFrame, zone: Tuple[float, float], zone_type: str, breach_threshold: float = 0.003) -> str:
        """
        U5 & FIX 2: Returns 'ACTIVE', 'BREACHED', or 'FLIPPED'.
        Prevents trading at dead zones.
        """
        z_low, z_high = zone
        if df is None or df.empty: return "ACTIVE"
        
        current_price = PriceActionEngine._safe_float(df['close'].iloc[-1])
        breach_buffer = current_price * breach_threshold # FIX 2: Reference current price
        
        if zone_type == "support":
            if current_price < z_low - breach_buffer:
                # Check for Flip
                recent_highs = df['high'].iloc[-10:]
                if any((z_low <= h <= z_high + breach_buffer) for h in recent_highs): return "FLIPPED"
                return "BREACHED"
        else: # resistance
            if current_price > z_high + breach_buffer:
                recent_lows = df['low'].iloc[-10:]
                if any((z_low - breach_buffer <= l <= z_high) for l in recent_lows): return "FLIPPED"
                return "BREACHED"
        return "ACTIVE"

    @staticmethod
    def find_mtf_confluent_zones(df_5m: pd.DataFrame, df_15m: pd.DataFrame, zone_type: str = "support", overlap_tolerance: float = 0.003) -> List[Dict[str, Any]]:
        """
        U6 & FIX 4: Returns zones where 5m and 15m S/R overlap.
        These are the highest-conviction institutional areas.
        """
        s5, r5 = PriceActionEngine.find_support_resistance(df_5m)
        s15, r15 = PriceActionEngine.find_support_resistance(df_15m)
        
        z5 = s5 if zone_type == "support" else r5
        z15 = s15 if zone_type == "support" else r15
        
        confluent = []
        for p5 in z5:
            for p15 in z15:
                if abs(p5['center'] - p15['center']) / p5['center'] <= overlap_tolerance:
                    confluent.append({
                        "zone": (min(p5['zone'][0], p15['zone'][0]), max(p5['zone'][1], p15['zone'][1])),
                        "center": (p5['center'] + p15['center']) / 2,
                        "strength": p5['strength'] + p15['strength'] * 1.5,
                        "recency": max(p5['recency'], p15['recency']),
                        "type": zone_type,
                        "mtf_confluence": True
                    })
        
        # FIX 4: Graceful fallback to single-TF if no confluent overlap
        if not confluent:
            fallback = z5 if z5 else z15
            for z in fallback:
                z['mtf_confluence'] = False
            return sorted(fallback, key=lambda x: x['strength'], reverse=True)[:3]

        return sorted(confluent, key=lambda x: x['strength'], reverse=True)[:3]

    @staticmethod
    def find_support_resistance(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Wrapper to produce the new Rectangle Zones."""
        s_points, r_points = PriceActionEngine.detect_swings(df)
        s_clusters = PriceActionEngine.cluster_levels(s_points)
        r_clusters = PriceActionEngine.cluster_levels(r_points)
        
        supports = PriceActionEngine.build_zones(df, s_clusters, "support")
        resistances = PriceActionEngine.build_zones(df, r_clusters, "resistance")
        
        # FIX 5: Sort by distance from current price and label S1/S2/R1/R2
        current_price = PriceActionEngine._safe_float(df['close'].iloc[-1])

        # Sort supports: nearest below current price first
        supports_below = sorted(
            [s for s in supports if s['center'] < current_price],
            key=lambda x: current_price - x['center']
        )
        supports_above = sorted(
            [s for s in supports if s['center'] >= current_price],
            key=lambda x: x['center'] - current_price
        )
        supports = supports_below + supports_above

        # Sort resistances: nearest above current price first
        resistances_above = sorted(
            [r for r in resistances if r['center'] > current_price],
            key=lambda x: x['center'] - current_price
        )
        resistances_below = sorted(
            [r for r in resistances if r['center'] <= current_price],
            key=lambda x: current_price - x['center']
        )
        resistances = resistances_above + resistances_below

        # Add labels: S1, S2, S3... and R1, R2, R3...
        support_labels = ['S1', 'S2', 'S3']
        for i, s in enumerate(supports):
            s['label'] = support_labels[i] if i < len(support_labels) else f'S{i+1}'

        resistance_labels = ['R1', 'R2', 'R3']
        for i, r in enumerate(resistances):
            r['label'] = resistance_labels[i] if i < len(resistance_labels) else f'R{i+1}'

        return supports, resistances

    @staticmethod
    def get_zone_summary(df: pd.DataFrame, df_5m: pd.DataFrame = None, 
                         df_15m: pd.DataFrame = None) -> dict:
        """
        Returns S1/S2/R1/R2 summary with full zone metadata.
        Uses MTF confluence zones if df_5m and df_15m provided, otherwise single-TF.
        
        Returns dict with keys: current_price, S1, S2, R1, R2
        Each zone contains: zone_low, zone_high, center, strength, respect_ratio, 
                            status, mtf, distance_pct
        """
        # Use MTF zones if multiple timeframes provided
        if df_5m is not None and df_15m is not None:
            supports = PriceActionEngine.find_mtf_confluent_zones(df_5m, df_15m, 'support')
            resistances = PriceActionEngine.find_mtf_confluent_zones(df_5m, df_15m, 'resistance')
        else:
            supports, resistances = PriceActionEngine.find_support_resistance(df)

        current_price = PriceActionEngine._safe_float(df['close'].iloc[-1])
        
        summary = {'current_price': round(current_price, 2)}
        
        # Initialize zone placeholders
        zone_keys = {
            'S1': None, 'S2': None,
            'R1': None, 'R2': None
        }
        
        # Populate support zones (S1, S2)
        for s in supports[:2]:
            label = s.get('label', '')
            if label in zone_keys:
                zone_keys[label] = {
                    'zone_low': round(s['zone'][0], 2),
                    'zone_high': round(s['zone'][1], 2),
                    'center': round(s['center'], 2),
                    'strength': round(s.get('strength', 0), 2),
                    'respect_ratio': s.get('respect_ratio', 0.0),
                    'status': PriceActionEngine.classify_zone_status(df, s['zone'], 'support'),
                    'mtf': s.get('mtf_confluence', False),
                    'distance_pct': round(abs(current_price - s['center']) / current_price * 100, 2)
                }
        
        # Populate resistance zones (R1, R2)
        for r in resistances[:2]:
            label = r.get('label', '')
            if label in zone_keys:
                zone_keys[label] = {
                    'zone_low': round(r['zone'][0], 2),
                    'zone_high': round(r['zone'][1], 2),
                    'center': round(r['center'], 2),
                    'strength': round(r.get('strength', 0), 2),
                    'respect_ratio': r.get('respect_ratio', 0.0),
                    'status': PriceActionEngine.classify_zone_status(df, r['zone'], 'resistance'),
                    'mtf': r.get('mtf_confluence', False),
                    'distance_pct': round(abs(current_price - r['center']) / current_price * 100, 2)
                }
        
        summary.update(zone_keys)
        return summary

    @staticmethod
    def _safe_float(x, default: float = 0.0) -> float:
        try:
            if x is None: return float(default)
            if isinstance(x, pd.Series):
                return float(x.iloc[0])
            if isinstance(x, (np.ndarray,)):
                return float(x.item())
            return float(x)
        except Exception:
            try:
                return float(np.array(x).item())
            except Exception:
                return float(default)

    @staticmethod
    def is_near_level(price: float, zones: List[Dict[str, Any]]) -> bool:
        """Checks if price is within any of the rectangular zones."""
        if price is None or not zones:
            return False

        for z in zones:
            low, high = z["zone"]
            # Allow a tiny buffer (0.05%) outside the zone
            buffer = price * 0.0005
            if (low - buffer) <= price <= (high + buffer):
                return True
        return False

    @staticmethod
    def analyze_candle(candle: pd.Series) -> Tuple[float, float, float]:
        body = abs(PriceActionEngine._safe_float(candle['close']) - PriceActionEngine._safe_float(candle['open']))
        upper_wick = PriceActionEngine._safe_float(candle['high']) - max(PriceActionEngine._safe_float(candle['open']), PriceActionEngine._safe_float(candle['close']))
        lower_wick = min(PriceActionEngine._safe_float(candle['open']), PriceActionEngine._safe_float(candle['close'])) - PriceActionEngine._safe_float(candle['low'])
        return body, upper_wick, lower_wick

    @staticmethod
    def is_bullish_rejection(candle: pd.Series) -> bool:
        body, upper, lower = PriceActionEngine.analyze_candle(candle)
        return lower > body * 2

    @staticmethod
    def is_bearish_rejection(candle: pd.Series) -> bool:
        body, upper, lower = PriceActionEngine.analyze_candle(candle)
        return upper > body * 2

    @staticmethod
    def is_strong_bullish(candle: pd.Series) -> bool:
        body, upper, lower = PriceActionEngine.analyze_candle(candle)
        return body > (upper + lower)

    @staticmethod
    def is_doji(candle: pd.Series) -> bool:
        body, upper, lower = PriceActionEngine.analyze_candle(candle)
        return body < (upper + lower) * 0.2

    @staticmethod
    def last_three_candles(df: pd.DataFrame) -> str:
        if df is None or len(df) < 3: return "INSUFFICIENT_DATA"
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        bullish = sum([1 for c in [c1, c2, c3] if PriceActionEngine._safe_float(c['close']) > PriceActionEngine._safe_float(c['open'])])
        bearish = sum([1 for c in [c1, c2, c3] if PriceActionEngine._safe_float(c['close']) < PriceActionEngine._safe_float(c['open'])])
        if bullish >= 2: return "BULLISH_MOMENTUM"
        elif bearish >= 2: return "BEARISH_MOMENTUM"
        else: return "INDECISION"

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        """Calculates Average True Range for volatility-based stops."""
        if df is None or len(df) < period + 1: return 0.0
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        return float(true_range.rolling(period).mean().iloc[-1])

    @staticmethod
    def detect_volume_spike(df: pd.DataFrame, period: int = 20, multiplier: float = 1.5) -> bool:
        if df is None or 'Volume' not in df.columns: return False
        try:
            if len(df['volume'].dropna()) < period: return False
            vol_mean = PriceActionEngine._safe_float(df['volume'].rolling(period).mean().iloc[-1])
            last_vol = PriceActionEngine._safe_float(df['volume'].iloc[-1])
            return (vol_mean > 0) and (last_vol > vol_mean * multiplier)
        except Exception: return False

    @staticmethod
    def volume_confirmation(df: pd.DataFrame) -> str:
        spike = PriceActionEngine.detect_volume_spike(df)
        if df is None or len(df) < 1: return 'NEUTRAL'
        last = df.iloc[-1]
        c, o = PriceActionEngine._safe_float(last['close']), PriceActionEngine._safe_float(last['open'])
        if spike and c > o: return 'STRONG_BULLISH'
        if spike and c < o: return 'STRONG_BEARISH'
        if not spike: return 'WEAK_MOVE'
        return 'NEUTRAL'

    @staticmethod
    def trap_signal(df: pd.DataFrame, supports: List[Dict[str, Any]], resistances: List[Dict[str, Any]], tolerance: float = 5.0) -> Tuple[str, Any]:
        """Simple trap check using zones."""
        if df is None or len(df) < 2: return "NO_TRAP", None
        last = df.iloc[-1]
        low, high, close = last['low'], last['high'], last['close']
        
        # Check if last candle dipped into support zone and closed above it (Bullish Trap)
        for s in supports:
            z_low, z_high = s['zone']
            if low < z_low and close > z_high:
                return "BUY_TRAP_REVERSAL", z_low
                
        # Check if last candle spiked into resistance and closed below it (Bearish Trap)
        for r in resistances:
            z_low, z_high = r['zone']
            if high > z_high and close < z_low:
                return "SELL_TRAP_REVERSAL", z_high
                
        return "NO_TRAP", None

    @staticmethod
    def analyze_timeframe(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 3:
            return {'trend': 'SIDEWAYS', 'momentum': 'INSUFFICIENT_DATA', 'candle': 'NEUTRAL', 'vol_spike': False}
        structure = PriceActionEngine.detect_market_structure(df)
        trend = PriceActionEngine.get_trend(structure)
        momentum = PriceActionEngine.last_three_candles(df)
        last = df.iloc[-1]
        candle = 'BULLISH' if PriceActionEngine.is_strong_bullish(last) or PriceActionEngine.is_bullish_rejection(last) else \
                 'BEARISH' if PriceActionEngine.is_bearish_rejection(last) else 'NEUTRAL'
        vol_spike = PriceActionEngine.detect_volume_spike(df)
        return {'trend': trend, 'momentum': momentum, 'candle': candle, 'vol_spike': vol_spike}

    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if df is None or df.empty: return df
        if not isinstance(df.index, pd.DatetimeIndex): df.index = pd.to_datetime(df.index)
        logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        resampled = df.resample(timeframe).apply(logic).dropna()
        # Ensure lowercase duplicates for downstream modules
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in resampled.columns:
                resampled[col.lower()] = resampled[col]
        return resampled

    @staticmethod
    def final_trading_decision(mtf_analyses: Dict[str, Any], option_df: pd.DataFrame, price_df: pd.DataFrame, symbol: str = "UNKNOWN", prior_ohlc: Dict[str, float] = None, intermarket_context: Dict[str, Any] = None, backtest_mode: bool = False, strategy_isolation_filter: str = None) -> Dict[str, Any]:
        from modules.regime.integration import MarketRegimeAdapter
        from modules.vp_avwap.integration import VolumeProfileAdapter
        
        # 0. REGIME CLASSIFICATION
        adapter = MarketRegimeAdapter()
        regime_decision = adapter.get_regime_decision(mtf_analyses, backtest_mode=backtest_mode)
        
        out = {
            'trade': 'NO TRADE', 
            'confidence': 0, 
            'reasons': [f"REGIME: {regime_decision.regime}"], 
            'checklist_score': 0,
            'entry': None,
            'sl': None,
            'target1': None,
            'target2': None,
            'regime': regime_decision.regime
        }
        
        if not regime_decision.allow_trades:
            out['reasons'].append("TRADE BLOCKED BY REGIME")
            return out

        # Apply Regime Overrides (e.g., min_score_delta)
        base_config = {'min_score': 5.5} 
        config = adapter.apply_overrides(base_config, regime_decision)
        
        # 0.5. VOLUME PROFILE & VWAP LEVELS
        atr_5m = PriceActionEngine.calculate_atr(mtf_analyses.get('5m'))
        vp_adapter = VolumeProfileAdapter()
        vp_levels = vp_adapter.get_vp_levels(symbol, mtf_analyses, mtf_analyses.get('1m'), atr_5m)

        # 0.7. SMART MONEY CONCEPTS (SMC)
        from modules.smc.integration import SMCAdapter, merge_with_smc
        smc_adapter = SMCAdapter()
        
        # Preopen range proxy (09:00-09:15)
        preopen = {'high': mtf_analyses['1m']['high'].iloc[0], 'low': mtf_analyses['1m']['low'].iloc[0]}
        
        smc_state = smc_adapter.get_smc_state(symbol, mtf_analyses, prior_ohlc or {}, preopen)
        
        # Merge levels
        vp_levels.confluence_levels = merge_with_smc(vp_levels.confluence_levels, smc_state, atr_5m)
        
        if price_df is None or price_df.empty: return out
        
        # DEBUG: Check columns
        if 'Close' not in price_df.columns:
            return out

        # 1. New Rectangle S/R Zones
        supports, resistances = PriceActionEngine.find_support_resistance(price_df)
        current_price = PriceActionEngine._safe_float(price_df.iloc[-1]['close'])
        
        # 2. Analyze Timeframes
        tf15 = PriceActionEngine.analyze_timeframe(mtf_analyses.get('15m'))
        tf5 = PriceActionEngine.analyze_timeframe(mtf_analyses.get('5m'))
        tf1 = PriceActionEngine.analyze_timeframe(mtf_analyses.get('1m'))
        
        # Safety for NoneType analyses
        if tf15 is None: tf15 = {'trend': 'SIDEWAYS', 'momentum': 'INDECISION', 'candle': 'NEUTRAL'}
        if tf5 is None: tf5 = {'trend': 'SIDEWAYS', 'momentum': 'INDECISION', 'candle': 'NEUTRAL'}
        if tf1 is None: tf1 = {'trend': 'SIDEWAYS', 'momentum': 'INDECISION', 'candle': 'NEUTRAL'}
        
        pa_trend = PriceActionEngine.get_trend(PriceActionEngine.detect_market_structure(price_df))
        volume_signal = PriceActionEngine.volume_confirmation(price_df)
        trap_type, _ = PriceActionEngine.trap_signal(price_df, supports, resistances)
        
        # --- MOMENTUM & VOLUME FILTERS (Converted from hard-reject to weighted confluence) ---
        # We no longer exit early here. We allow the checklist score to decide.
        # This prevents the 'silent killer' effect where valid zones are ignored due to slightly low volume.

        reasons = []
        last_candle = price_df.iloc[-1]
        c_low = PriceActionEngine._safe_float(last_candle['low'])
        c_high = PriceActionEngine._safe_float(last_candle['high'])
        c_close = PriceActionEngine._safe_float(last_candle['close'])

        # ZONE TOUCH-AND-REVERSAL ENTRY LOGIC
        valid_reversal = False
        potential_direction = 'SIDEWAYS'
        
        # Check Resistance Rejection (PE) or Breakout (CE)
        if not valid_reversal:
            for r in resistances:
                z_low, z_high = r['zone']
                # Breakout UP (CE)
                if c_close > z_high:
                    valid_reversal = True
                    potential_direction = 'BULLISH'
                    label = r.get('label', 'R?')
                    reasons.append(f'Breakout above {label} at {c_close}')
                    out['setup_override'] = "BREAKOUT"
                    break
                # Basic Touch-and-Rejection
                if c_high >= z_low and (c_close < z_low or tf1.get('candle') == 'BEARISH'):
                    valid_reversal = True
                    potential_direction = 'BEARISH'
                    label = r.get('label', 'R?')
                    reasons.append(f'{label} Rejection at {c_close}')
                    break
        
        # Check Support Rejection (CE) or Breakout (PE)
        if not valid_reversal:
            for s in supports:
                z_low, z_high = s['zone']
                # Breakout DOWN (PE)
                if c_close < z_low:
                    valid_reversal = True
                    potential_direction = 'BEARISH'
                    label = s.get('label', 'S?')
                    reasons.append(f'Breakout below {label} at {c_close}')
                    out['setup_override'] = "BREAKOUT"
                    break
                # Basic Touch-and-Bounce
                if c_low <= z_high and (c_close > z_high or tf1.get('candle') == 'BULLISH'):
                    valid_reversal = True
                    potential_direction = 'BULLISH'
                    label = s.get('label', 'S?')
                    reasons.append(f'{label} Rejection Bounce at {c_close}')
                    break
            
        if not valid_reversal:
            # DEBUG: Why no reversal?
            closest_s = supports[0]['zone'] if supports else "None"
            closest_r = resistances[0]['zone'] if resistances else "None"
            out['reasons'].append("No clear bounce/rejection from S/R lines - Filtering out.")
            return out

        direction = potential_direction

        # PHASE 2: SCORE REBALANCING
        score = 0.0
        reasons = []

        # 1. ZONE QUALITY (Primary Component)
        zone_quality_score = 2.0  # Base for valid zone touch
        active_zone = None
        
        if direction == 'BULLISH' and supports and len(supports) > 0:
            active_zone = supports[0]
            if active_zone.get('label') == 'S1':
                zone_quality_score += 2.0
                if active_zone.get('respect_ratio', 0) >= 0.75: zone_quality_score += 2.0
                elif active_zone.get('respect_ratio', 0) >= 0.5: zone_quality_score += 1.0
                if active_zone.get('mtf_confluence'): zone_quality_score += 1.5
            elif active_zone.get('label') == 'S2':
                zone_quality_score += 1.0
                if active_zone.get('respect_ratio', 0) >= 0.75: zone_quality_score += 1.5
        elif direction == 'BEARISH' and resistances and len(resistances) > 0:
            active_zone = resistances[0]
            if active_zone.get('label') == 'R1':
                zone_quality_score += 2.0
                if active_zone.get('respect_ratio', 0) >= 0.75: zone_quality_score += 2.0
                elif active_zone.get('respect_ratio', 0) >= 0.5: zone_quality_score += 1.0
                if active_zone.get('mtf_confluence'): zone_quality_score += 1.5
            elif active_zone.get('label') == 'R2':
                zone_quality_score += 1.0
                if active_zone.get('respect_ratio', 0) >= 0.75: zone_quality_score += 1.5

        score += zone_quality_score
        z_label = active_zone.get('label', '??') if active_zone else '??'
        reasons.append(f'{z_label} Zone Quality (+{zone_quality_score:.1f})')

        # 2. PRICE ACTION CONFIRMATION (Secondary)
        if tf1.get('candle') == direction: 
            score += 1.0
            reasons.append('1m Candle Confirms (+1.0)')

        # 3. TREND ALIGNMENT (Bonus)
        if tf15.get('trend') == direction: 
            score += 1.5
            reasons.append('15m Trend Alignment (+1.5)')
        if tf5.get('trend') == direction: 
            score += 0.75
            reasons.append('5m Trend Alignment (+0.75)')

        # 4. VOLUME (Nice-to-have)
        vol_type = 'STRONG_BULLISH' if direction == 'BULLISH' else 'STRONG_BEARISH'
        if volume_signal == vol_type: 
            score += 1.0
            reasons.append('Volume Confirms (+1.0)')

        # 5. TRAP (High conviction overlay)
        if trap_type != "NO_TRAP": 
            score += 2.0
            reasons.append(f'Trap Detected: {trap_type} (+2.0)')

        # PHASE 1: ADAPTIVE THRESHOLD SYSTEM
        base_trending = 3.0
        base_ranging = 4.0
        
        is_elite_zone = active_zone.get('label') in ['S1', 'S2', 'R1', 'R2'] if active_zone else False
        zone_respect = active_zone.get('respect_ratio', 0) if active_zone else 0

        # FILTER: Minimum zone quality
        if zone_respect < 0.50:
            out['trade'] = 'NO TRADE'
            out['reasons'].append(f'Zone respect too low: {zone_respect:.2f} < 0.50')
            return out

        if is_elite_zone:
            z_lbl = active_zone.get('label')
            if zone_respect >= 0.75:
                threshold = base_trending * 0.9 if pa_trend in ["BULLISH", "BEARISH"] else base_ranging * 0.8
                reasons.append(f'Elite {z_lbl} (Respect: {zone_respect:.2f}, Threshold: {threshold:.1f})')
            elif zone_respect >= 0.5:
                threshold = base_trending if pa_trend in ["BULLISH", "BEARISH"] else base_ranging * 0.9
                reasons.append(f'{z_lbl} Zone (Threshold: {threshold:.1f})')
            else:
                threshold = base_trending * 1.1 if pa_trend in ["BULLISH", "BEARISH"] else base_ranging
                reasons.append(f'{z_lbl} Low Respect (Threshold: {threshold:.1f})')
        else:
            threshold = base_ranging
            reasons.append(f'Regime Threshold: {threshold:.1f}')

        out['checklist_score'] = score
        out['confidence'] = min(100, int(score * 10))
        out['reasons'] = reasons

        if score >= threshold:
            print(f"TRADE APPROVED | Score: {score:.2f} >= {threshold:.2f} | {direction} | Reasons: {reasons}")
            trade_type = 'CE' if direction == 'BULLISH' else 'PE'
            out['trade'] = trade_type
            entry = current_price
            out['entry'] = PriceActionEngine._safe_float(entry)

            # APPLY VOLUME PROFILE SCORING & MERGE
            out = vp_adapter.score_and_merge(out, vp_levels, regime_decision.regime, atr_5m)
            
            # APPLY SMC SCORING
            out = smc_adapter.score_and_merge(out, smc_state, vp_levels, regime_decision.regime, atr_5m)
            
            # --- FIX 3: MODULE 6 INTERMARKET & RS GATE ---
            from modules.intermarket.integration import IntermarketAdapter
            inter_adapter = IntermarketAdapter()
            
            if intermarket_context:
                # Support for smoke testing via 'mock_verdict' key
                if 'mock_verdict' in intermarket_context:
                    inter_verdict = intermarket_context['mock_verdict']
                else:
                    inter_verdict = inter_adapter.engine.evaluate(
                        symbol=symbol,
                        candidate_direction=out['trade'], 
                        setup_type=out.get('setup', 'ZONE_REJECTION'),
                        active_window=filter_decision.time_of_day.active_window if 'filter_decision' in locals() else "UNKNOWN",
                        regime=regime_decision.regime,
                        smc_tier=smc_state.tier_label if hasattr(smc_state, 'tier_label') else "MINOR",
                        now_ist=mtf_analyses['1m'].index[-1],
                        nifty_ctx=intermarket_context.get('nifty_ctx'),
                        sector_indices=intermarket_context.get('sector_indices', {}),
                        stock_ohlcv_session=mtf_analyses.get('5m'), 
                        universe_snapshot=intermarket_context.get('universe_snapshot'),
                        cross_assets=intermarket_context.get('cross_assets'),
                        global_ctx=intermarket_context.get('global_ctx'),
                        banknifty_ctx=intermarket_context.get('banknifty_ctx')
                    )
                
                if not inter_verdict.allow:
                    print(f"INTERMARKET VETO | Reasons: {inter_verdict.veto_reasons}")
                    out['trade'] = 'NO TRADE'
                    out['reasons'].extend([f"Intermarket Veto: {r}" for r in inter_verdict.veto_reasons])
                    return out
                
                out['checklist_score'] += inter_verdict.final_delta
                out['intermarket_metadata'] = inter_verdict
                out['reasons'].append(f"Intermarket Aligned (Delta: +{inter_verdict.final_delta:.2f})")

            # --- NEW: CONTEXT FILTER STACK (Final Veto Gate) ---
            from modules.context_filters.integration import ContextFilterAdapter
            context_adapter = ContextFilterAdapter()
            
            filter_decision = context_adapter.evaluate_context(
                symbol, out, mtf_analyses, regime_decision.regime, prior_ohlc or {}, backtest_mode=backtest_mode
            )
            
            if not filter_decision.allow_trade:
                print(f"TRADE VETOED | Reasons: {filter_decision.veto_reasons}")
                out['trade'] = 'NO TRADE'
                out['reasons'].extend(filter_decision.veto_reasons)
                return out
                
            # Apply Filter Weights & Threshold Delta
            out['checklist_score'] *= filter_decision.combined_weight_multiplier
            # effective_threshold = threshold + filter_decision.combined_threshold_delta
            # Note: We adjust score or threshold. Standardizing on adjusting score here.
            
            out['context_metadata'] = filter_decision
            
            # --- CONSOLIDATED SETUP CATEGORIZATION & FILTERING ---
            pullback = (pa_trend == 'BULLISH' and direction == 'BULLISH' and c_low < active_zone.get('center', 0)) if (active_zone and direction == 'BULLISH') else False
            if direction == 'BEARISH' and pa_trend == 'BEARISH' and active_zone:
                pullback = c_high > active_zone.get('center', 0)

            setup = out.get('setup_override', "ZONE_REJECTION")
            if setup == "ZONE_REJECTION":
                if trap_type != "NO_TRAP":
                    setup = "TRAP_REVERSAL"
                elif smc_state and hasattr(smc_state, 'sweeps') and len(smc_state.sweeps) > 0:
                    setup = "LIQUIDITY_SWEEP"
                elif smc_state and hasattr(smc_state, 'order_blocks') and len(smc_state.order_blocks) > 0:
                    setup = "OB_MITIGATION"
                elif out.get('vp_metadata') and out['vp_metadata'].regime_weighted_score > 1.5:
                    setup = "VP_CONFLUENCE"
                elif pullback:
                    setup = "PULLBACK"
                
            out['setup'] = setup

            # 1. Strategy Activation Filter
            strategy_filter = PriceActionEngine.load_strategy_filter()
            if not PriceActionEngine.is_strategy_allowed(setup, symbol, out['checklist_score'], strategy_filter):
                out['trade'] = 'NO TRADE'
                out['reasons'].append(f"Strategy filter: {setup} disabled for {symbol} or score too low")
                return out

            # 2. Strategy Isolation Filter (Internal Backtest Testing)
            if strategy_isolation_filter and setup != strategy_isolation_filter:
                out['trade'] = 'NO TRADE'
                out['reasons'].append(f"Isolated setup filter: {setup} != {strategy_isolation_filter}")
                return out
            
            # --- VOLATILITY-TIERED STOP LOSS BUFFER ---
            atr = PriceActionEngine.calculate_atr(price_df)
            atr_series = price_df['high'] - price_df['low']
            atr_20 = atr_series.rolling(20).mean()
            last_atr_20 = atr_20.iloc[-1] if not atr_20.empty and not pd.isna(atr_20.iloc[-1]) else atr
            current_atr_pct = (atr / last_atr_20) if last_atr_20 > 0 else 1.0

            if current_atr_pct > 1.3: # High volatility
                vol_multiplier = 0.8 # Wider stop
            elif current_atr_pct < 0.7: # Low volatility
                vol_multiplier = 0.3 # Tighter stop
            else:
                vol_multiplier = 0.5 # Normal regime
            
            buffer = atr * vol_multiplier
            
            if trade_type == 'CE':
                z = supports[0]['zone'] if (supports and len(supports) > 0) else (entry - buffer*2, entry - buffer)
                sl = z[0] - buffer 
                if sl >= entry: sl = entry - buffer # Final safety
                dist = entry - sl
                out['target1'] = entry + 1.0 * dist
                out['target2'] = entry + 3.0 * dist
            else:
                z = resistances[0]['zone'] if (resistances and len(resistances) > 0) else (entry + buffer, entry + buffer*2)
                sl = z[1] + buffer
                if sl <= entry: sl = entry + buffer # Final safety
                dist = sl - entry
                out['target1'] = entry - 1.0 * dist
                out['target2'] = entry - 3.0 * dist
 
            out['entry'] = PriceActionEngine._safe_float(entry)
            out['sl'] = PriceActionEngine._safe_float(sl)
            
            # ENTRY REFINEMENT
            if trade_type == 'CE':
                out['trigger_price'] = PriceActionEngine._safe_float(c_high + (c_high * 0.0005))
            else:
                out['trigger_price'] = PriceActionEngine._safe_float(c_low - (c_low * 0.0005))

            # UPGRADE 4: Zone Entry Tolerance (Immediate Entry for High-Conviction)
            if trade_type == 'CE' and supports and supports[0].get('mtf_confluence') and supports[0].get('respect_ratio', 0) >= 0.75:
                out['trigger_price'] = out['entry']
                out['reasons'].append('Immediate Entry (High-Conviction MTF Zone)')
            elif trade_type == 'PE' and resistances and resistances[0].get('mtf_confluence') and resistances[0].get('respect_ratio', 0) >= 0.75:
                out['trigger_price'] = out['entry']
                out['reasons'].append('Immediate Entry (High-Conviction MTF Zone)')
                
            out['target1'] = PriceActionEngine._safe_float(out.get('target1'))
            out['target2'] = PriceActionEngine._safe_float(out.get('target2'))

            # --- NEW: META-LEARNING (MIRROR) LAYER ---
            from modules.learning import LearningSystem
            learning_db = LearningSystem()
            history = learning_db.get_similar_feedback(setup, symbol, regime_decision.regime)
            
            if not history.empty:
                # If 3+ of last 5 similar setups were losers
                losses = history[history['result'].str.contains('LOSS|FORCE_CLOSE|STALLED|FAIL', na=False, case=False)]
                if len(losses) >= 3:
                    out['checklist_score'] *= 0.8 # Penalty
                    out['reasons'].append(f"Learning Layer Penalty: High failure rate for {setup}")
                elif len(history[history['result'].str.contains('win|hit', na=False, case=False)]) >= 3:
                    out['checklist_score'] += 0.5 # Bonus
                    out['reasons'].append("Learning Layer Bonus: Consistent history")

            # --- MODULE 5: RISK & TRADE MANAGEMENT GATE ---

            from modules.risk_exec.integration import RiskExecAdapter
            risk_adapter = RiskExecAdapter()
            
            # Build objects
            approved_signal = risk_adapter.build_approved_signal(symbol, out, mtf_analyses, regime_decision.regime)
            market_context = risk_adapter.build_market_context(
                symbol, mtf_analyses, regime_decision, vp_levels, smc_state, 
                filter_decision.time_of_day.active_window if 'filter_decision' in locals() else "UNKNOWN",
                prior_ohlc or {}
            )
            
            # Risk Engine Call
            # Note: In a real bot, we'd pass actual portfolio equity and open positions
            # For this 'decision' function, we check if the trade IS ALLOWED and get its adaptive parameters
            risk_dec = risk_adapter.engine.place_trade(
                signal=approved_signal,
                current_equity=100000.0, # Placeholder, real value comes from executor
                open_positions=[], 
                market_context=market_context
            )
            
            if risk_dec.action != "EXECUTED":
                print(f"RISK VETO | Reason: {risk_dec.veto_reason}")
                out['trade'] = 'NO TRADE'
                out['reasons'].append(f"Risk Veto: {risk_dec.veto_reason}")
                return out
                
            # Apply Adaptive Parameters
            out['qty'] = risk_dec.sizing.shares
            out['sl'] = risk_dec.sl.sl_price
            out['targets_plan'] = risk_dec.exits
            out['risk_metadata'] = risk_dec
            
            print(f"RISK APPROVED | Size: {out['qty']} | SL: {out['sl']} | R: {risk_dec.sl.per_share_risk}")
        else:
            if score > 2.5:
                print(f'DEBUG: {direction} REJECTED - Score {score:.2f} < {threshold:.2f}. Reasons: {reasons}')
            out['trade'] = 'NO TRADE'

        if PA_BRIDGE_AVAILABLE:
            try:
                pa_signals = PAEngineBridge.get_signals(price_df, timeframe='5m')
                # Overwrite 'out' if we have a valid PA signal with higher confidence
                best_pa = None
                for ps in pa_signals:
                    if ps['trade'] != 'NO TRADE':
                        if best_pa is None or ps['confidence'] > best_pa['confidence']:
                            best_pa = ps
                if best_pa and best_pa['confidence'] > out.get('confidence', 0):
                    out.update(best_pa)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"PA bridge signal fetch failed: {e}")

        return out
