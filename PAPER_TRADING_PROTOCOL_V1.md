# 📝 PAPER TRADING PROTOCOL V1

## 1. Morning Routine (09:00 - 09:15)
1. Verify internet connectivity.
2. Start the Backend: `cd AlgoTradingTelegramBotAndFrontend/backend && python server.py`
3. Start the Frontend: `cd AlgoTradingTelegramBotAndFrontend/frontend && npm start`
4. Check Dashboard for "Market Status: PRE-OPEN".
5. Verify VIX is within range (12-25).

## 2. Session Monitoring (09:15 - 15:30)
1. Keep the "Live P&L" tab open.
2. Monitor Telegram for trade alerts.
3. Do NOT modify configs unless VIX jumps > 20%.

## 3. Evening Routine (15:30 - 16:00)
1. Export trade history to CSV.
2. Review any SL hits.
3. Stop the bot: `python stop_trader.py`
