import cProfile
import pstats
import io
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def profile_backtest():
    from scripts.fast_backtest import main
    # Profile a 2-day run on 1 symbol to get a representative sample quickly
    # Use -s NIFTY to limit scope for profiling
    sys.argv = ['fast_backtest.py', '--days', '2', '--symbols', 'NIFTY']
    
    pr = cProfile.Profile()
    pr.enable()
    
    main()
    
    pr.disable()
    s = io.StringIO()
    sortby = 'cumulative'
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats(30) # Top 30 functions
    print(s.getvalue())

if __name__ == "__main__":
    profile_backtest()
