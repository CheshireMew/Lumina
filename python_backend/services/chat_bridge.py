import logging
import asyncio
from core.protocol import EventType, EventPacket
from core.events.bus import get_event_bus
from services.chat.instance import chat_pipeline

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
            
            # [Smart Context] If history is empty (Fresh Session), disable RAG 
            # to prevent "leaking" immediate previous conversation via database logs.
            # Only enable RAG once we have established a new context.
            enable_rag_for_turn = len(messages) > 1 

            try:
                token_count = 0
                async for token in chat_pipeline.run(
                    messages,
                    user_id=user_id,
                    character_id=char_id,
                    stream=True,
                    model=model,
                    enable_rag=enable_rag_for_turn
                ):
                    token_count += 1
                    final_response += token
                    logger.info(f"[Token #{token_count}]: {token!r}")  # Debug stutter
                    await self.bus.emit(EventType.BRAIN_RESPONSE, EventPacket(
                        session_id=session_id,
                        type=EventType.BRAIN_RESPONSE,
                        source="core.chat_bridge",
                        payload={"content": token}
                    ))
                
                await self.bus.emit(EventType.BRAIN_RESPONSE_END, EventPacket(
                    session_id=session_id,
                    type=EventType.BRAIN_RESPONSE_END,
                    source="core.chat_bridge",
                    payload={}
                ))
                
                # History is now auto-saved by ChatPipeline
                # if session_manager:
                #     session_manager.add_turn(user_id, char_id, text, final_response)

                # 4. Log to Memory (Conversation Log)
                try:
                    memory_service = getattr(services, 'memory', None)
                    if memory_service:
                        u_label = packet.payload.get("user_name", user_id)
                        narrative = f"{u_label}: {text}\n{char_id}: {final_response}"
                        await memory_service.log_conversation(char_id, narrative)
                        logger.info("✅ Conversation logged to Memory")
                except Exception as log_e:
                    logger.error(f"Failed to log conversation: {log_e}")

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
