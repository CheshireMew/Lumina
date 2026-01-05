import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8765/ws/stt"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WS")
            while True:
                msg = await websocket.recv()
                print(f"Received: {msg}")
    except Exception as e:
        print(f"WS Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Main Error: {e}")
