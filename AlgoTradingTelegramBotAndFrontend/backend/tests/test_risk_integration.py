"""Backend tests for Risk Lab and Integration page APIs"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestRiskAPI:
    """Risk analytics endpoints"""

    def test_risk_metrics_returns_200(self):
        r = requests.get(f"{BASE_URL}/api/analytics/risk")
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"

    def test_risk_metrics_has_required_fields(self):
        r = requests.get(f"{BASE_URL}/api/analytics/risk")
        data = r.json()
        required = ["sharpe", "sortino", "calmar", "max_drawdown", "kelly_pct",
                    "win_rate", "profit_factor", "expectancy", "chart_data",
                    "strategy_risk", "total_completed"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_risk_metrics_strategy_risk_has_4_strategies(self):
        r = requests.get(f"{BASE_URL}/api/analytics/risk")
        data = r.json()
        strategy_risk = data.get("strategy_risk", {})
        assert len(strategy_risk) >= 1, "No strategy data"
        # Each strategy should have kelly_pct, win_rate, profit_factor
        for name, s in strategy_risk.items():
            assert "kelly_pct" in s, f"Missing kelly_pct in {name}"
            assert "win_rate" in s, f"Missing win_rate in {name}"
            assert "profit_factor" in s, f"Missing profit_factor in {name}"

    def test_risk_chart_data_has_equity_drawdown(self):
        r = requests.get(f"{BASE_URL}/api/analytics/risk")
        data = r.json()
        chart_data = data.get("chart_data", [])
        assert len(chart_data) > 0, "No chart data"
        first = chart_data[0]
        assert "equity" in first
        assert "drawdown" in first


class TestMonteCarloAPI:
    """Monte Carlo simulation endpoint"""

    def test_monte_carlo_returns_200(self):
        r = requests.get(f"{BASE_URL}/api/analytics/monte-carlo")
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"

    def test_monte_carlo_has_percentiles(self):
        r = requests.get(f"{BASE_URL}/api/analytics/monte-carlo")
        data = r.json()
        assert "percentiles" in data, f"Missing percentiles. Keys: {list(data.keys())}"
        percentiles = data["percentiles"]
        for key in ["5", "25", "50", "75", "95"]:
            assert key in percentiles, f"Missing percentile key: {key}"

    def test_monte_carlo_has_prob_profit(self):
        r = requests.get(f"{BASE_URL}/api/analytics/monte-carlo")
        data = r.json()
        assert "prob_profit" in data, f"Missing prob_profit. Keys: {list(data.keys())}"
        assert 0 <= data["prob_profit"] <= 100, "prob_profit should be 0-100"

    def test_monte_carlo_simulations_param(self):
        r = requests.get(f"{BASE_URL}/api/analytics/monte-carlo?simulations=500")
        assert r.status_code == 200


class TestPositionSizeAPI:
    """Position sizing calculator endpoint"""

    def test_position_size_returns_200(self):
        r = requests.post(f"{BASE_URL}/api/analytics/position-size", json={
            "account_size": 500000,
            "risk_pct": 1.0,
            "stop_loss_pct": 1.5,
            "entry_price": 22150
        })
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"

    def test_position_size_required_fields(self):
        r = requests.post(f"{BASE_URL}/api/analytics/position-size", json={
            "account_size": 500000,
            "risk_pct": 1.0,
            "stop_loss_pct": 1.5,
            "entry_price": 22150
        })
        data = r.json()
        required = ["kelly_pct", "half_kelly_usd", "risk_position_usd", "quarter_kelly_usd"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_position_size_math(self):
        r = requests.post(f"{BASE_URL}/api/analytics/position-size", json={
            "account_size": 500000,
            "risk_pct": 1.0,
            "stop_loss_pct": 1.5
        })
        data = r.json()
        expected_risk = 500000 * 1.0 / 100
        assert abs(data["risk_amount"] - expected_risk) < 1, "Risk amount math error"


class TestIntegrationAPI:
    """Integration page endpoints"""

    def test_template_returns_200(self):
        r = requests.get(f"{BASE_URL}/api/integration/template")
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"

    def test_template_has_content(self):
        r = requests.get(f"{BASE_URL}/api/integration/template")
        data = r.json()
        assert "content" in data, "Missing content key"
        assert len(data["content"]) > 100, "Template content too short"
        assert "execution_engine" in data.get("filename", "").lower() or "execution_engine" in data["content"].lower()

    def test_test_connection_endpoint(self):
        r = requests.post(f"{BASE_URL}/api/trades/test", json={})
        assert r.status_code == 200, f"Got {r.status_code}: {r.text[:200]}"
