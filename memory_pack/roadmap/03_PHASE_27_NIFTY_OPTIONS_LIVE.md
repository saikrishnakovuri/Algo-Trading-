# 03 — Phase 27: Real NIFTY Options Integration
## 🎯 Objectives
Move away from synthetic price modeling to real-time NIFTY option chain data.

## 📋 Requirements (User Items)
- **Item 12**: Option chain fetcher for current and next expiry.
- **Item 15**: IV (Implied Volatility) calculation per strike.
- **Item 22**: Dynamic strike selection based on ATM/OTM delta.

## 🧪 Tests
1. **Data Accuracy**: Compare local option prices against NSE India website (allow 1 tick diff).
2. **Execution Logic**: Verify strike selection updates correctly as NIFTY Spot moves.

## 🏁 Acceptance Gate
- [ ] Real-time option chain updates < 100ms lag.
- [ ] Successful paper trade executed using real option contracts.
- **Gate Result**: [PASS/FAIL]
