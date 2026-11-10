# NIFTY AI Trading System Requirements Checklist

## 1. Environment Requirements
- [ ] Python 3.9+ installed
- [ ] VS Code with Python extension
- [ ] API Key for Google Gemini (Google AI Studio)
- [ ] Broker API (Optional for Step 1, required for live execution)
- [ ] Internet Connection (High stability)

## 2. Dependencies
- [ ] `pandas`: Data handling
- [ ] `pandas-ta`: Technical indicators
- [ ] `google-generativeai`: AI Brain
- [ ] `yfinance`: Market data source (as proxy)
- [ ] `python-dotenv`: Environment variable management

## 3. Data Requirements
- [ ] NIFTY 50 Spot data (1m, 5m, 15m intervals)
- [ ] Option Chain data (OI, Volume, PCR) - *Step 2*
- [ ] Sentiment analysis sources (News/Twitter) - *Step 2*

## 4. Risk Management Rules
- [ ] Fixed Stop Loss / Target logic
- [ ] Daily Max Loss / Profit limits
- [ ] Minimum confidence threshold (65%)

## 5. Persistence
- [ ] SQLite database for trade logs and learning - *Step 4*
