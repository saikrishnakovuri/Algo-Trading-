import os
import sys
from datetime import datetime
import pandas as pd

# Add current directory to path
sys.path.append(os.getcwd())

from modules.intermarket.feeds.manager import IntermarketFeedManager
from modules.intermarket.engine import IntermarketRelativeStrengthEngine
from modules.intermarket.schemas import UniverseSnapshot

def main():
    print("="*50)
    print("🌐 INTERMARKET FEED WIRING TEST")
    print("="*50)
    
    # 1. Initialize
    feed_manager = IntermarketFeedManager()
    engine = IntermarketRelativeStrengthEngine()
    
    # 2. Refresh Feeds
    symbols = ["RELIANCE", "HDFCBANK", "INFY", "TCS", "SBIN"]
    feed_manager.refresh_all(symbols, current_date=datetime(2026, 4, 15))
    
    ctxs = feed_manager.get_latest_contexts()
    
    # 3. Perform a test evaluation
    # RELIANCE test
    print("\n🔍 Evaluating RELIANCE with real intermarket context...")
    
    # Create a mock 5m dataframe for RELIANCE
    # In reality, this would be the actual intraday 5m data
    mock_ohlcv = pd.DataFrame({
        'Open': [1350.0], 'High': [1360.0], 'Low': [1345.0], 'Close': [1355.0]
    })
    
    # Ensure universe_snapshot is not empty for breadth calc
    if ctxs['universe_snapshot'] is None:
        ctxs['universe_snapshot'] = UniverseSnapshot(timestamp=datetime.now(), symbol_snapshots={})
    
    # Wrap in try-except as indices might be empty if market is closed/fetching failed
    try:
        if ctxs['nifty_ctx'] is None:
            print("⚠️ Nifty Context failed to fetch. Intermarket will use defaults.")
            return
            
        verdict = engine.evaluate(
            symbol="RELIANCE",
            candidate_direction="LONG",
            setup_type="ZONE_REJECTION",
            active_window="OPENING_BURST",
            regime="TRENDING_LOW_VOL",
            smc_tier="ELITE",
            now_ist=datetime.now(),
            nifty_ctx=ctxs['nifty_ctx'],
            sector_indices={}, # Simplified for test
            stock_ohlcv_session=mock_ohlcv,
            universe_snapshot=ctxs['universe_snapshot'],
            cross_assets=ctxs['cross_assets'],
            global_ctx=ctxs['global_ctx'],
            banknifty_ctx=ctxs['banknifty_ctx']
        )
        
        print("\n" + "="*30)
        print("📊 INTERMARKET VERDICT")
        print("="*30)
        print(f"Allow Trade: {verdict.allow}")
        print(f"Final Delta: {verdict.final_delta:+.2f}")
        print(f"Raw Combined: {verdict.raw_combined_delta:+.2f}")
        print(f"Veto Reasons: {verdict.veto_reasons}")
        print(f"Reasoning: {verdict.reasoning}")
        print("\nSUB-VERDICTS:")
        for name, sub in verdict.sub_verdicts.items():
            delta = getattr(sub, 'score_delta', 0.0)
            print(f" - {name:12}: {delta:+.2f} | {sub.reasoning}")
            
        if abs(verdict.final_delta) > 0:
            print("\n✅ SUCCESS: Module 6 is generating non-zero deltas from live data.")
        else:
            print("\n⚠️ WARNING: Final delta is 0.0. Check if indices/vix returns are non-zero.")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
