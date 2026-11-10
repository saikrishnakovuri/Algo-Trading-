import pandas as pd
import numpy as np
import yaml
import os
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

try:
    from modules.pa_engine_bridge import PAEngineBridge
    PA_BRIDGE_AVAILABLE = True
except ImportError:
    PA_BRIDGE_AVAILABLE = False


class PriceActionEngine:
    """Price action utilities following the pipeline:

    RAW DATA -> MARKET STRUCTURE -> ZONES -> CANDLES -> CONFLUENCE -> DECISION
    """

    _config_cache = {}

    @staticmethod
    def load_strategy_filter():
        cache_key = "strategy_filter"
        if cache_key in PriceActionEngine._config_cache:
            return PriceActionEngine._config_cache[cache_key]
            
        try:
            if os.path.exists("config/strategy_filter.yaml"):
                with open("config/strategy_filter.yaml") as f:
                    config = yaml.safe_load(f).get("strategies", {})
                    PriceActionEngine._config_cache[cache_key] = config
                    return config
        except Exception:
            pass
        return {}

    @staticmethod
    def is_strategy_allowed(setup_type, symbol, score, strategy_filter):
        config = strategy_filter.get(setup_type, {})
        if not config:
            if setup_type == "ZONE_REJECTION" and score < 7.0: return False
            return True
        if not config.get("enabled", True): return False
        allowed = config.get("allowed_symbols", "ALL")
        if allowed != "ALL" and symbol not in allowed: return False
        min_score = config.get("min_score_override")
        if not min_score and setup_type == "ZONE_REJECTION": min_score = 7.0
        if min_score and score < min_score: return False
        return True

    @staticmethod
    def detect_market_structure(df: pd.DataFrame) -> str:
        if df is None or len(df) < 20: return "UNKNOWN"
        s_highs, s_lows = PriceActionEngine.detect_swings(df, window=3)
        if len(s_highs) < 2 or len(s_lows) < 2: return "RANGE"
        h2, h1 = s_highs[-1][1], s_highs[-2][1]
        l2, l1 = s_lows[-1][1], s_lows[-2][1]
        if h2 > h1 and l2 > l1: return "HH-HL"
        elif h2 < h1 and l2 < l1: return "LH-LL"
        else: return "RANGE"

    @staticmethod
    def get_trend(structure: str) -> str:
        if structure == "HH-HL": return "BULLISH"
        elif structure == "LH-LL": return "BEARISH"
        else: return "SIDEWAYS"

    @staticmethod
    def detect_swings(df: pd.DataFrame, window: int = 2) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        swing_highs, swing_lows = [], []
        if df is None or len(df) < (window * 2 + 1): return swing_highs, swing_lows
        highs, lows = df['high'].values, df['low'].values
        lookback = 200
        start_idx = max(2 * window, len(df) - lookback)
        for i in range(start_idx, len(df)):
            window_slice = highs[i - 2*window : i + 1]
            if len(window_slice) > 0 and highs[i-window] == window_slice.max():
                swing_highs.append((i-window, PriceActionEngine._safe_float(highs[i-window])))
            window_slice_low = lows[i - 2*window : i + 1]
            if len(window_slice_low) > 0 and lows[i-window] == window_slice_low.min():
                swing_lows.append((i-window, PriceActionEngine._safe_float(lows[i-window])))
        return swing_highs, swing_lows

    @staticmethod
    def cluster_levels(levels: List[Tuple[int, float]], tolerance: float = 0.002) -> List[Dict[str, Any]]:
        if not levels: return []
        clusters = []
        sorted_levels = sorted(levels, key=lambda x: x[1])
        for idx, price in sorted_levels:
            found = False
            for cluster in clusters:
                dynamic_tol = cluster['center'] * tolerance
                if abs(cluster['center'] - price) <= dynamic_tol:
                    cluster['indices'].append(idx); cluster['prices'].append(price)
                    cluster['center'] = sum(cluster['prices']) / len(cluster['prices'])
                    found = True; break
            if not found: clusters.append({"center": price, "prices": [price], "indices": [idx]})
        return clusters

    @staticmethod
    def build_zones(df: pd.DataFrame, clusters: List[Dict[str, Any]], zone_type: str = "support") -> List[Dict[str, Any]]:
        zones = []
        if df is None or df.empty: return zones
        atr = PriceActionEngine.calculate_atr(df, period=14)
        for cluster in clusters:
            indices, prices = cluster["indices"], cluster["prices"]
            candle_bodies = []
            for i in indices:
                candle = df.iloc[i]
                candle_bodies.append((PriceActionEngine._safe_float(candle['open']) + PriceActionEngine._safe_float(candle['close'])) / 2.0)
            avg_body, touch_count = sum(candle_bodies) / len(candle_bodies), len(prices)
            if zone_type == "support": lower, upper = min(prices), avg_body
            else: lower, upper = avg_body, max(prices)
            if lower > upper: lower, upper = upper, lower
            zone_width = upper - lower
            if atr > 0:
                center_price = (lower + upper) / 2.0
                if zone_width < atr * 0.3: lower, upper = center_price - atr * 0.15, center_price + atr * 0.15
                elif zone_width > atr * 2.0: lower, upper = center_price - atr * 1.0, center_price + atr * 1.0
            latest_idx = max(indices)
            recency = 1.0 / (len(df) - latest_idx + 1)
            respect = PriceActionEngine.score_zone_respect(df, (lower, upper))
            zones.append({"zone": (round(lower, 2), round(upper, 2)), "center": (lower + upper) / 2.0, "strength": touch_count, "recency": recency, "respect_ratio": respect, "type": zone_type})
        return sorted(zones, key=lambda x: (x["strength"] * 0.4 + x["recency"] * 0.2 + x["respect_ratio"] * 0.4), reverse=True)[:3]

    @staticmethod
    def score_zone_respect(df: pd.DataFrame, zone: Tuple[float, float], lookback: int = 5) -> float:
        z_low, z_high = zone
        atr = PriceActionEngine.calculate_atr(df)
        min_bounce, touches, respected = atr * 0.5, 0, 0
        start_idx = max(0, len(df) - 100)
        closes, lows, highs = df['close'].values, df['low'].values, df['high'].values
        for i in range(start_idx, len(df) - lookback):
            c_low, c_high, c_close = lows[i], highs[i], closes[i]
            if c_low <= z_high and c_close >= z_high:
                touches += 1
                if (closes[i+1 : i+1+lookback].max() - c_close) >= min_bounce: respected += 1
            elif c_high >= z_low and c_close <= z_low:
                touches += 1
                if (c_close - closes[i+1 : i+1+lookback].min()) >= min_bounce: respected += 1
        return round(respected / touches, 2) if touches > 0 else 0.0

    @staticmethod
    def find_support_resistance(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        s_pts, r_pts = PriceActionEngine.detect_swings(df)
        supports = PriceActionEngine.build_zones(df, PriceActionEngine.cluster_levels(s_pts), "support")
        resistances = PriceActionEngine.build_zones(df, PriceActionEngine.cluster_levels(r_pts), "resistance")
        cp = PriceActionEngine._safe_float(df['close'].iloc[-1])
        supports = sorted(supports, key=lambda x: abs(x['center'] - cp))
        for i, s in enumerate(supports): s['label'] = f"S{i+1}"
        resistances = sorted(resistances, key=lambda x: abs(x['center'] - cp))
        for i, r in enumerate(resistances): r['label'] = f"R{i+1}"
        return supports, resistances

    @staticmethod
    def final_trading_decision(mtf_analyses: Dict[str, Any], option_df: pd.DataFrame, price_df: pd.DataFrame, symbol: str = "UNKNOWN", prior_ohlc: Dict[str, float] = None, intermarket_context: Dict[str, Any] = None, backtest_mode: bool = False, strategy_isolation_filter: str = None, regime_adapter=None, vp_adapter=None, smc_adapter=None, intermarket_adapter=None, context_adapter=None, risk_adapter=None, learning_system=None) -> Dict[str, Any]:
        from modules.regime.integration import MarketRegimeAdapter
        from modules.vp_avwap.integration import VolumeProfileAdapter
        from modules.smc.integration import SMCAdapter, merge_with_smc
        from modules.intermarket.integration import IntermarketAdapter
        from modules.context_filters.integration import ContextFilterAdapter
        from modules.risk_exec.integration import RiskExecAdapter
        from modules.learning import LearningSystem

        if regime_adapter is None: regime_adapter = MarketRegimeAdapter()
        regime_decision = regime_adapter.get_regime_decision(mtf_analyses, backtest_mode=backtest_mode)
        out = {'trade': 'NO TRADE', 'reasons': [f"REGIME: {regime_decision.regime}"], 'checklist_score': 0, 'confidence': 0, 'entry': None, 'sl': None, 'target1': None, 'target2': None, 'regime': regime_decision.regime}
        if not regime_decision.allow_trades: return out

        atr_5m = PriceActionEngine.calculate_atr(mtf_analyses.get('5m'))
        if vp_adapter is None: vp_adapter = VolumeProfileAdapter()
        vp_levels = vp_adapter.get_vp_levels(symbol, mtf_analyses, mtf_analyses.get('1m'), atr_5m)
        if smc_adapter is None: smc_adapter = SMCAdapter()
        df_1m = mtf_analyses.get('1m')
        if not df_1m.empty:
            day_data = df_1m[df_1m.index.date == df_1m.index[-1].date()]
            preopen = {'high': day_data['high'].iloc[0], 'low': day_data['low'].iloc[0]} if not day_data.empty else {'high': df_1m['high'].iloc[0], 'low': df_1m['low'].iloc[0]}
        else: preopen = {'high':0, 'low':0}
        smc_state = smc_adapter.get_smc_state(symbol, mtf_analyses, prior_ohlc or {}, preopen)
        vp_levels.confluence_levels = merge_with_smc(vp_levels.confluence_levels, smc_state, atr_5m)

        supports, resistances = PriceActionEngine.find_support_resistance(price_df)
        cp = PriceActionEngine._safe_float(price_df.iloc[-1]['close'])
        tf5, tf1 = PriceActionEngine.analyze_timeframe(mtf_analyses.get('5m')), PriceActionEngine.analyze_timeframe(mtf_analyses.get('1m'))
        pa_trend = PriceActionEngine.get_trend(PriceActionEngine.detect_market_structure(price_df))
        last = price_df.iloc[-1]
        c_low, c_high, c_close = last['low'], last['high'], last['close']

        direction, active_zone, reasons = 'SIDEWAYS', None, []
        for r in resistances:
            if c_high >= r['zone'][0] and (c_close < r['zone'][0] or tf1['candle'] == 'BEARISH'):
                direction, active_zone = 'BEARISH', r; reasons.append(f"{r['label']} Rejection"); break
        if direction == 'SIDEWAYS':
            for s in supports:
                if c_low <= s['zone'][1] and (c_close > s['zone'][1] or tf1['candle'] == 'BULLISH'):
                    direction, active_zone = 'BULLISH', s; reasons.append(f"{s['label']} Rejection Bounce"); break
        if direction == 'SIDEWAYS': return out

        score = 2.0 + (active_zone['respect_ratio'] * 2.0)
        if tf1['candle'] == direction: score += 1.0; reasons.append("1m Candle Confirms")
        if tf5['trend'] == direction: score += 1.0; reasons.append("5m Trend Aligned")
        out['checklist_score'], out['reasons'] = score, reasons
        
        threshold = 5.5 if pa_trend in ["BULLISH", "BEARISH"] else 6.5
        if score >= threshold:
            out['trade'] = 'CE' if direction == 'BULLISH' else 'PE'
            out['entry'] = cp
            out = vp_adapter.score_and_merge(out, vp_levels, regime_decision.regime, atr_5m)
            out = smc_adapter.score_and_merge(out, smc_state, vp_levels, regime_decision.regime, atr_5m)
            
            if intermarket_adapter is None: intermarket_adapter = IntermarketAdapter()
            if intermarket_context:
                # FIX: Handle missing sector_indices and other args
                inter_verdict = intermarket_adapter.engine.evaluate(
                    symbol=symbol, candidate_direction="LONG" if out['trade'] == 'CE' else "SHORT", 
                    setup_type="ZONE_REJECTION", active_window="UNKNOWN", regime=regime_decision.regime, 
                    smc_tier=smc_state.tier_label if hasattr(smc_state, 'tier_label') else "MINOR",
                    now_ist=price_df.index[-1], nifty_ctx=intermarket_context.get('nifty_ctx'),
                    sector_indices=intermarket_context.get('sector_indices', {}),
                    stock_ohlcv_session=mtf_analyses.get('5m'), universe_snapshot=intermarket_context.get('universe_snapshot'),
                    cross_assets=intermarket_context.get('cross_assets'), 
                    banknifty_ctx=intermarket_context.get('banknifty_ctx'), global_ctx=intermarket_context.get('global_ctx')
                )
                if not inter_verdict.allow:
                    out['trade'] = 'NO TRADE'; out['reasons'].append(f"Intermarket Veto: {inter_verdict.veto_reasons}"); return out
                out['checklist_score'] += inter_verdict.final_delta

            if context_adapter is None: context_adapter = ContextFilterAdapter()
            f_dec = context_adapter.evaluate_context(symbol, out, mtf_analyses, regime_decision.regime, prior_ohlc or {}, backtest_mode=backtest_mode)
            if not f_dec.allow_trade:
                out['trade'] = 'NO TRADE'; out['reasons'].extend(f_dec.veto_reasons); return out
            out['checklist_score'] *= f_dec.combined_weight_multiplier
            
            if learning_system is None: learning_system = LearningSystem()
            hist = learning_system.get_similar_feedback("ZONE_REJECTION", symbol, regime_decision.regime)
            if not hist.empty and len(hist[hist['result'].str.contains('LOSS|FAIL', na=False)]) >= 3:
                out['checklist_score'] *= 0.8; out['reasons'].append("Learning Penalty")

            out['setup'] = "ZONE_REJECTION"
            if risk_adapter is None: risk_adapter = RiskExecAdapter()
            approved_sig = risk_adapter.build_approved_signal(symbol, out, mtf_analyses, regime_decision.regime)
            market_ctx = risk_adapter.build_market_context(symbol, mtf_analyses, regime_decision, vp_levels, smc_state, "UNKNOWN", prior_ohlc or {})
            risk_dec = risk_adapter.engine.place_trade(signal=approved_sig, current_equity=1000000.0, open_positions=[], market_context=market_ctx)
            if risk_dec.action != "EXECUTED":
                out['trade'] = 'NO TRADE'; out['reasons'].append(f"Risk Veto: {risk_dec.veto_reason}"); return out
            out['qty'], out['sl'], out['targets_plan'] = risk_dec.sizing.shares, risk_dec.sl.sl_price, risk_dec.exits
            out['trigger_price'] = c_high + 0.5 if out['trade'] == 'CE' else c_low - 0.5
        return out

    @staticmethod
    def analyze_timeframe(df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 3: return {'trend': 'SIDEWAYS', 'candle': 'NEUTRAL'}
        structure = PriceActionEngine.detect_market_structure(df)
        trend = PriceActionEngine.get_trend(structure)
        last = df.iloc[-1]
        candle = 'BULLISH' if last['close'] > last['open'] else 'BEARISH' if last['close'] < last['open'] else 'NEUTRAL'
        return {'trend': trend, 'candle': candle}

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        if df is None or len(df) < period + 1: return 0.0
        tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    @staticmethod
    def _safe_float(x, default: float = 0.0) -> float:
        try: return float(x.iloc[0]) if isinstance(x, pd.Series) else float(x)
        except: return default

    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if df is None or df.empty: return df
        logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
        resampled = df.resample(timeframe).agg(logic).dropna()
        for col in resampled.columns: resampled[col.lower()] = resampled[col]
        return resampled
