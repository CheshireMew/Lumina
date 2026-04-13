import logging
from typing import Any, AsyncGenerator, Dict, Optional

import asyncpg
from pgvector.asyncpg import register_vector

from app_config import config
from core.db.query_builder import QueryBuilder
from core.interfaces.driver import BaseMemoryDriver

from .crud import create as crud_create
from .crud import delete as crud_delete
from .crud import mark_memories_hit as crud_mark_memories_hit
from .crud import query as crud_query
from .crud import update as crud_update
from .graph import get_neighbors as graph_get_neighbors
from .graph import relate as graph_relate
from .notifications import publish as notifications_publish
from .notifications import listen as notifications_listen
from .query_builder import PostgresQueryBuilder
from .schema import initialize_schema as initialize_postgres_schema
from .search import search_fulltext as search_fulltext_impl
from .search import search_hybrid as search_hybrid_impl
from .search import search_vector as search_vector_impl

logger = logging.getLogger("PostgresDriver")


class PostgresDriver(BaseMemoryDriver):
    def __init__(
        self,
        id: str = "driver.memory.postgres",
        name: str = "PostgreSQL Driver",
        description: str = "Industry Standard Database for Memory & Context",
    ):
        super().__init__(id, name, description)
        self._pool: Optional[asyncpg.Pool] = None
        self._config = config.memory
        self._initialized = False
        self._qb = PostgresQueryBuilder()

    def _require_pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        return self._pool

    def get_query_builder(self) -> QueryBuilder:
        return self._qb

    async def load(self):
        await self.connect()

    async def connect(self):
        if self._pool:
            return

        pg_config = self._config.postgres
        try:
            self._pool = await asyncpg.create_pool(
                user=pg_config.user,
                password=pg_config.password,
                database=pg_config.database,
                host=pg_config.host,
                port=pg_config.port,
                min_size=1,
                max_size=10,
                init=self._init_connection,
            )
            await initialize_postgres_schema(self._pool)
            self._initialized = True
            logger.info("Connected to PostgreSQL at %s:%s", pg_config.host, pg_config.port)
        except Exception as exc:
            logger.error("PostgreSQL connection failed: %s", exc)
            raise

    async def _init_connection(self, conn):
        await register_vector(conn)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def initialize_schema(self):
        await initialize_postgres_schema(self._require_pool())

    async def create(self, table: str, data: Dict[str, Any]) -> str:
        return await crud_create(self._require_pool(), table, data)

    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        return await crud_update(self._require_pool(), table, id, data)

    async def delete(self, table: str, id: str) -> bool:
        return await crud_delete(self._require_pool(), table, id)

    async def query(self, sql: str, params: Optional[Dict] = None) -> Any:
        return await crud_query(self._require_pool(), sql, params)

    async def mark_memories_hit(self, memory_ids: list):
        return await crud_mark_memories_hit(self._require_pool(), memory_ids)

    async def search_vector(
        self,
        table: str,
        vector: list,
        limit: int,
        threshold: float,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        return await search_vector_impl(
            self._require_pool(), table, vector, limit, threshold, filter_criteria
        )

    async def search_fulltext(
        self,
        table: str,
        query: str,
        limit: int,
        fields: list,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        return await search_fulltext_impl(
            self._require_pool(), table, query, limit, fields, filter_criteria
        )

    async def search_hybrid(
        self,
        query: str,
        vector: list,
        table: str,
        limit: int,
        threshold: float,
        vector_weight: float = 0.5,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        return await search_hybrid_impl(
            self._require_pool(),
            query,
            vector,
            table,
            limit,
            threshold,
            vector_weight,
            filter_criteria,
        )

    async def relate(
        self,
        subject: str,
        predicate: str,
        object: str,
        data: Optional[Dict] = None,
    ) -> bool:
        return await graph_relate(
            self._require_pool(), subject, predicate, object, data
        )

    async def get_neighbors(self, node_id: str, depth: int = 1) -> list:
        return await graph_get_neighbors(self._require_pool(), node_id, depth)

    async def publish(self, channel: str, message: Dict[str, Any]):
        return await notifications_publish(self._require_pool(), channel, message)

    async def listen(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        async for item in notifications_listen(self._require_pool(), channel):
            yield item
