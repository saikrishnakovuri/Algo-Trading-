import asyncio
import websockets
import json
import time
import statistics

async def multi_client_test(client_id, results):
    uri = "ws://localhost:8001/ws/live"
    try:
        async with websockets.connect(uri) as ws:
            start_time = time.perf_counter()
            count = 0
            while count < 50: # Collect 50 messages
                data = await ws.recv()
                end_time = time.perf_counter()
                results.append(end_time - start_time)
                count += 1
            print(f"Client {client_id} finished")
    except Exception as e:
        print(f"Client {client_id} error: {e}")

async def run_benchmark():
    results = []
    # Test 3 clients simultaneously
    await asyncio.gather(
        multi_client_test(1, results),
        multi_client_test(2, results),
        multi_client_test(3, results)
    )
    print(f"Average latency: {statistics.mean(results):.4f}s")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
