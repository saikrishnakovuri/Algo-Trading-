from datetime import datetime

def format_trade_message(event_type, data):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if event_type == "ENTRY":
        return f"""
🟢 *TRADE ENTRY*

*Symbol:* {data.get("symbol")}
*Direction:* {data.get("direction")}
*Price:* {data.get("price")}
*Size:* {data.get("size")}
*Score:* {data.get("score")}
*Regime:* {data.get("regime")}
*RR:* {data.get("rr")}
*Time:* {ts}
"""

    elif event_type == "EXIT":
        return f"""
🔴 *TRADE EXIT*

*Symbol:* {data.get("symbol")}
*PnL:* {data.get("pnl")} ({data.get("pnl_pct")}%)
*Duration:* {data.get("duration")}
*Time:* {ts}
"""

    elif event_type == "SIGNAL":
        return f"""
⚠️ *SIGNAL GENERATED*

*Symbol:* {data.get("symbol")}
*Direction:* {data.get("direction")}
*Score:* {data.get("score")}
*Regime:* {data.get("regime")}
*Timeframe:* {data.get("timeframe")}
*Time:* {ts}
"""

    return f"ℹ️ *System Message*: {data.get('message', 'Unknown event')}"
