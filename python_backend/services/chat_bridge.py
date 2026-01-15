import logging
import asyncio
from core.protocol import EventType, EventPacket
from core.events.bus import get_event_bus
from services.unified_chat import unified_chat

logger = logging.getLogger("ChatBridge")

class BasicChatBridge:
    """
    Core Service that bridges EventBus 'input_text' to UnifiedChat (LLM).
    This replaces the complex CognitivePlugin for the MVP.
    """
    def __init__(self):
        self.bus = get_event_bus()
        self.subscribed = False

    def start(self):
        if not self.subscribed:
            self.bus.subscribe(EventType.INPUT_TEXT, self.handle_input_text)
            self.subscribed = True
            logger.info("✅ Basic Chat Bridge Started (Listening to input_text)")

    async def handle_input_text(self, event):
        # [Interruption Logic]
        # If a task is running, cancel it to allow new input to take over (user interrupt)
        if hasattr(self, "current_task") and self.current_task and not self.current_task.done():
            logger.info("🛑 Interrupting previous LLM task for new input...")
            self.current_task.cancel()
            
        # Spawn new task non-blocking so Gateway isn't frozen
        self.current_task = asyncio.create_task(self._process_chat(event))

    async def _process_chat(self, event):
        """Internal worker for chat processing"""
        try:
            print(f"DEBUG: ChatBridge Processing Event: {event.type}")
            logger.info(f"BRIDGE PROCESSING: {event.data}")
            packet = event.data
            if not isinstance(packet, EventPacket):
                if isinstance(packet, dict):
                    packet = EventPacket(**packet)
                else:
                    return

            # --- DEDUPLICATION GUARD ---
            # Detect double-submission from frontend or event bus echo
            current_time = asyncio.get_event_loop().time()
            text_content = packet.payload.get("text", "")
            
            # Simple signature: Text + SessionID
            req_sig = f"{packet.session_id}:{text_content}"
            
            if hasattr(self, "_last_req_sig") and self._last_req_sig == req_sig:
                # Check time delta
                if hasattr(self, "_last_req_time") and (current_time - self._last_req_time) < 2.0:
                    logger.warning(f"⚠️ Duplicate request detected (sig={req_sig}). Ignoring.")
                    return
            
            self._last_req_sig = req_sig
            self._last_req_time = current_time
            # ---------------------------

            session_id = packet.session_id
            text = packet.payload.get("text", "")
            
            if not text:
                return

            # 1. Emit Thinking
            await self.bus.emit(EventType.BRAIN_THINKING, EventPacket(
                session_id=session_id,
                type=EventType.BRAIN_THINKING,
                source="core.chat_bridge",
                payload={"mode": "chat", "text": text}
            ))

            # 2. Call LLM
            from services.container import services
            session_manager = getattr(services, 'session_manager', None)
            
            user_id = packet.payload.get("user_id", "default_user")
            char_id = packet.payload.get("character_id", "default_char")
            
            messages = []
            if session_manager:
                try:
                    state = session_manager.load_session(user_id, char_id)
                    if hasattr(state, "short_term_history"):
                        messages = [{"role": m["role"], "content": m["content"]} for m in state.short_term_history[-10:]]
                except Exception as e:
                    logger.error(f"Failed to load session: {e}")

            messages.append({"role": "user", "content": text})
            
            # Extract model from payload if present (dynamic model switching)
            model = packet.payload.get("model")
            
            # 3. Stream Response
            final_response = ""
            
            try:
                async for token in unified_chat.process(
                    messages,
                    user_id=user_id,
                    character_id=char_id,
                    stream=True,
                    model=model
                ):
                    final_response += token
                    await self.bus.emit(EventType.BRAIN_RESPONSE, EventPacket(
                        session_id=session_id,
                        type=EventType.BRAIN_RESPONSE,
                        source="core.chat_bridge",
                        payload={"content": token}
                    ))
                
                await self.bus.emit("brain_response_end", EventPacket(
                    session_id=session_id,
                    type="brain_response_end",
                    source="core.chat_bridge",
                    payload={}
                ))
                
                if session_manager:
                    session_manager.add_turn(user_id, char_id, text, final_response)

                # 4. Log to SurrealDB (Permanent Memory)
                try:
                    surreal = services.surreal_system
                    if surreal:
                        # Use user_name or user_id for label, and char_id for AI label
                        u_label = packet.payload.get("user_name", user_id)
                        narrative = f"{u_label}: {text}\n{char_id}: {final_response}"
                        await surreal.log_conversation(char_id, narrative)
                        logger.info("✅ Conversation logged to SurrealDB")
                except Exception as log_e:
                    logger.error(f"Failed to log to SurrealDB: {log_e}")

            except asyncio.CancelledError:
                logger.info("⚠️ Chat Task Cancelled by User Interrupt")
                # Optional: Emit a "silence" or "stop" event? 
                # Frontend usually handles interruption via VAD logic triggering new input
                raise # Propagate cancel
                
            except Exception as e:
                logger.error(f"Chat processing failed: {e}")
                await self.bus.emit(EventType.SYSTEM_STATUS, EventPacket(
                    session_id=session_id,
                    type=EventType.SYSTEM_STATUS,
                    source="core.chat_bridge",
                    payload={"error": str(e)}
                ))
                
        except asyncio.CancelledError:
            pass # Clean exit
        except Exception as outer_e:
            logger.error(f"Bridge Worker Error: {outer_e}")
