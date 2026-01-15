"""
Unified Chat Processor
Consolidation of chat.py, free_llm.py, and CognitiveLoop logic.

Responsibilities:
- RAG Retrieval (Memory Search)
- Tool Execution (Web Search)
- Soul Context Rendering
- LLM Streaming
"""

import logging
import json

import logging
from typing import AsyncGenerator, List, Dict, Any
from services.chat.pipeline import ChatPipeline

logger = logging.getLogger("UnifiedChat")


class UnifiedChatProcessor:
    """
    Facade for Chat Processing.
    Delegates to ChatPipeline.
    """

    def __init__(self):
        self.pipeline = ChatPipeline()

    async def process(
        self,
        messages: List[Dict[str, Any]],
        user_id: str = "default_user",
        character_id: str = "default_char",
        enable_rag: bool = True,
        enable_tools: bool = True,
        model: str = None,
        temperature: float = 0.7,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Delegates to the Pipeline.
        """
        async for token in self.pipeline.run(
            messages,
            user_id=user_id,
            character_id=character_id,
            enable_rag=enable_rag,
            enable_tools=enable_tools,
            model=model,
            temperature=temperature,
            stream=stream
        ):
            yield token



# Singleton instance
unified_chat = UnifiedChatProcessor()
