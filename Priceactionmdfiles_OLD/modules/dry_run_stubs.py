import logging

class AngelOneBrokerStub:
    def __init__(self):
        self.api_key = "MOCK_API_KEY"
        self.client_id = "MOCK_CLIENT_ID"
        self.password = "MOCK_PASS"
        self.totp_token = "JBSWY3DPEBLW64TMMQQQ===="
        self.feed_token = "MOCK_FEED"
        self.auth_token = "MOCK_AUTH"

    def login(self):
        return True

    def get_historical_data(self, symbol, token, interval, days=1, from_date_str=None, to_date_str=None):
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        idx = pd.date_range(end=datetime.now(), periods=100, freq='1min')
        df = pd.DataFrame({
            'Open': np.random.uniform(100, 200, 100),
            'High': np.random.uniform(100, 200, 100),
            'Low': np.random.uniform(100, 200, 100),
            'Close': np.random.uniform(100, 200, 100),
            'Volume': np.random.randint(1000, 5000, 100)
        }, index=idx)
        return df

    def logout(self):
        return True
