"""
PA Engine Bridge — Connects Priceactionmdfiles/engine to modules/
=================================================================

This bridge imports the 48-strategy engine from Priceactionmdfiles
and exposes signals in the format the existing decision_engine expects.

DOES NOT CHANGE ANY EXISTING CODE. Only bridges the two systems.
"""

import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

# Find Priceactionmdfiles directory
# It is a sibling of the root modules folder or a subdirectory of project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PA_ENGINE_DIR = os.path.join(BASE_DIR, "Priceactionmdfiles")

if not os.path.exists(PA_ENGINE_DIR):
    # Fallback for different structures
    PA_ENGINE_DIR = BASE_DIR # Maybe we are already in Priceactionmdfiles

if PA_ENGINE_DIR not in sys.path:
    sys.path.insert(0, PA_ENGINE_DIR)

# Load production config
CONFIG_PATH = os.path.join(PA_ENGINE_DIR, "pipeline", "results", "FINAL_PRODUCTION_CONFIG.json")


class PAEngineBridge:
    """Bridge between Priceactionmdfiles engine and the live trader modules."""

    _engine = None
    _config = None
    _edge_monitor = None

    @classmethod
    def get_engine(cls):
        """Lazy-load the unified strategy engine."""
        if cls._engine is None:
            try:
                # Ensure PA_ENGINE_DIR is in path before import
                if PA_ENGINE_DIR not in sys.path:
                    sys.path.insert(0, PA_ENGINE_DIR)
                    
                from engine.unified_strategy_engine import UnifiedStrategyEngine
                cls._engine = UnifiedStrategyEngine()
                logger.info(f"PA Engine loaded from {PA_ENGINE_DIR}")
            except ImportError as e:
                logger.error(f"Failed to import PA engine: {e}. Path: {sys.path}")
                return None
        return cls._engine

    @classmethod
    def get_config(cls):
        """Load FINAL_PRODUCTION_CONFIG.json."""
        if cls._config is None:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    cls._config = json.load(f)
                logger.info(f"PA config loaded: {len(cls._config.get('strategies', []))} strategies")
            else:
                logger.warning(f"PA config not found at {CONFIG_PATH}")
                cls._config = {}
        return cls._config

    @classmethod
    def save_config(cls, config: dict):
        """Save updated config (from frontend edits)."""
        import shutil
        if os.path.exists(CONFIG_PATH):
            shutil.copy2(CONFIG_PATH, CONFIG_PATH + '.backup')
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, default=str)
        cls._config = config
        logger.info("PA config saved")

    @classmethod
    def get_signals(cls, df, timeframe='5m'):
        """
        Get signals from the 48-strategy PA engine.
        """
        engine = cls.get_engine()
        config = cls.get_config()

        if engine is None:
            return []

        try:
            raw_signals = engine.get_signals(df, backtest_mode=False)
            if not raw_signals:
                return []

            # Filter by production config
            active_strategies = set(config.get('strategies', []))

            filtered = []
            for sig in raw_signals:
                # Strategy filter
                if active_strategies and sig.strategy_name not in active_strategies:
                    continue

                # Confidence filter
                strat_cfg = config.get('strategy_configs', {}).get(sig.strategy_name, {})
                min_conf = strat_cfg.get('optimal_confidence', 0.70)
                if sig.confidence < min_conf:
                    continue

                # Convert to the format decision_engine expects
                # direction = 'BULLISH' if sig.signal_type.name in ['BUY', 'STRONG_BUY'] else 'BEARISH'
                # Use signal_type.value if it's an enum or check name
                type_name = sig.signal_type.name if hasattr(sig.signal_type, 'name') else str(sig.signal_type)
                direction = 'BULLISH' if 'BUY' in type_name.upper() else 'BEARISH'
                
                filtered.append({
                    'trade': 'CE' if direction == 'BULLISH' else 'PE',
                    'confidence': int(sig.confidence * 100),
                    'reasons': [f"PA Engine: {sig.strategy_name} - {sig.reasoning}"],
                    'entry': getattr(sig, 'entry_price', None) or df.iloc[-1]['close'],
                    'sl': getattr(sig, 'stop_loss', None),
                    'target1': getattr(sig, 'take_profit', None),
                    'target2': getattr(sig, 'take_profit', None),
                    'regime': getattr(sig, 'metadata', {}).get('regime', 'UNKNOWN'),
                    'source': 'pa_engine',
                    'strategy': sig.strategy_name,
                    'checklist_score': sig.confidence * 10
                })

            return filtered

        except Exception as e:
            logger.error(f"PA engine signal error: {e}")
            return []

    @classmethod
    def get_edge_status(cls):
        """Run edge monitor and return status."""
        try:
            from edge_monitor import EdgeMonitor

            # Find the most recent backtest CSV
            results_dir = os.path.join(PA_ENGINE_DIR, "pipeline", "results")
            if not os.path.exists(results_dir):
                return {"status": "NO_DATA", "is_alive": True}
                
            csv_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
            if not csv_files:
                return {"status": "NO_DATA", "is_alive": True}

            latest_csv = os.path.join(results_dir, sorted(csv_files)[-1])
            monitor = EdgeMonitor(trades_csv=latest_csv, capital=500000)

            return {
                "status": "GREEN" if monitor.is_edge_alive() else "RED",
                "is_alive": monitor.is_edge_alive(),
                "triggers": monitor.generate_stop_triggers(),
                "kelly": monitor.kelly_criterion(),
                "decay": monitor.rolling_edge_decay(),
                "streaks": monitor.consecutive_loss_analysis(),
            }
        except Exception as e:
            logger.error(f"Edge monitor error: {e}")
            return {"status": "ERROR", "error": str(e), "is_alive": True}

    @classmethod
    def get_monte_carlo(cls):
        """Read Monte Carlo results."""
        mc_path = os.path.join(PA_ENGINE_DIR, "pipeline", "results", "monte_carlo_results.json")
        if os.path.exists(mc_path):
            try:
                with open(mc_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return None

    @classmethod
    def get_backtest_results(cls):
        """List all backtest result files."""
        results_dir = os.path.join(PA_ENGINE_DIR, "pipeline", "results")
        files = []
        if os.path.exists(results_dir):
            for f in sorted(os.listdir(results_dir)):
                path = os.path.join(results_dir, f)
                files.append({
                    "name": f,
                    "type": f.split('.')[-1],
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                })
        return files
