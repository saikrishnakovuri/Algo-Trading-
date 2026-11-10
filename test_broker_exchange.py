from modules.broker_layer import AngelOneBroker

def test_exchange_resolution():
    broker = AngelOneBroker()
    
    # Test cases
    test_symbols = {
        "NIFTY": "NSE",
        "BANKNIFTY": "NSE",
        "NIFTY26MAY2622500CE": "NFO",
        "BANKNIFTY26MAY2650000PE": "NFO"
    }
    
    for symbol, expected in test_symbols.items():
        actual = broker._get_exchange(symbol)
        print(f"Symbol: {symbol} | Expected: {expected} | Actual: {actual}")
        assert actual == expected, f"Failed for {symbol}"

if __name__ == "__main__":
    test_exchange_resolution()
    print("Exchange Resolution Test Passed!")
