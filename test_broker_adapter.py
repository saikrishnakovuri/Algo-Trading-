import logging
from modules.broker_layer import AngelOneBroker
from modules.options.broker_adapter import OptionsBrokerAdapter

logging.basicConfig(level=logging.INFO)

def test_broker_adapter():
    from modules.options.scrip_master import scrip_master
    scrip_master.initialize('scrip_master.json')
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed, test aborted.")
        return

    adapter = OptionsBrokerAdapter(broker)
    
    # Test LTP
    nifty_ltp = adapter.get_ltp("NIFTY")
    print(f"NIFTY Spot: {nifty_ltp}")
    
    # Test Chain
    print("Fetching Chain...")
    df = adapter.get_full_option_chain("NIFTY")
    print(df.head())
    
    # Verify we got something
    assert not df.empty, "Option chain is empty"
    
    # Find an ATM row to check LTP
    atm_strike = int(round(nifty_ltp / 50) * 50)
    atm_row = df[(df['strike'] == atm_strike) & (df['type'] == 'CE')]
    if not atm_row.empty:
        assert atm_row.iloc[0]['ltp'] > 0, "LTP for ATM strike is 0, fetch failed"
        print(f"ATM Strike ({atm_strike} CE) LTP: {atm_row.iloc[0]['ltp']}")
    else:
        print(f"Warning: ATM Strike {atm_strike} CE not found in chain.")
        
    print("Broker Adapter Test Passed!")

if __name__ == "__main__":
    test_broker_adapter()
