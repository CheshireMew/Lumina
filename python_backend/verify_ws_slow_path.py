import asyncio
import websockets
import json

URI = "ws://127.0.0.1:8010/lumina/gateway/ws?client_id=verify_script"

async def test_slow_path():
    async with websockets.connect(URI) as websocket:
        print("Connected to Gateway")
        
        # 1. Send Task Request
        msg = {
            "type": "input_text",
            "payload": {
                "text": "Please search for the capital of France",
                "user_id": "tester_slow",
                "character_id": "hiyori"
            }
        }
        await websocket.send(json.dumps(msg))
        print(f"Sent: {msg['payload']['text']}")
        
        # 2. Listen for Response
        intent_detected = False
        start_received = False
        
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                evt_type = data.get("type")
                payload = data.get("payload", {})
                
                # Check for THINKING event (Task Mode)
                if evt_type == "brain_thinking":
                    mode = payload.get("mode")
                    print(f"Received THINKING: mode={mode}, details={payload.get('details')}")
                    if mode == "task":
                        intent_detected = True
                        print("鉁?Slow Path Triggered!")
                
                # Check for Response
                elif evt_type == "brain_response":
                    print(f"Received Token: {payload.get('content')}", end="", flush=True)

                elif evt_type == "brain_response_end":
                    print("\n[DONE]")
                    break
                    
            except Exception as e:
                print(f"Error: {e}")
                break
        
        if intent_detected:
            print("\nSUCCESS: Slow Path verified.")
        else:
            print("\nFAILURE: Did not detect Slow Path (Task Mode).")

if __name__ == "__main__":
    asyncio.run(test_slow_path())
