
import sys; sys.path.insert(0,'.')

# Check 1: Confidence threshold
try:
    from modules.confidence_scorer import CONFIDENCE_THRESHOLDS
    t = CONFIDENCE_THRESHOLDS['default']
    print(f'Threshold: {t} | Expected: 52 | Status: {"OK" if t == 52 else "WRONG - fix now"}')
except Exception as e:
    print(f'Confidence threshold check failed: {e}')

# Check 2: NO_TRADE_CONDITIONS
try:
    from modules.strategy_mapper import NO_TRADE_CONDITIONS
    print(f'NO_TRADE blocks: {len(NO_TRADE_CONDITIONS)} | Expected: 5 | Status: {"OK" if len(NO_TRADE_CONDITIONS) >= 5 else "WRONG - restore now"}')
except Exception as e:
    print(f'NO_TRADE_CONDITIONS check failed: {e}')

# Check 3: Context detector override
try:
    import inspect
    from modules.context_detector import ContextDetector
    src = inspect.getsource(ContextDetector.detect)
    has_override = 'TRENDING_UP' in src and 'CHOPPY' in src and 'EMERGENCY OVERRIDE' in src
    print(f'CHOPPY override: {"STILL PRESENT - remove" if has_override else "REMOVED - OK"}')
except Exception as e:
    print(f'Context detector check failed: {e}')
