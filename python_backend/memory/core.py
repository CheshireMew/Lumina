import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.interfaces.driver import BaseMemoryDriver
from memory.store import MemoryItemStore
from services.companion.context import CompanionContext

logger = logging.getLogger("memory.core")


class MemoryService:
    """Single business boundary for conversation turns and long-term memories."""

    def __init__(self, driver: BaseMemoryDriver):
        if driver is None:
            raise ValueError("MemoryService requires an explicit memory driver.")

        self._driver = driver
        self.memory_items = MemoryItemStore(self._driver)
        self.encoder = None

    def set_encoder(self, encoder_fn):
        self.encoder = encoder_fn

    @property
    def driver(self):
        """Current memory driver, exposed read-only for diagnostics and raw queries."""
        return self._driver

    @property
    def driver_id(self) -> str:
        return getattr(self._driver, "id", "memory")

    def is_driver_active(self, driver_id: str) -> bool:
        return self.driver_id == driver_id

    async def replace_driver(self, driver, *, close_existing: bool = True):
        current = self._driver
        if current is driver:
            return

        if close_existing and current:
            await current.close()

        self._driver = driver
        self.memory_items.replace_driver(driver)

    async def connect(self):
        if self._driver:
            await self._driver.connect()

    async def close(self):
        if self._driver:
            await self._driver.close()

    @property
    def db(self):
        if not self._driver:
            return None
        return getattr(self._driver, "_db", None) or getattr(self._driver, "_pool", None)

    def _character_id(self, context: CompanionContext) -> str:
        if not isinstance(context, CompanionContext):
            raise ValueError("MemoryService requires CompanionContext")

        character_id = str(context.character_id or "").strip()
        if not character_id:
            raise ValueError("CompanionContext.character_id must be configured")
        return character_id.lower()

    def _parse_query_result(self, result: Any) -> List[Dict]:
        if not result:
            return []

        rows = result
        if isinstance(result, dict):
            rows = result.get("result") or result.get("data") or [result]

        parsed = []
        for row in rows:
            if isinstance(row, dict):
                parsed.append(dict(row))
            elif hasattr(row, "items"):
                parsed.append(dict(row.items()))
            else:
                try:
                    parsed.append(dict(row))
                except (TypeError, ValueError):
                    logger.warning("Skipping unparseable memory row: %r", row)
        return parsed

    async def record_turn(
        self,
        context: CompanionContext,
        *,
        user_message: str,
        assistant_message: str,
        user_name: Optional[str] = None,
        companion_name: Optional[str] = None,
    ) -> str:
        """Append one raw interaction event. This is not long-term memory."""
        label = user_name or context.user_id
        companion_label = companion_name or context.character_id
        narrative = (
            f"{label}: {user_message or '(Silence)'}\n"
            f"{companion_label}: {assistant_message}"
        )
        data = {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "character_id": self._character_id(context),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "narrative": narrative,
            "created_at": datetime.now(timezone.utc),
            "metadata": {},
        }

        if self.encoder:
            try:
                vec = self.encoder(narrative)
                if hasattr(vec, "tolist"):
                    vec = vec.tolist()
                data["embedding"] = vec
            except Exception as exc:
                logger.warning("Failed to embed conversation turn: %s", exc)

        try:
            turn_id = await self.driver.create("conversation_turns", data)
            return str(turn_id)
        except Exception as exc:
            logger.error("Error recording conversation turn: %s", exc)
            raise

    async def create_memory_item(
        self,
        context: CompanionContext,
        *,
        content: str,
        scope: str = "relationship",
        memory_type: str = "episode",
        subject_id: Optional[str] = None,
        summary: Optional[str] = None,
        source_turn_ids: Optional[list[str]] = None,
        confidence: float = 1.0,
        importance: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> str:
        embedding = None
        if self.encoder:
            vec = self.encoder(content)
            embedding = vec.tolist() if hasattr(vec, "tolist") else vec

        return await self.memory_items.create_memory_item(
            character_id=self._character_id(context),
            content=content,
            embedding=embedding,
            scope=scope,
            memory_type=memory_type,
            subject_id=subject_id or context.user_id,
            summary=summary,
            source_turn_ids=source_turn_ids,
            confidence=confidence,
            importance=importance,
            metadata=metadata,
        )

    async def search_memory_items(
        self,
        query_vector: list[float],
        context: CompanionContext,
        *,
        limit: int = 10,
        memory_types: Optional[list[str]] = None,
    ) -> List[Dict]:
        return await self.memory_items.search_vector(
            query_vector=query_vector,
            character_id=self._character_id(context),
            limit=limit,
            memory_types=memory_types,
        )

    async def _search_memory_items_fulltext(
        self,
        *,
        query: str,
        context: CompanionContext,
        limit: int = 10,
        memory_types: Optional[list[str]] = None,
    ) -> List[Dict]:
        return await self.memory_items.search_fulltext(
            query=query,
            character_id=self._character_id(context),
            limit=limit,
            memory_types=memory_types,
        )

    async def search_memory_items_hybrid(
        self,
        *,
        query: str,
        query_vector: list[float],
        context: CompanionContext,
        limit: int = 10,
        memory_types: Optional[list[str]] = None,
    ) -> List[Dict]:
        return await self.memory_items.search_hybrid(
            query=query,
            query_vector=query_vector,
            character_id=self._character_id(context),
            limit=limit,
            memory_types=memory_types,
        )

    async def get_stats(self, context: CompanionContext) -> Dict:
        character_id = self._character_id(context)
        memory_sql = "SELECT count(*) as count FROM memory_items WHERE character_id = $cid;"
        turn_sql = "SELECT count(*) as count FROM conversation_turns WHERE character_id = $cid;"
        params = {"cid": character_id}

        memory_result, turn_result = await asyncio.gather(
            self.driver.query(memory_sql, params),
            self.driver.query(turn_sql, params),
        )

        def get_count(res):
            if res and isinstance(res, list) and len(res) > 0:
                if hasattr(res[0], "get"):
                    return res[0].get("count", 0)
                if isinstance(res[0], dict):
                    return res[0].get("count", 0)
            return 0

        return {"memories": get_count(memory_result), "turns": get_count(turn_result)}

    async def get_unprocessed_turns(
        self,
        context: CompanionContext,
        limit: int = 20,
    ) -> List[Dict]:
        sql = """
            SELECT *
            FROM conversation_turns
            WHERE processed_at IS NULL AND character_id = $cid
            ORDER BY created_at ASC
            LIMIT $limit;
        """
        res = await self.driver.query(
            sql,
            {"cid": self._character_id(context), "limit": limit},
        )
        return self._parse_query_result(res)[:limit]

    async def mark_turns_processed(self, turn_ids: List[str]):
        if not turn_ids:
            return

        await self.driver.query(
            """
            UPDATE conversation_turns
            SET processed_at = NOW()
            WHERE id = ANY($ids::uuid[])
            """,
            {"ids": turn_ids},
        )
        logger.debug("Marked %s conversation turns as processed", len(turn_ids))

    async def get_all_turns(self, context: CompanionContext) -> List[Dict]:
        sql = """
            SELECT *
            FROM conversation_turns
            WHERE character_id = $cid
            ORDER BY created_at DESC
            LIMIT 1000;
        """
        res = await self.driver.query(sql, {"cid": self._character_id(context)})
        return self._parse_query_result(res)

    async def get_recent_turns(self, context: CompanionContext, limit: int = 20) -> List[Dict]:
        sql = """
            SELECT *
            FROM conversation_turns
            WHERE character_id = $cid
            ORDER BY created_at DESC
            LIMIT $limit;
        """
        res = await self.driver.query(
            sql,
            {"cid": self._character_id(context), "limit": limit},
        )
        return self._parse_query_result(res)[:limit]

    async def get_inspiration(self, context: CompanionContext, limit: int = 3) -> List[Dict]:
        sql = """
            SELECT *
            FROM memory_items
            WHERE character_id = $cid AND status = 'active'
            ORDER BY random()
            LIMIT $limit;
        """
        res = await self.driver.query(
            sql,
            {"cid": self._character_id(context), "limit": limit},
        )
        return self._parse_query_result(res)[:limit]

    async def retrieve_context(self, query: str, context: CompanionContext, limit: int = 3) -> str:
        """Retrieve long-term facts for the model without prescribing behavior."""
        vector = None
        if self.encoder:
            try:
                from services.embedding_cache import get_embedding_cache

                cache = get_embedding_cache()
                cached = cache.get(query, model_name="memory_encoder")
                if cached is not None:
                    vector = cached
                else:
                    def _encode():
                        vec = self.encoder(query)
                        if hasattr(vec, "tolist"):
                            vec = vec.tolist()
                        return vec

                    vector = await asyncio.to_thread(_encode)
                    cache.put(query, vector, model_name="memory_encoder")
            except Exception as exc:
                logger.warning("Failed to generate memory query embedding: %s", exc)

        if vector:
            results = await self.search_memory_items_hybrid(
                query=query,
                query_vector=vector,
                context=context,
                limit=limit,
            )
        else:
            logger.warning("Retrieving memory context without vector")
            results = await self._search_memory_items_fulltext(
                query=query,
                context=context,
                limit=limit,
                memory_types=None,
            )

        return "\n".join(
            item.get("content") or item.get("summary") or ""
            for item in results
            if item.get("content") or item.get("summary")
        )
