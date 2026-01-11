import logging
from typing import Optional
from surrealdb import AsyncSurreal
from app_config import config

logger = logging.getLogger("memory.connection")

class DBConnection:
    """
    Singleton Wrapper for SurrealDB Connection.
    Ensures a single active connection is shared across valid scopes.
    """
    _db: Optional[AsyncSurreal] = None
    
    @classmethod
    async def get_db(cls) -> AsyncSurreal:
        """Get the active DB instance. Auto-connects if not connected."""
        if cls._db is None:
            await cls._connect()
        return cls._db

    @classmethod
    async def _connect(cls):
        """Internal connection logic using app_config with retry"""
        url = config.memory.url
        import asyncio
        
        max_retries = 5
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔌 Connecting to SurrealDB at {url} (Attempt {attempt+1}/{max_retries})...")
                
                # Initialize Client
                db = AsyncSurreal(url)
                await db.connect()
                
                # Sign in & Select Namespace
                await db.signin({
                    "username": config.memory.user,
                    "password": config.memory.password
                })
                await db.use(config.memory.namespace, config.memory.database)
                
                cls._db = db
                logger.info("✅ Connected to SurrealDB successfully")
                return # Success
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to SurrealDB (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    wait_time = base_delay * (attempt + 1)
                    logger.info(f"⏳ Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    cls._db = None
                    raise

    @classmethod
    async def close(cls):
        """Close the connection explicitly"""
        if cls._db:
            try:
                await cls._db.close()
            except Exception as e:
                logger.warning(f"Error closing DB: {e}")
            finally:
                cls._db = None

    @classmethod
    async def connect(cls):
        """Public entry point to ensure connection is active"""
        if cls._db is None:
            await cls._connect()

