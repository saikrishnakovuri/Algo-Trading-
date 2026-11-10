
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8000/ws/live-candles"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to ws://localhost:8000/ws/live-candles")
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    print(f"Received: {message}")
                except asyncio.TimeoutError:
                    print("No message received in 10 seconds (Heartbeat?)")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
