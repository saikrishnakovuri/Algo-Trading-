"""
Adapters that convert each strategy engine's output 
to the standard StrategyResult format.
"""
from modules.strategy_selector import StrategyResult
import pandas as pd


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures OHLCV columns are lowercase for engine compatibility."""
    if df is None: return None
    df_new = df.copy()
    df_new.columns = [c.lower() for c in df_new.columns]
    return df_new

def momentum_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for MomentumBreakoutEngine -> StrategyResult"""
    df = _normalize_df(df)
    raw = engine.generate_signal(df, symbol, config)
    
    if not raw or not raw.get('signal'):
        return None
    
    score = raw.get('score', 0)
    # Convert score (0-10) to confidence (0-100%)
    confidence = min(100, int(score * 12))
    
    return StrategyResult(
        strategy_name="MOMENTUM_BREAKOUT",
        signal=raw['signal'],
        direction=raw.get('direction', raw.get('type')),
        entry=raw.get('entry'),
        sl=raw.get('sl'),
        target1=raw.get('target1'),
        target2=raw.get('target2'),
        score=score,
        confidence_pct=confidence,
        setup_type=raw.get('setup_type', 'MOMENTUM_BREAKOUT'),
        reasons=raw.get('reasons', [])
    )

def ema_crossover_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for MomentumBreakoutEngine (EMA Crossover) -> StrategyResult"""
    df = _normalize_df(df)
    # Requires vwap for confirmation
    vwap = None
    if 'volume' in df.columns:
        typical_price = (df['high'] + df['low'] + df['close']) / 3.0
        vwap = (typical_price * df['volume']).cumsum().iloc[-1] / df['volume'].cumsum().iloc[-1]
    
    raw = engine.detect_ema_crossover(df, len(df)-1, vwap=vwap)
    
    if not raw or not raw.get('signal'):
        return None
    
    score = raw.get('score', 0)
    confidence = min(100, int(score * 10))
    
    entry = raw['entry']
    sl = raw['sl']
    dist = abs(entry - sl)
    target1 = entry + 1.5 * dist if raw['direction'] == 'CE' else entry - 1.5 * dist

    return StrategyResult(
        strategy_name="EMA_CROSSOVER",
        signal="BUY" if raw['signal'] == 'LONG' else "SELL",
        direction=raw['direction'],
        entry=entry,
        sl=sl,
        target1=target1,
        target2=None,
        score=score,
        confidence_pct=confidence,
        setup_type="EMA_CROSSOVER",
        reasons=[f"EMA 9/21 Cross", f"Price vs VWAP alignment"]
    )


def candlestick_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for CandlestickEngine -> StrategyResult"""
    df = _normalize_df(df)
    signal = engine.generate_signal(df, symbol, config)
    
    if signal is None:
        return None
    
    return StrategyResult(
        strategy_name="CANDLESTICK",
        signal="BUY" if signal.direction == "LONG" else "SELL",
        direction="CE" if signal.direction == "LONG" else "PE",
        entry=signal.entry_price,
        sl=signal.sl_price,
        target1=signal.target_price,
        target2=None,
        score=signal.score,
        confidence_pct=int(signal.confidence * 100),
        setup_type=signal.pattern_name,
        reasons=[f"Pattern: {signal.pattern_name}", f"RSI: {signal.context_details.get('rsi')}", f"VWAP: {signal.context_details.get('vwap_dist_pct')}%"]
    )


def mean_reversion_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for MeanReversionEngine -> StrategyResult"""
    df = _normalize_df(df)
    signal = engine.generate_signal(df, symbol, config)
    
    if signal is None:
        return None

    # Normalization Fix: Scale score to confidence consistently.
    confidence = min(100, int(signal.confidence * 100))

    return StrategyResult(
        strategy_name="MEAN_REVERSION",
        signal="BUY" if signal.direction == "LONG" else "SELL",
        direction="CE" if signal.direction == "LONG" else "PE",
        entry=signal.entry_price,
        sl=signal.sl_price,
        target1=signal.target_price,
        target2=None,
        score=signal.score,
        confidence_pct=confidence,
        setup_type=signal.signal_type,
        reasons=[f"Type: {signal.signal_type}", f"RSI: {signal.indicator_state.get('rsi')}", f"BB %B: {signal.indicator_state.get('bb_pct_b')}"]
    )


def sweep_retest_adapter(engine, df, symbol, df_1m=None, config=None, **kwargs):
    """Adapter for SweepRetestEngine -> StrategyResult"""
    df = _normalize_df(df)
    df_1m = _normalize_df(df_1m)
    raw = engine.generate_signal(df, symbol, df_1m=df_1m, config=config)
    
    if not raw or not raw.get('signal'):
        return None
    
    return StrategyResult(
        strategy_name="SWEEP_RETEST",
        signal=raw['signal'],
        direction=raw['direction'],
        entry=raw['entry'],
        sl=raw['sl'],
        target1=raw['target1'],
        target2=raw.get('target2'),
        score=raw['score'],
        confidence_pct=raw['confidence'],
        setup_type=raw['setup_type'],
        reasons=raw['reasons']
    )


def structure_strategy_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for StructureStrategyEngine -> StrategyResult"""
    df = _normalize_df(df)
    raw = engine.generate_signal(df, symbol, config=config)
    
    if not raw or not raw.get('signal'):
        return None
    
    return StrategyResult(
        strategy_name="STRUCTURE_BOUNCE",
        signal=raw['signal'],
        direction=raw['direction'],
        entry=raw['entry'],
        sl=raw['sl'],
        target1=raw['target1'],
        target2=raw.get('target2'),
        score=raw['score'],
        confidence_pct=raw['confidence'],
        setup_type=raw['setup_type'],
        reasons=raw['reasons']
    )

def vwap_bounce_adapter(engine, df, symbol, vix=15.0, pcr=1.0, oi_data={}, is_expiry=False, config=None, **kwargs):
    """Adapter for IndexLiquidityTrapAdapter (VWAP Bounce) -> StrategyResult"""
    df = _normalize_df(df)
    raw = engine.evaluate_signal(df, symbol, vix, pcr, oi_data, is_expiry)
    
    if not raw or raw['strategy'] != 'VWAP_BOUNCE':
        return None
    
    return StrategyResult(
        strategy_name="VWAP_BOUNCE",
        signal="BUY" if raw['options_direction'] == 'CE' else "SELL",
        direction=raw['options_direction'],
        entry=raw['spot_price'],
        sl=raw['spot_price'] * 0.995, # Placeholder, manager calculates real SL
        target1=raw['spot_price'] * 1.01,
        target2=None,
        score=raw['confidence'] / 10.0,
        confidence_pct=raw['confidence'],
        setup_type="VWAP_BOUNCE",
        reasons=[f"VWAP Bounce", f"Context: {raw.get('adaptive_exits', {}).get('context')}"]
    )

def liquidity_trap_adapter(engine, df, symbol, config=None, **kwargs):
    """Adapter for IndexLiquidityTrapAdapter (Liquidity Trap) -> StrategyResult"""
    # We need to call the new _detect_liquidity_trap method
    df = _normalize_df(df)
    raw = engine._detect_liquidity_trap(df, symbol)
    
    if not raw:
        return None
    
    return StrategyResult(
        strategy_name="LIQUIDITY_TRAP",
        signal="BUY" if raw['options_direction'] == 'CE' else "SELL",
        direction=raw['options_direction'],
        entry=raw['spot_price'],
        sl=raw['spot_price'] * 0.995,
        target1=raw['spot_price'] * 1.01,
        target2=None,
        score=raw['confidence'] / 10.0,
        confidence_pct=raw['confidence'],
        setup_type="LIQUIDITY_TRAP",
        reasons=[f"Fake breakout detected", f"Context: {raw.get('adaptive_exits', {}).get('context')}"]
    )

def smc_adapter(engine, df, symbol, df_1m=None, config=None, **kwargs):
    """Adapter for SmartMoneyConceptsEngine -> StrategyResult"""
    # This engine requires complex state update. 
    # For a simple 'generate_signal' style call, we'd need more inputs.
    # Placeholder for now as it's primarily used for background scoring.
    return None
