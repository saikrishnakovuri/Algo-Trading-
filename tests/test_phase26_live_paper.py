import asyncio
import json

import live_paper_controller as lpc
from live_paper_controller import LivePaperController
from modules.options.risk_manager import OptionsRiskManager
from modules.portfolio_manager import PortfolioManager


def test_phase26_options_risk_uses_one_percent_and_five_lot_cap():
    risk = OptionsRiskManager(total_capital=500000.0)

    assert risk.get_position_size("NIFTY", premium=100.0, sl_points=10.0) == 325
    assert risk.get_position_size("RELIANCE", premium=1000.0, sl_points=20.0) == 75


def test_phase26_portfolio_trips_two_percent_breaker_on_unrealized_loss():
    portfolio = PortfolioManager(initial_capital=500000.0)
    positions = [
        {
            "symbol": "RELIANCE",
            "qty": 75,
            "side": "LONG",
            "entry_price": 1000.0,
        }
    ]

    snapshot = portfolio.update_unrealized_pnl(positions, {"RELIANCE": 866.0})

    assert snapshot["daily_pnl"] == -10050.0
    assert snapshot["circuit_breaker_tripped"] is True
    assert portfolio.can_enter_trade(100.0) is False


def test_phase26_async_portfolio_mtm_path():
    async def run_check():
        portfolio = PortfolioManager(initial_capital=100000.0)
        snapshot = await portfolio.async_update_unrealized_pnl(
            [{"symbol": "NIFTY", "qty": 65, "side": "LONG", "entry_price": 100.0}],
            {"NIFTY": 60.0},
        )
        return snapshot

    snapshot = asyncio.get_event_loop().run_until_complete(run_check())
    assert snapshot["circuit_breaker_tripped"] is True


def test_phase26b_latest_equity_auto_resume(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports" / "live_paper"
    report_dir.mkdir(parents=True)
    summary = report_dir / "summary_20260517.json"
    summary.write_text(json.dumps({"portfolio": {"total_equity": 512345.67}}), encoding="utf-8")
    monkeypatch.setattr(lpc, "REPORT_DIR", report_dir)

    assert LivePaperController._get_latest_equity(500000.0) == 512345.67


def test_phase26b_open_position_recovery(tmp_path, monkeypatch):
    trade_file = tmp_path / "live_paper_trades.json"
    memory_file = tmp_path / "market_memory_state.json"
    trade_file.write_text(json.dumps([
        {
            "trade_id": "RELIANCE_1",
            "symbol": "RELIANCE",
            "token": "MOCK_RELIANCE",
            "side": "LONG",
            "qty": 75,
            "entry_price": 1000.0,
            "sl": 990.0,
            "tp": 1020.0,
            "opened_at": "2026-05-17T09:30:00",
            "strategy": "MARKET_MEMORY",
            "risk_amount": 750.0,
            "status": "OPEN",
        },
        {
            "trade_id": "INFY_1",
            "symbol": "INFY",
            "token": "MOCK_INFY",
            "side": "LONG",
            "qty": 75,
            "entry_price": 1500.0,
            "sl": 1490.0,
            "tp": 1520.0,
            "opened_at": "2026-05-17T10:00:00",
            "strategy": "MARKET_MEMORY",
            "risk_amount": 750.0,
            "status": "OPEN",
        },
        {
            "trade_id": "INFY_1",
            "symbol": "INFY",
            "status": "CLOSED",
        },
    ]), encoding="utf-8")
    monkeypatch.setattr(lpc, "TRADE_FILE", trade_file)
    monkeypatch.setattr(lpc, "MEMORY_STATE_FILE", memory_file)

    controller = LivePaperController(500000.0, ["RELIANCE", "INFY"], {})

    assert list(controller.positions) == ["RELIANCE"]
    assert controller.positions["RELIANCE"].qty == 75
    assert controller.portfolio.active_risk == 750.0
