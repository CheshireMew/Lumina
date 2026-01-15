from typing import Any, Dict, AsyncGenerator
import logging
import asyncio
from core.protocol import EventPacket, EventType
from ..state import CognitiveContext, InteractionPhase
from .classifier import IntentClassifier, IntentType
# Removed direct container import, use helper functions
from services.unified_chat import unified_chat

logger = logging.getLogger("CognitiveLoop")



class GatewayAdapter:
    @property
    def session_id(self):
        try:
            from routers.gateway import gateway_service
            return gateway_service._session_id
        except ImportError:
            return 0

    async def emit(self, packet):
        from core.events.bus import get_event_bus
        await get_event_bus().emit(packet.type, packet, source="cognitive_loop")

def _get_gateway():
    """Adapter to direct EventBus calls"""
    return GatewayAdapter()


def _get_llm_manager():
    """Get LLM manager from container"""
    from services.container import services
    return services.llm_manager


def _get_session_manager():
    """Get session manager from container"""
    from services.container import services
    return services.session_manager


def _get_vision():
    """Get vision service from container"""
    from services.container import services
    return services.vision


class CognitiveLoop:
    """
    The Brain's Logic Processing Unit.
    Phase 23 MVP: Direct Fast Path (Input -> LLM -> Output).
    Future: Parse -> Decide -> Act.
    """
    
    def __init__(self, context: CognitiveContext):
        self.context = context
        self.llm_service = _get_llm_manager()
        self.classifier = IntentClassifier()

    async def process_input(self, input_packet: EventPacket):
        """
        Main Entry Point for 'thinking'.
        """
        # 0. Load Session (Persistence)
        user_id = input_packet.payload.get("user_id", "default_user")
        char_id = input_packet.payload.get("character_id", "default_char")
        
        if _get_session_manager():
            # Merge persisted state (History) into Rich State
            loaded_state = _get_session_manager().load_session(user_id, char_id)
            
            # Only update history (and maybe session_id?)
            # We assume loaded_state is the 'basic' version from session_manager.py
            if hasattr(loaded_state, 'short_term_history'):
                 self.context.state.short_term_history = loaded_state.short_term_history
            
            # Note: Phase, Emotion, etc. are ephemeral or managed by CognitivePlugin, 
            # while SessionManager currently only knows basic history. 
            # In future, SessionManager should use the full SessionState schema or be plugin-aware.

        # Emit THINKING state
        await self._emit_state(InteractionPhase.THINKING, input_packet.session_id)
        
        user_text = input_packet.payload.get("text", "")
        # msg_user_name = input_packet.payload.get("user_name", "User") # Unused locally
        
        if not user_text:
            return

        # [MVP Decision] Skip Intent Classification for now.
        # Keep it simple: Always use Fast Path (Chat).
        # We can re-enable Agentic capabilities (Tasks/Vision) later via config.
        
        # 48-74 Removed for Minimal MVP to avoid "Coupling" intelligent features too early.

        
        # Else: Fast Path (Standard Chat Flow) -> Continue below



        # 2. Append User Input to Persistent History
        self.context.state.short_term_history.append({"role": "user", "content": user_text})
        
        # 3. Prepare Messages for Unified Processor
        # Extract recent history
        messages = [{"role": m["role"], "content": m["content"]} for m in self.context.state.short_term_history[-10:]]

        # 4. Stream via Unified Path
        await self._fast_path_stream(messages, input_packet.session_id, user_id, char_id)

        
    async def _fast_path_stream(self, messages: list, session_id: int, user_id: str, char_id: str):
        try:
            # Emit Start
            logger.info(f"馃 [Loop] Emitting BRAIN_THINKING (session={session_id})...")
            await _get_gateway().emit(EventPacket(
                session_id=session_id,
                type=EventType.BRAIN_THINKING,
                source="cognitive_loop",
                payload={"mode": "chat"}
            ))
            
            # Use Unified Processor (Handles RAG, Tools, Soul)
            model = self.llm_service.get_model_name("chat")
            logger.info(f"馃 [Loop] Starting Unified Chat Process (model={model})...")
            
            full_response = ""
            token_count = 0
            async for token in unified_chat.process(
                messages, 
                user_id=user_id, 
                character_id=char_id,
                model=model,
                stream=True
            ):
                token_count += 1
                if _get_gateway().session_id != session_id:
                     logger.info("Cognitive Loop Interrupted (Session Mismatch)")
                     return 

                if token:
                    full_response += token
                    await _get_gateway().emit(EventPacket(
                        session_id=session_id,
                        type=EventType.BRAIN_RESPONSE, 
                        source="cognitive_loop",
                        payload={"content": token}
                    ))
            
            logger.info(f"馃 [Loop] Finished Unified Chat. Tokens: {token_count}")
            
            # Emit End
            await _get_gateway().emit(EventPacket(
                session_id=session_id,
                type="brain_response_end", 
                source="cognitive_loop",
                payload={}
            ))
            
            # Update History & Persist (Same as Fast Path for now, but Slow Path usually has reasoning logs)
            self.context.state.short_term_history.append({"role": "assistant", "content": full_response})
            await self._emit_state(InteractionPhase.IDLE, session_id)
            
            if _get_session_manager():
                _get_session_manager().save_session(user_id, char_id, self.context.state)

        except Exception as e:
            logger.error(f"Cognitive Loop Error: {e}")
            await _get_gateway().emit(EventPacket(
                session_id=session_id,
                type=EventType.SYSTEM_STATUS,
                source="cognitive_loop", 
                payload={"error": str(e)}
            ))

    async def _slow_path_loop(self, user_text: str, session_id: int, user_id: str, char_id: str):
        """
        System 2: Reasoning & Tool Execution Loop.
        MVP: Emulate 'Thinking' and return a canned response.
        Future: ReAct Agent Loop.
        """
        logger.info(f"Entered Slow Path for: {user_text}")
        
        try:
            # 1. Emit START (Task Mode)
            await _get_gateway().emit(EventPacket(
                session_id=session_id,
                type=EventType.BRAIN_THINKING,
                source="cognitive_loop",
                payload={"mode": "task", "details": "Analyzing request..."}
            ))

            full_response = ""
            
            # Vision Check
            # Simple heuristic: if input contains "see" or "screen" or "look at", use Vision
            vision_keywords = ["see", "screen", "look at", "what is this", "screenshot"]
            if _get_vision() and any(k in user_text.lower() for k in vision_keywords):
                await _get_gateway().emit(EventPacket(
                    session_id=session_id,
                    type=EventType.BRAIN_THINKING,
                    source="cognitive_loop",
                    payload={"mode": "vision", "details": "Capturing screen..."}
                ))
                
                # Analyze Screen
                driver = await self.llm_service.get_driver("chat") # Assuming OpenAI Driver supports images
                vision_result = await _get_vision().analyze_screen(driver, prompt=user_text)
                full_response = vision_result
                
                # Emit results
                await _get_gateway().emit(EventPacket(
                     session_id=session_id, 
                     type=EventType.BRAIN_RESPONSE,
                     source="cognitive_loop",
                     payload={"content": full_response}
                 ))

            else:
                # Standard Slow Path (ReAct Placeholder)
                system_prompt = "You are an expert problem solver. Break down the user's request and provide a detailed solution."
                
                messages = [{"role": "system", "content": system_prompt}]
                messages.append({"role": "user", "content": user_text})
                
                # Emit "Executing" state
                await _get_gateway().emit(EventPacket(
                    session_id=session_id,
                    type=EventType.BRAIN_THINKING,
                    source="cognitive_loop",
                    payload={"mode": "task", "details": "Executing logic..."}
                ))
                
                # Stream Response
                driver = await self.llm_service.get_driver("chat") 
                model = self.llm_service.get_model_name("chat")
                
                async for token in driver.chat_completion(messages, model=model, stream=True):
                     if _get_gateway().session_id != session_id:
                          return
                     
                     full_response += token
                     await _get_gateway().emit(EventPacket(
                         session_id=session_id, 
                         type=EventType.BRAIN_RESPONSE,
                         source="cognitive_loop",
                         payload={"content": token}
                     ))
            
            await _get_gateway().emit(EventPacket(session_id=session_id, type="brain_response_end", source="cognitive_loop", payload={}))

            # 5. Persist
            if _get_session_manager():
                 self.context.state.short_term_history.append({"role": "user", "content": user_text})
                 self.context.state.short_term_history.append({"role": "assistant", "content": full_response})
                 _get_session_manager().save_session(user_id, char_id, self.context.state)

        except Exception as e:
            logger.error(f"Slow Path Error: {e}")
            await _get_gateway().emit(EventPacket(session_id=session_id, type=EventType.SYSTEM_STATUS, source="cognitive_loop", payload={"error": str(e)}))

    async def _emit_state(self, phase: InteractionPhase, session_id: int):
        """Helper to update state and emit event"""
        self.context.state.phase = phase
        await _get_gateway().emit(EventPacket(
            session_id=session_id,
            type=EventType.COGNITIVE_STATE,
            source="cognitive_loop",
            payload={"phase": phase.value}
        ))
