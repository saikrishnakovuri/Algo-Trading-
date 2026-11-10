# Bug Remediation Log

| Bug ID | Status | File | Description | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| B001 | Done | modules/broker_layer.py | Missing `timedelta` import | Add import |
| B002 | Done | modules/options/trade_executor.py | EMA20 SL defaulting to 8 | Pass `ema20` to trade manager |
| B003 | Done | modules/context_detector.py | VWAP not resetting daily | Update logic to reset daily |
| B004 | Done | modules/strategy_mapper.py | Dead/vetoed strategy code | Enable blocked regimes |
| B005 | Done | utils/jsonl_tailer.py | Inefficient memory usage | Implement proper streaming |
| B006 | Done | server.py | Missing/Redundant dependencies | Cleanup and unify imports |
| B007 | Done | modules/options/broker_adapter.py | Token lookup failure | Sync expiry format with ScripMaster |
| B008 | Done | live_options_trader.py | Race condition on `active_trades` | Add threading lock |
| B009 | Done | live_options_trader.py | Exit monitoring thread lacks error handling | Add try-except block |
| B011 | Done | modules/options/risk_manager.py | Outdated lot sizes (Nifty 65, BN 30) | Confirmed values per user |
| B013 | Done | main_backtest.py | Logic Inconsistency: Spot vs Options | Sync backtest with option premium logic |
| B017 | Done | modules/options/strike_selector.py | Brittle expiry shift on Wednesdays | Correct Nifty vs BN expiry logic |
| B021 | Done | modules/options/broker_adapter.py | Hardcoded Thursday expiries | Dynamic expiry retrieval |
| B029 | Done | modules/websocket_manager.py | Infinite recursion in reconnect | Replace recursion with iterative retry |
| B032 | Done | modules/option_chain.py | Hardcoded symbols & resource leaks | Implement session closing |
| B033 | Done | modules/options/trade_executor.py | Spot distance applied to premium | Adjust SL/TP logic using Delta |
| B034 | Done | modules/options/broker_adapter.py | O(N) REST calls for option chain | Optimize chain fetch |
| B035 | Done | modules/websocket_manager.py | Missing NFO subscription | Add NFO to exchangeType list |
| B036 | Done | modules/options/risk_manager.py | Lack of thread safety | Add locks to risk managers |
| B037 | Done | modules/options/trade_executor.py | Ignores Selector SL/TP | Map signal SL/TP directly |
| B038 | Done | modules/data_adapters/base_adapter.py | Missing legacy DataReader methods | Add compat methods to DataAdapter |
| B039 | Done | live_options_trader.py | Exit Monitoring Key Mismatch | Prioritize tradingsymbol over token |
| B040 | Done | AlgoTradingTelegramBotAndFrontend/backend/server.py | Dashboard Bridge Timeouts | Add pass-through endpoints |
| B041 | Done | modules/websocket_manager.py | WebSocket Subscription Mixup | Separate NSE and NFO tokens |
| B042 | Done | modules/options/trade_executor.py | Partial booking misses broker order | Add place_order call for partial exit |
| B043 | Done | modules/data_adapters/angelone_adapter.py | Incorrect broker method calls | Map arguments correctly to broker API |
| B044 | Done | live_options_trader.py | Double broker login | Use shared broker instance |
| B045 | Done | modules/price_action_engine.py | Unprotected dictionary/iloc access | Add None/empty DataFrame guards |
| B046 | Done | AlgoTradingTelegramBotAndFrontend/backend/server.py | Duplicate route and unsafe payload | Remove duplicate and add error guards |

