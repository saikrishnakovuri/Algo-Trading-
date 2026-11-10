from orchestrator import Orchestrator

# Runtime prompt provided by user
market_summary = """
Symbol: NIFTY 50
Current Price: 22450.00
RSI: 62
EMA 20: 22440.00
EMA 50: 22350.00
VWAP: 22420.00
Trend Direction: Uptrend

Price Action: Bullish Breakout
Support: 22350.00 | Resistance: 22500.00

Option Chain Summary:
PCR: 0.85
Max Pain: 22400
CE OI: High CE OI unwinding
PE OI: Strong buildup at 22300
"""

if __name__ == '__main__':
    orch = Orchestrator()
    decision = orch.run_cycle(mock_market_summary=market_summary, dry_run=True)
    print(decision)
