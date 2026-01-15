
import asyncio
import json
import logging
from datetime import datetime

# Set up logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GatewayDebugger")

try:
    import websockets
except ImportError:
    logger.error("websockets module not found. Please pip install websockets")
    exit(1)

async def test_gateway_handshake():
    uri = "ws://127.0.0.1:8010/lumina/gateway/ws"
    logger.info(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket Connected!")
            
            # Wait for meaningful messages (System Status)
            # It should come immediately
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                logger.info(f"📩 First Message Received: {message}")
                
                data = json.loads(message)
                if data.get("type") == "system_status":
                    sid = data.get("session_id") # Top level
                    if sid is None: 
                        # Check payload
                        sid = data.get("payload", {}).get("session_id")
                        
                    logger.info(f"🔑 Session ID extracted: {sid}")
                    if sid is not None and int(sid) >= 0:
                        logger.info("PASS: Valid Session ID received.")
                    else:
                        logger.error("FAIL: Session ID invalid or missing.")
                        
                    # Now try sending a chat message to see loopback
                    logger.info("📤 Sending Test Input...")
                    test_input = {
                        "trace_id": "debug-123",
                        "session_id": sid or 0,
                        "type": "input_text",
                        "source": "debugger",
                        "payload": {"text": "你好，这是调试消息"}
                    }
                    await websocket.send(json.dumps(test_input))
                    
                    # Listen for response
                    while True:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        logger.info(f"📩 Received: {msg}")
                        pd = json.loads(msg)
                        if pd.get("type") == "brain_response":
                            logger.info("✅ Brain Responded!")
                            break

                else:
                    logger.warning(f"Unexpected first message type: {data.get('type')}")
                    
            except asyncio.TimeoutError:
                logger.error("❌ Timeout waiting for System Status or Response.")
                
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gateway_handshake())
