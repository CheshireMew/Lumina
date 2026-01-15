import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyVision")

async def test_vision_flow():
    uri = "ws://127.0.0.1:8010/lumina/gateway/ws?client_id=verify_vision"
    async with websockets.connect(uri) as websocket:
        logger.info("Connected to Gateway")
        
        # Authenticate / Handshake if needed (Gateway sends Connect first)
        msg1 = await websocket.recv()
        logger.info(f"Received: {msg1}") # Welcome/Status
        
        # Send Vision Request
        request = {
            "type": "input_text",
            "session_id": 0,
            "source": "frontend",
            "payload": {
                "text": "What do you see on my screen right now?",
                "character_id": "hiyori", # Default char
                "user_id": "tester"
            }
        }
        await websocket.send(json.dumps(request))
        logger.info("Sent: What do you see on my screen?")
        
        # Wait for Vision Thinking Event
        vision_triggered = False
        
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                data = json.loads(response)
                
                # Check for Thinking Event with mode="vision"
                if data.get("type") == "brain_thinking":
                    payload = data.get("payload", {})
                    mode = payload.get("mode")
                    details = payload.get("details")
                    logger.info(f"Received THINKING: mode={mode}, details={details}")
                    
                    if mode == "vision":
                        print("\n鉁?Vision Mode Triggered!")
                        vision_triggered = True
                        
                elif data.get("type") == "brain_response":
                    content = data.get("payload", {}).get("content", "")
                    print(content, end="", flush=True)
                    
                elif data.get("type") == "brain_response_end":
                    print("\n[Done]")
                    break
                    
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for response")
                break
        
        if not vision_triggered:
            print("\n鉂?Vision Mode NOT Triggered")
        else:
            print("\n鉁?SUCCESS: Vision Pipeline Verified")

if __name__ == "__main__":
    asyncio.run(test_vision_flow())
