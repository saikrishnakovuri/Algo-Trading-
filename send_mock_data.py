
import asyncio
import websockets
import json
import time

async def send_mock_candle():
    uri = "ws://localhost:8001/ws/live"
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to broadcaster")
            candle = {
                "type": "candle",
                "symbol": "NIFTY",
                "timeframe": "5m",
                "open": 22500,
                "high": 22550,
                "low": 22480,
                "close": 22520,
                "volume": 5000,
                "timestamp": int(time.time())
            }
            print(f"Sending mock candle: {candle}")
            await ws.send(json.dumps(candle))
            print("Sent.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(send_mock_candle())
