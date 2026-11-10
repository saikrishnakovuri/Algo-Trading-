import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001/ws/live"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        await websocket.send(json.dumps({"test": "hello"}))
        response = await websocket.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
