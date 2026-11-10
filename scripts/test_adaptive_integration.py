import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from modules.options.signal_adapter import IndexLiquidityTrapAdapter
from modules.options.trade_executor import OptionTradeManager

def test_adaptive_integration():
    # 1. Setup Mock Data
    dates = pd.date_range(start="2026-05-03 09:15:00", periods=100, freq="5min")
    df = pd.DataFrame({
        'Open': np.linspace(1000, 1010, 100),
        'High': np.linspace(1005, 1015, 100),
        'Low': np.linspace(995, 1005, 100),
        'Close': np.linspace(1000, 1010, 100),
        'Volume': [1000] * 100
    }, index=dates)
    
    adapter = IndexLiquidityTrapAdapter()
    
    # 2. Test evaluate_signal
    # Note: evaluate_signal needs at least 50 bars
    print("Testing Signal Adapter Context Tagging...")
    sig = adapter.evaluate_signal(
        df, "NIFTY", vix_value=15.0, pcr_value=1.0, 
        oi_data={}, is_expiry_day=False
    )
    
    if sig:
        print(f"✅ Signal Generated: {sig['strategy']}")
        print(f"Context: {sig['adaptive_exits']['context']}")
        print(f"Adaptive SL: {sig['adaptive_exits']['sl_type']}")
        print(f"Adaptive TP: {sig['adaptive_exits']['tp_type']}")
        
        # 3. Test Trade Manager Integration
        class MockRisk:
            def get_position_size(self, *args): return 50
            daily_pnl = 0
            def record_trade(self, *args): pass

        class MockBroker:
            def place_order(self, *args, **kwargs): return "MOCK_ORDER_ID"

        manager = OptionTradeManager(broker=MockBroker(), risk_manager=MockRisk())
        
        opt_details = {
            'premium': 100.0, 'lot_size': 50, 'strike': 22500, 
            'option_type': 'CE', 'expiry': '2026-05-07'
        }
        
        print("\nTesting Trade Executor Adaptive Entry...")
        tid = manager.enter_trade(sig, opt_details, 100000.0, paper_mode=True)
        
        if tid:
            trade = manager.active_trades[tid]
            print(f"✅ Trade Executed: {tid}")
            print(f"Stored SL Type: {trade['sl_type']}")
            print(f"Stored TP Type: {trade['tp_type']}")
            
            # 4. Test Monitor Exits (ATR Trailing)
            if trade['tp_type'] == 'TP_TRAIL_ATR':
                print("\nTesting ATR Trailing Exit...")
                # Mock a price jump
                quotes = {tid: {'ltp': 150.0}}
                manager.monitor_exits(quotes)
                new_sl = manager.active_trades[tid]['sl_price']
                print(f"Initial SL: {trade['entry_price'] - trade['sl_dist']}")
                print(f"New Trailed SL: {new_sl}")
                if new_sl > (trade['entry_price'] - trade['sl_dist']):
                    print("✅ ATR Trailing Successful.")

if __name__ == "__main__":
    try:
        test_adaptive_integration()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
