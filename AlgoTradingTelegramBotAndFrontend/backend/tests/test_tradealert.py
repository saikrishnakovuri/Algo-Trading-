"""Backend tests for TradeAlert Bot API - all endpoints"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestBotStatus:
    def test_bot_status_configured(self):
        r = requests.get(f"{BASE_URL}/api/bot/status")
        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is True
        assert data["bot_token_set"] is True
        assert data["chat_id_set"] is True


class TestAnalytics:
    def test_analytics_summary(self):
        r = requests.get(f"{BASE_URL}/api/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_trades" in data
        assert "win_rate" in data
        assert "total_pnl" in data

    def test_pnl_history(self):
        r = requests.get(f"{BASE_URL}/api/analytics/pnl-history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestTrades:
    def test_get_trades(self):
        r = requests.get(f"{BASE_URL}/api/trades")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_trades_count(self):
        r = requests.get(f"{BASE_URL}/api/trades/count")
        assert r.status_code == 200
        assert "total" in r.json()

    def test_notify_trade_creates_and_persists(self):
        payload = {
            "symbol": "ETHUSDT",
            "direction": "BUY",
            "event_type": "entry",
            "entry_price": 3200.00,
            "position_size": 1.0,
            "strategy_name": "TEST_Strategy",
            "confidence_score": 0.75,
            "market_regime": "trend",
        }
        r = requests.post(f"{BASE_URL}/api/trades/notify", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "ETHUSDT"
        assert "trade_id" in data
        assert "alert_sent" in data
        assert data["id"] != ""

        # Verify persistence
        r2 = requests.get(f"{BASE_URL}/api/trades?symbol=ETHUSDT&limit=10")
        assert r2.status_code == 200
        trades = r2.json()
        ids = [t["trade_id"] for t in trades]
        assert data["trade_id"] in ids

    def test_notify_trade_missing_required_fields(self):
        r = requests.post(f"{BASE_URL}/api/trades/notify", json={"symbol": "BTC"})
        assert r.status_code == 422

    def test_preview_message(self):
        payload = {
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "event_type": "entry",
            "entry_price": 67500.0,
            "position_size": 0.05,
            "strategy_name": "Momentum Alpha",
            "confidence_score": 0.85,
            "market_regime": "trend",
        }
        r = requests.post(f"{BASE_URL}/api/trades/preview", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "BTCUSDT" in data["message"]

    def test_trade_filters(self):
        r = requests.get(f"{BASE_URL}/api/trades?direction=BUY&limit=5")
        assert r.status_code == 200
        trades = r.json()
        for t in trades:
            assert t["direction"] == "BUY"


class TestAlerts:
    def test_get_alerts(self):
        r = requests.get(f"{BASE_URL}/api/alerts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_alert_log_structure(self):
        r = requests.get(f"{BASE_URL}/api/alerts?limit=1")
        assert r.status_code == 200
        alerts = r.json()
        if alerts:
            a = alerts[0]
            assert "id" in a
            assert "trade_id" in a
            assert "status" in a
            assert "message" in a


class TestTestAlert:
    def test_send_test_alert(self):
        r = requests.post(f"{BASE_URL}/api/trades/test")
        assert r.status_code == 200
        data = r.json()
        assert "success" in data
        # Note: may succeed or fail depending on Telegram rate limit
        print(f"Test alert result: {data}")
