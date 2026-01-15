
import asyncio
import json
import logging

try:
    import websockets
except ImportError:
    print("websockets module not found. Please install it (pip install websockets) or this test will fail.")
    exit(1)

async def test_gateway():
    uri = "ws://127.0.0.1:8010/lumina/gateway/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # 1. Wait for System Status
            init_msg = await websocket.recv()
            print(f"Received: {init_msg}")
            
            # 2. Send "Hello"
            payload = {
                "type": "input_text",
                "source": "test_script",
                "session_id": 0, # Should rely on current id, but let's try 0 for now
                "payload": {
                    "text": "你好，能听到我说话吗？"
                }
            }
            print(f"Sending: {json.dumps(payload, ensure_ascii=False)}")
            await websocket.send(json.dumps(payload))
            
            # 3. Listen for response
            print("Waiting for response (timeout 30s)...")
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    print(f"Received Packet: Type={data.get('type')}")
                    
                    if data.get('type') == 'brain_response':
                         print(f"\n✅ BRAIN RESPONSE: {data['payload'].get('text')}\n")
                         break
                except asyncio.TimeoutError:
                    print("Timeout waiting for LLM response.")
                    break
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gateway())
