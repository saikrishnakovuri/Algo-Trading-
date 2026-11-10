import logging
import warnings
from typing import Optional, Dict, List
from modules.context_detector import ContextDetector
from modules.strategy_mapper import StrategyMapper, StrategyCandidate
from modules.confidence_scorer import ConfidenceScorer, CONFIDENCE_THRESHOLDS
from modules.strategy_definitions import STRATEGY_DEFINITIONS
from modules.market_memory_engine import MarketMemoryEngine
from modules.narrative_hierarchy import NarrativeHierarchyResolver
from modules.trade_tiers import TradeTierResolver

# Import all existing engines (DO NOT rewrite)
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.momentum_engine import MomentumBreakoutEngine as MomentumEngine
from modules.mean_reversion_engine import MeanReversionEngine
from modules.sweep_retest_engine import SweepRetestEngine
from modules.structure_strategy_engine import StructureStrategyEngine
from modules.candlestick_engine import CandlestickEngine
from modules.smc.engine import SmartMoneyConceptsEngine


logger = logging.getLogger(__name__)


class StrategyResult:
    """
    DEPRECATED — used by legacy StrategySelector.
    Will be removed in a future cleanup phase.
    """
    def __init__(self, strategy_name, signal, direction, entry, sl,
                 target1, target2=None, score=0, confidence_pct=0, 
                 setup_type="Standard", reasons=None):
        warnings.warn("StrategyResult is deprecated, use MasterStrategySelector signal dicts instead", DeprecationWarning, stacklevel=2)
        self.strategy_name = strategy_name
        self.signal = signal # 'BUY', 'SELL', 'HOLD'
        self.direction = direction # 'CE', 'PE'
        self.entry = entry
        self.sl = sl
        self.target1 = target1
        self.target2 = target2
        self.score = score
        self.confidence_pct = confidence_pct
        self.setup_type = setup_type
        self.reasons = reasons or []


class StrategySelector:
    """
    DEPRECATED — use MasterStrategySelector. Kept for backward compatibility.
    Main orchestrator for legacy multi-strategy scanning.
    """
    def __init__(self):
        warnings.warn("StrategySelector is deprecated, use MasterStrategySelector instead", DeprecationWarning, stacklevel=2)
        self.strategies = {} # {name: {'engine': obj, 'evaluate': func}}
        self.history = []

    def register(self, name, engine_obj, evaluate_func):
        self.strategies[name] = {
            'engine': engine_obj,
            'evaluate': evaluate_func
        }

    def select_best(self, df, symbol, config=None, **kwargs):
        """
        Runs all registered strategies and returns the one with highest confidence.
        """
        results = []
        for name, strat in self.strategies.items():
            try:
                res = strat['evaluate'](strat['engine'], df, symbol, config=config, **kwargs)
                if res:
                    print(f"DEBUG: {symbol} {name} signal={res.signal} conf={res.confidence_pct}")
                    if res.signal != 'HOLD' and res.confidence_pct > 0:
                        results.append(res)



            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error in strategy {name}: {e}")
        
        if not results:
            return None
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence_pct, reverse=True)
        best = results[0]
        
        # Log for learning layer
        self.history.append({
            'timestamp': df.index[-1] if hasattr(df, 'index') else None,
            'symbol': symbol,
            'selected': best.strategy_name,
            'confidence': best.confidence_pct,
            'all_candidates': [r.strategy_name for r in results]
        })
        
        return best

    def get_stats(self):
        from collections import Counter
        counts = Counter(h['selected'] for h in self.history)
        total = len(self.history)
        return {n: {'count': c, 'pct': round(c/total*100,1)} 
                for n, c in counts.most_common()} if total > 0 else {}


# ══════════════════════════════════════════════════════
# NEW: MASTER STRATEGY SELECTOR (PHASE 6)
# ══════════════════════════════════════════════════════


class MasterStrategySelector:

    def __init__(self):
        self.context_detector = ContextDetector()
        self.strategy_mapper  = StrategyMapper()
        self.confidence_scorer = ConfidenceScorer()
        self.market_memory = MarketMemoryEngine()
        self.narrative_hierarchy = NarrativeHierarchyResolver()
        self.trade_tiers = TradeTierResolver()

        # Phase 18: Load ATR exit overrides from config
        self.phase18_overrides = {}
        self.volatility_gate = {}
        try:
            import yaml
            with open("config/risk_execution.yaml", "r", encoding="utf-8") as f:
                _cfg = yaml.safe_load(f)
                self.phase18_overrides = _cfg.get("exits", {}).get("strategy_overrides", {})
                self.volatility_gate = _cfg.get("volatility_gate", {"enabled": False})
        except Exception as e:
            logger.warning(f"Failed to load Phase 18 overrides or vol gate: {e}")

        # Initialize all engines ONCE (not per signal)
        self.engines = {
            "VWAP_BOUNCE":        IndexLiquidityTrapAdapter(),
            "MOMENTUM_BREAKOUT":  MomentumEngine(),
            "MEAN_REVERSION":     MeanReversionEngine(),
            "SWEEP_RETEST":       SweepRetestEngine(),
            "STRUCTURE_BOUNCE":   StructureStrategyEngine(),
            "CANDLESTICK":        CandlestickEngine(),
            "SMC_CORE":           SmartMoneyConceptsEngine(),
        }

        # Per-strategy funnel counters (Phase 13 instrumentation)
        from collections import defaultdict
        self.funnel = defaultdict(lambda: {
            "offered": 0,
            "engine_called": 0,
            "signal_generated": 0,
            "passed_threshold": 0,
            "won": 0,
        })

    def select_best_signal(self, df_5m, symbol: str, vix: float, df_1m=None, current_time=None,
                           mode: str = "NORMAL") -> Optional[Dict]:
        """
        Main entry point. Called from live trading loop.
        Returns single best signal dict or None.
        """
        # Normalize columns to lowercase to prevent KeyErrors in engines
        df_5m = df_5m.copy()
        df_5m.columns = [c.lower() for c in df_5m.columns]
        
        if df_1m is not None:
            df_1m = df_1m.copy()
            df_1m.columns = [c.lower() for c in df_1m.columns]

        # ── Step 1: Detect Context ────────────────────
        ctx = self.context_detector.detect(df_5m, vix, current_time, df_1m=df_1m)
        logger.debug(f"[{symbol}] Regime: {ctx.regime}")
        self.market_memory.update(symbol, df_5m, context=ctx)
        memory_signal = self.market_memory.ready_signal(symbol, df_5m)
        if self.market_memory.has_active_setups(symbol):
            logger.debug(f"[{symbol}] Market memory active setups: {len(self.market_memory.active_setups(symbol))}")

        # ── Step 2: Get Strategy Candidates ──────────
        candidates = self.strategy_mapper.get_candidates(ctx)
        candidates = self._augment_candidates_for_participation(candidates, ctx, mode)
        logger.debug(f"[{symbol}] Candidates: {[c.name for c in candidates] if candidates else 'None'}")
        if not candidates:
            if memory_signal:
                if self.market_memory.should_veto_for_manipulation(symbol, current_idx=len(df_5m) - 1):
                    logger.debug(
                        f"[{symbol}] MARKET_MEMORY vetoed: {self.market_memory.manipulation_reason(symbol)} "
                        f"weight={self.market_memory.manipulation_weight(symbol):.2f}"
                    )
                    return None
                
                score = self.confidence_scorer.score("MARKET_MEMORY", memory_signal, ctx, df_5m)
                if mode == "AGGRESSIVE":
                    threshold = CONFIDENCE_THRESHOLDS.get("aggressive_mode", 50)
                else:
                    threshold = CONFIDENCE_THRESHOLDS.get(f"{ctx.regime}_regime", CONFIDENCE_THRESHOLDS.get("default", 55))
                threshold = self.trade_tiers.threshold_for_mode(threshold, mode)
                
                if score < threshold:
                    logger.debug(f"[{symbol}] MARKET_MEMORY score {score} < threshold {threshold}")
                    return None

                return {
                    "symbol":          symbol,
                    "direction":       memory_signal.get("direction") or memory_signal.get("options_direction") or memory_signal.get("signal"),
                    "strategy":        "MARKET_MEMORY",
                    "confidence":      score,
                    "context":         ctx,
                    "entry_price":     memory_signal.get("entry_price") or memory_signal.get("spot_price"),
                    "sl":              memory_signal.get("sl"),
                    "tp":              memory_signal.get("tp"),
                    "risk_multiplier": self.strategy_mapper.get_risk_multiplier(ctx),
                    "context_tags":    self._build_tags(ctx, "MARKET_MEMORY"),
                    "raw_signal":      memory_signal,
                }
            logger.debug(f"[{symbol}] NO TRADE ZONE: {ctx.regime}")
            return None

        # ── Step 3: Generate signals from each engine
        scored_signals = []
        if memory_signal:
            self.funnel["MARKET_MEMORY"]["signal_generated"] += 1
            score = self.confidence_scorer.score("MARKET_MEMORY", memory_signal, ctx, df_5m)
            
            if mode == "AGGRESSIVE":
                threshold = CONFIDENCE_THRESHOLDS.get("aggressive_mode", 50)
            else:
                threshold = CONFIDENCE_THRESHOLDS.get(f"{ctx.regime}_regime", CONFIDENCE_THRESHOLDS.get("default", 55))
            threshold = self.trade_tiers.threshold_for_mode(threshold, mode)
            
            if score >= threshold:
                scored_signals.append({
                    "symbol":          symbol,
                    "direction":       memory_signal.get("direction") or memory_signal.get("options_direction") or memory_signal.get("signal"),
                    "strategy":        "MARKET_MEMORY",
                    "confidence":      score,
                    "context":         ctx,
                    "entry_price":     memory_signal.get("entry_price") or memory_signal.get("spot_price"),
                    "sl":              memory_signal.get("sl"),
                    "tp":              memory_signal.get("tp"),
                    "risk_multiplier": self.strategy_mapper.get_risk_multiplier(ctx),
                    "context_tags":    self._build_tags(ctx, "MARKET_MEMORY"),
                    "raw_signal":      memory_signal,
                })
                self.funnel["MARKET_MEMORY"]["passed_threshold"] += 1
            else:
                logger.debug(f"[{symbol}] MARKET_MEMORY score {score} < threshold {threshold}")
        for candidate in candidates:
            try:
                logger.info(f"[{symbol}] Offering candidate: {candidate.name}")
                self.funnel[candidate.name]["offered"] += 1
                engine = self.engines.get(candidate.name)
                if not engine:
                    continue

                # ── Phase 24d: Volatility Gate ──
                if self.volatility_gate.get("enabled", False) and candidate.name in self.volatility_gate.get("applies_to_strategies", []):
                    # We don't have VIX in the current test data frame easily accessible unless passed.
                    # Use fallback ATR
                    atr_col = next((c for c in ["tr_atr", "atr", "ATR"] if c in df_5m.columns), None)
                    close_col = next((c for c in ["close", "Close"] if c in df_5m.columns), None)
                    
                    if atr_col and close_col:
                        atr_val = df_5m[atr_col].iloc[-1]
                        close_val = df_5m[close_col].iloc[-1]
                        atr_pct = (atr_val / close_val) * 100.0
                        min_atr_pct = self.volatility_gate.get("fallback_atr_pct_of_price_min", 0.06)
                        
                        if atr_pct < min_atr_pct:
                            logger.debug(f"[VOL_GATE_VETO_ATR] {symbol} | {candidate.name} | ATR%={atr_pct:.3f} < {min_atr_pct}")
                            continue

                self.funnel[candidate.name]["engine_called"] += 1

                # Normalization check: ensure all engines use standard generate_signal(df, symbol)
                # We may need adapters if some engines have different signatures
                raw_signal = self._call_engine(
                    candidate.name, engine, df_5m, symbol, ctx, vix=vix, mode=mode, df_1m=df_1m
                )

                if not raw_signal or not (raw_signal.get('signal') or raw_signal.get('direction') or raw_signal.get('options_direction')):
                    continue
                self.funnel[candidate.name]["signal_generated"] += 1

                # ── Step 4: Score each signal ─────────
                score = self.confidence_scorer.score(
                    candidate.name, raw_signal, ctx, df_5m
                )

                # Determine threshold
                # Priority: aggressive > per-strategy min_confidence > regime > default
                if mode == "AGGRESSIVE":
                    threshold = CONFIDENCE_THRESHOLDS["aggressive_mode"]
                elif candidate.min_confidence and candidate.min_confidence > 20:
                    threshold = candidate.min_confidence
                else:
                    threshold = CONFIDENCE_THRESHOLDS.get(
                        f"{ctx.regime}_regime",
                        CONFIDENCE_THRESHOLDS["default"]
                    )
                threshold = self.trade_tiers.threshold_for_mode(threshold, mode)

                logger.debug(f"[SCORE] {symbol} | {candidate.name} | {score:.0f}% | threshold: {threshold}")

                if score < threshold:
                    logger.debug(f"[SIGNAL DEBUG] {symbol} | {candidate.name} | Score: {score} | Threshold: {threshold}")
                    logger.debug(f"[{symbol}] {candidate.name} "
                                 f"score {score} < threshold {threshold}")
                    continue
                self.funnel[candidate.name]["passed_threshold"] += 1

                # ── Step 5: Apply risk multiplier ─────
                risk_mult = (self.strategy_mapper.get_risk_multiplier(ctx)
                             * candidate.risk_multiplier)

                scored_signals.append({
                    "symbol":          symbol,
                    "direction":       raw_signal.get("direction") or raw_signal.get("options_direction") or raw_signal.get("signal"),
                    "strategy":        candidate.name,
                    "confidence":      score,
                    "context":         ctx,
                    "entry_price":     raw_signal.get("entry_price") or raw_signal.get("spot_price"),
                    "sl":              raw_signal.get("sl"),
                    "tp":              raw_signal.get("tp"),
                    "risk_multiplier": risk_mult,
                    "context_tags":    self._build_tags(ctx, candidate.name),
                    "raw_signal":      raw_signal,
                })

            except Exception as e:
                logger.warning(f"[{symbol}] Engine {candidate.name} error: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue

        if not scored_signals:
            return None

        scored_signals = self._apply_narrative_hierarchy(scored_signals, mode=mode)
        scored_signals = self._apply_trade_tiers(scored_signals, ctx, mode, symbol, current_idx=len(df_5m) - 1)
        if not scored_signals:
            return None

        if self.market_memory.should_veto_for_manipulation(symbol, current_idx=len(df_5m) - 1):
            logger.debug(
                f"[{symbol}] Trade vetoed: {self.market_memory.manipulation_reason(symbol)} "
                f"weight={self.market_memory.manipulation_weight(symbol):.2f}"
            )
            return None

        # ── Step 6: Return highest confidence signal ──
        best = max(scored_signals, key=lambda x: x["confidence"])
        self.funnel[best["strategy"]]["won"] += 1

        # ── Phase 18: Per-strategy ATR exit overrides ──
        # Only strategies defined in risk_execution.yaml exits.strategy_overrides are overridden.
        # VWAP_BOUNCE, MEAN_REVERSION, SWEEP_RETEST typically keep their
        # existing sl/tp logic unchanged (hybrid approach).
        if best.get("strategy") in self.phase18_overrides:
            _prof = self.phase18_overrides[best["strategy"]]
            try:
                _atr_col = next((c for c in ["atr", "ATR"] if c in df_5m.columns), None)
                if _atr_col:
                    _atr = float(df_5m[_atr_col].iloc[-1])
                else:
                    _h = next(c for c in ["high", "High"] if c in df_5m.columns)
                    _l = next(c for c in ["low",  "Low"]  if c in df_5m.columns)
                    _atr = float((df_5m[_h] - df_5m[_l]).rolling(14).mean().iloc[-1])
                if _atr and _atr > 0:
                    _cl    = next(c for c in ["close", "Close"] if c in df_5m.columns)
                    _entry = best.get("entry_price") or float(df_5m[_cl].iloc[-1])
                    _long  = str(best.get("direction", "")).upper() in ("CE", "BUY", "LONG")
                    best["sl"] = round(_entry - _prof["sl_atr"] * _atr, 2) if _long \
                                 else round(_entry + _prof["sl_atr"] * _atr, 2)
                    best["tp"] = round(_entry + _prof["tp_atr"] * _atr, 2) if _long \
                                 else round(_entry - _prof["tp_atr"] * _atr, 2)
            except Exception as _exc:
                logger.debug(f"[Phase18] exit override skipped for "
                             f"{best.get('strategy')}: {_exc}")

        return best

    def _call_engine(self, name, engine, df_5m, symbol, ctx, vix=15.0, mode="NORMAL", df_1m=None):
        """Universal engine caller — handles different
        method signatures across engines."""
        try:
            # 1. Try generate_signal (standard for most engines)
            if hasattr(engine, 'generate_signal') and name not in ["SMC_CORE", "CANDLESTICK"]:
                engine_config = self._engine_config(name, ctx, mode)
                raw = engine.generate_signal(df_5m, symbol, config=engine_config)
                if name == "MEAN_REVERSION" and raw is not None and not isinstance(raw, dict):
                    direction_raw = getattr(raw, 'direction', '') or getattr(raw, 'signal_type', '') or ''
                    direction_str = str(direction_raw).upper()
                    is_long  = direction_str in ('LONG', 'BUY', 'CE', 'BULLISH', 'UP', 'OVERSOLD')
                    is_short = direction_str in ('SHORT', 'SELL', 'PE', 'BEARISH', 'DOWN', 'OVERBOUGHT')
                    if not is_long and not is_short:
                        logger.debug(f"[MEAN_REVERSION] unknown direction: {direction_raw!r}")
                        return None
                    conf_raw = getattr(raw, 'confidence', 0) or 0
                    conf_pct = conf_raw * 100 if conf_raw <= 1.0 else conf_raw
                    return {
                        'signal':            'BUY' if is_long else 'SELL',
                        'direction':         'CE' if is_long else 'PE',
                        'options_direction': 'CE' if is_long else 'PE',
                        'entry_price':       getattr(raw, 'entry_price', None) or df_5m['close'].iloc[-1],
                        'spot_price':        getattr(raw, 'entry_price', None) or df_5m['close'].iloc[-1],
                        'sl':                getattr(raw, 'sl_price', None),
                        'tp':                getattr(raw, 'target_price', None),
                        'confidence':        conf_pct,
                        'setup_type':        getattr(raw, 'signal_type', 'MEAN_REVERSION'),
                    }
                return raw
            
            # 2. IndexLiquidityTrapAdapter
            elif hasattr(engine, 'evaluate_signal'):
                return engine.evaluate_signal(
                    df_5m, symbol,
                    vix_value=vix,
                    pcr_value=1.0,
                    oi_data={},
                    is_expiry_day=False
                )
            
            # 3. CandlestickEngine uses scan()
            elif hasattr(engine, 'scan'):
                cfg = getattr(self, 'config', {}).get('patterns', {}) if hasattr(self, 'config') else {}
                try:
                    res = engine.scan(df_5m, symbol, config=cfg)
                except TypeError:
                    try:
                        res = engine.scan(df_5m, symbol)
                    except Exception as e:
                        logger.debug(f"[CANDLESTICK] scan() failed: {e}")
                        return None
                except Exception as e:
                    logger.debug(f"[CANDLESTICK] scan() with config failed: {e}")
                    return None

                if not res:
                    return None

                # If res is a list, take the first one
                if isinstance(res, list):
                    if not res: return None
                    res = res[0]

                # If res is already a dict, return as-is (defensive)
                if isinstance(res, dict):
                    return res

                # Else convert CandlestickSignal object to dict — defensively
                direction_raw = getattr(res, 'direction', '') or ''
                direction_str = str(direction_raw).upper()
                is_long = direction_str in ('LONG', 'BUY', 'CE', 'BULLISH', 'UP')
                is_short = direction_str in ('SHORT', 'SELL', 'PE', 'BEARISH', 'DOWN')
                if not is_long and not is_short:
                    logger.debug(f"[CANDLESTICK] unknown direction: {direction_raw!r}")
                    return None

                conf_raw = getattr(res, 'confidence', 0)
                # Handle both 0-1 floats and 0-100 ints
                if 0 <= conf_raw <= 1.0:
                    conf_pct = conf_raw * 100
                else:
                    conf_pct = conf_raw

                return {
                    'signal':            'BUY' if is_long else 'SELL',
                    'direction':         'CE' if is_long else 'PE',
                    'options_direction': 'CE' if is_long else 'PE',
                    'spot_price':        getattr(res, 'entry_price', None) or df_5m['close'].iloc[-1],
                    'entry_price':       getattr(res, 'entry_price', None) or df_5m['close'].iloc[-1],
                    'sl':                getattr(res, 'sl_price', None) or getattr(res, 'sl', None),
                    'tp':                getattr(res, 'target_price', None) or getattr(res, 'tp', None),
                    'confidence':        conf_pct,
                    'setup_type':        getattr(res, 'pattern_name', 'CANDLESTICK'),
                }
            
            # 4. SMC uses update()
            elif hasattr(engine, 'update'):
                # SMC needs 7 positional args. We synthesize what we have:
                import pandas as pd
                ohlcv_5m = df_5m

                # Use provided df_1m if available, otherwise fallback to proxy
                if df_1m is not None:
                    ohlcv_1m = df_1m
                else:
                    # 1m proxy via forward-fill resample (best-effort, may be coarse)
                    try:
                        ohlcv_1m = df_5m.resample('1min').ffill().dropna()
                    except Exception:
                        ohlcv_1m = df_5m  # fall back to 5m if resample fails

                # Prior session OHLC
                latest_date = df_5m.index[-1].date()
                prior_session = df_5m[df_5m.index.date < latest_date]
                if len(prior_session) > 0:
                    prior_session_ohlc = {
                        'open':  prior_session['open'].iloc[0],
                        'high':  prior_session['high'].max(),
                        'low':   prior_session['low'].min(),
                        'close': prior_session['close'].iloc[-1],
                    }
                else:
                    prior_session_ohlc = {
                        'open':  df_5m['open'].iloc[0],
                        'high':  df_5m['high'].iloc[:3].max(),
                        'low':   df_5m['low'].iloc[:3].min(),
                        'close': df_5m['close'].iloc[0],
                    }

                # Pre-open range: first 3 bars (15 min) of current session
                today_session = df_5m[df_5m.index.date == latest_date]
                if len(today_session) >= 3:
                    preopen_range = {
                        'high': today_session['high'].iloc[:3].max(),
                        'low':  today_session['low'].iloc[:3].min(),
                    }
                else:
                    preopen_range = {
                        'high': df_5m['high'].iloc[-3:].max(),
                        'low':  df_5m['low'].iloc[-3:].min(),
                    }

                # ATR
                h = df_5m['high']; l = df_5m['low']; cl = df_5m['close'].shift(1)
                tr = pd.concat([h-l, (h-cl).abs(), (l-cl).abs()], axis=1).max(axis=1)
                atr_5m = float(tr.rolling(14).mean().iloc[-1]) if len(tr) >= 14 else 0.0
                atr_1m = atr_5m / 5.0  # approximation

                try:
                    res = engine.update(
                        symbol,
                        ohlcv_5m, ohlcv_1m,
                        prior_session_ohlc, preopen_range,
                        atr_5m, atr_1m
                    )
                    if hasattr(engine, 'extract_memory_events'):
                        memory_events = engine.extract_memory_events(res)
                    else:
                        memory_events = self.market_memory.events_from_smc_state(res)

                    if memory_events:
                        logger.info(f"[{symbol}] Extracted {len(memory_events)} memory events from SMC.")
                        self.market_memory.ingest_events(
                            symbol,
                            memory_events,
                            current_idx=len(df_5m) - 1,
                            timestamp=df_5m.index[-1] if hasattr(df_5m, 'index') else None,
                        )
                    else:
                        logger.debug(f"[{symbol}] No memory events found in SMC state.")

                except Exception as e:
                    logger.debug(f"[SMC_CORE] update() failed: {e}")
                    return None

                # SMC Core drives narrative memory. Direct trade signals from SMC 
                # require `engine.score_signal`, which needs a candidate entry.
                # For now, it functions strictly as a memory feeder.
                return None

                return None
            
        except Exception as e:
            logger.warning(f"[ENGINE ERROR] {name}: {e}")
            return None

    def _build_tags(self, ctx, strategy_name: str) -> list:
        return [
            ctx.regime,
            ctx.volatility,
            ctx.structure,
            ctx.time_zone,
            f"VIX_{ctx.vix_state}",
            strategy_name,
        ]

    def _augment_candidates_for_participation(self, candidates: List[StrategyCandidate], ctx, mode: str) -> List[StrategyCandidate]:
        mode_key = str(mode or "NORMAL").upper()
        if mode_key not in ("BALANCED", "PARTICIPATION"):
            return candidates

        augmented = list(candidates)
        names = {c.name for c in augmented}
        if ctx.regime == "TRENDING_UP" and "MOMENTUM_BREAKOUT" not in names:
            augmented.append(
                StrategyCandidate(
                    "MOMENTUM_BREAKOUT",
                    priority=4,
                    min_confidence=56 if mode_key == "BALANCED" else 50,
                    risk_multiplier=0.45 if mode_key == "BALANCED" else 0.25,
                    rationale="Participation trend-continuation breakout",
                )
            )
        return sorted(augmented, key=lambda c: c.priority)

    def _engine_config(self, name: str, ctx, mode: str) -> Optional[Dict]:
        mode_key = str(mode or "NORMAL").upper()
        if name != "MOMENTUM_BREAKOUT" or mode_key not in ("BALANCED", "PARTICIPATION"):
            return None

        cfg = {
            "participation_mode": True,
            "volume_breakout_ratio": 1.15 if mode_key == "BALANCED" else 1.10,
            "body_impulse_ratio": 1.10 if mode_key == "BALANCED" else 1.05,
            "use_slope_confirmation": True,
            "target_r": 1.35 if mode_key == "BALANCED" else 1.20,
        }
        if getattr(ctx, "regime", "") in ("TRENDING_UP", "TRENDING_DOWN"):
            cfg["range_atr_threshold"] = 6.0
            cfg["consolidation_bars"] = 4
        return cfg

    def _apply_narrative_hierarchy(self, scored_signals: List[Dict], mode: str = "NORMAL") -> List[Dict]:
        resolved = []
        mode_key = str(mode or "NORMAL").upper()
        for signal in scored_signals:
            narratives = self._extract_timeframe_narratives(signal)
            if not narratives:
                resolved.append(signal)
                continue

            decision = self.narrative_hierarchy.resolve(
                narratives,
                trade_direction=signal.get("direction"),
                base_confidence=signal.get("confidence"),
            )
            signal["narrative_hierarchy"] = decision
            raw_signal = signal.get("raw_signal")
            if isinstance(raw_signal, dict):
                raw_signal["narrative_hierarchy"] = decision

            if not decision.get("trade_allowed", True):
                soft_conflict_allowed = (
                    mode_key in ("BALANCED", "PARTICIPATION")
                    and "manipulation" not in str(decision.get("reason", "")).lower()
                )
                if soft_conflict_allowed:
                    decision["trade_allowed"] = True
                    decision["softened_by_mode"] = mode_key
                    signal["narrative_hierarchy"] = decision
                    if isinstance(raw_signal, dict):
                        raw_signal["narrative_hierarchy"] = decision
                else:
                    logger.debug(
                        "[HIERARCHY_VETO] %s | %s | %s",
                        signal.get("symbol"),
                        signal.get("strategy"),
                        decision.get("reason"),
                    )
                    continue

            adjusted = decision.get("adjusted_confidence")
            if adjusted is not None:
                signal["confidence"] = adjusted

            resolved.append(signal)
        return resolved

    def _apply_trade_tiers(
        self,
        scored_signals: List[Dict],
        ctx,
        mode: str,
        symbol: str,
        current_idx: int,
    ) -> List[Dict]:
        tiered = []
        mode_key = str(mode or "NORMAL").upper()
        if mode_key not in ("BALANCED", "PARTICIPATION", "AGGRESSIVE"):
            for signal in scored_signals:
                legacy_tier = {
                    "tier": "A",
                    "label": "LEGACY_STRICT",
                    "risk_multiplier": 1.0,
                    "min_confidence": 0.0,
                    "reason": "normal mode preserves legacy sizing and filtering",
                }
                signal["trade_tier"] = legacy_tier
                raw_signal = signal.get("raw_signal")
                if isinstance(raw_signal, dict):
                    raw_signal["trade_tier"] = legacy_tier
            return scored_signals

        manipulation_weight = self.market_memory.manipulation_weight(symbol)
        for signal in scored_signals:
            tier = self.trade_tiers.classify(
                signal,
                ctx=ctx,
                mode=mode,
                hierarchy_decision=signal.get("narrative_hierarchy"),
                manipulation_weight=manipulation_weight,
            )
            signal["trade_tier"] = tier.as_dict()
            raw_signal = signal.get("raw_signal")
            if isinstance(raw_signal, dict):
                raw_signal["trade_tier"] = tier.as_dict()

            if tier.tier == "REJECT":
                logger.debug(
                    "[TIER_REJECT] %s | %s | %s",
                    signal.get("symbol"),
                    signal.get("strategy"),
                    tier.reason,
                )
                continue

            signal["risk_multiplier"] = signal.get("risk_multiplier", 1.0) * tier.risk_multiplier
            tiered.append(signal)
        return tiered

    def _extract_timeframe_narratives(self, signal: Dict) -> Optional[Dict]:
        for key in ("timeframe_narratives", "narratives", "mtf_narrative", "mtf_narratives"):
            value = signal.get(key)
            if isinstance(value, dict):
                return value

        raw_signal = signal.get("raw_signal")
        if isinstance(raw_signal, dict):
            for key in ("timeframe_narratives", "narratives", "mtf_narrative", "mtf_narratives"):
                value = raw_signal.get(key)
                if isinstance(value, dict):
                    return value

        return None

    def funnel_report(self) -> str:
        """Phase 13: human-readable funnel breakdown."""
        lines = [
            "",
            "=== STRATEGY FUNNEL REPORT ===",
            f"{'Strategy':<20} {'Offered':>8} {'Called':>7} {'Generated':>10} {'Passed':>7} {'Won':>5}",
            "-" * 65,
        ]
        for name in sorted(self.funnel.keys()):
            f = self.funnel[name]
            lines.append(
                f"{name:<20} {f['offered']:>8} {f['engine_called']:>7} "
                f"{f['signal_generated']:>10} {f['passed_threshold']:>7} {f['won']:>5}"
            )
        return "\n".join(lines)

    def reset_funnel(self):
        """Reset counters between backtest runs."""
        for k in self.funnel:
            for kk in self.funnel[k]:
                self.funnel[k][kk] = 0
