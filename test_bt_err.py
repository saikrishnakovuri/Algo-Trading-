import traceback
from backtest_engine import BacktestEngine

engine = BacktestEngine(initial_capital=1000000)
try:
    # Disable the print inside backtest engine to get pure traceback
    import builtins
    original_print = builtins.print
    def mock_print(*args, **kwargs):
        if "Error processing" in str(args):
            raise Exception("Captured internal error")
        # original_print(*args, **kwargs)
    builtins.print = mock_print
    
    engine.run_massive_backtest_v2(["data/universe_10d/VAL30IETF.csv"], step_size=10)
except Exception as e:
    import sys
    traceback.print_exc(file=sys.stderr)
