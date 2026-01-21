import asyncio
import asyncpg
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBInit")

async def init_db(password: str):
    logger.info("馃攧 Connecting to local PostgreSQL to initialize Lumina...")
    
    # 1. Connect to default 'postgres' database
    try:
        conn = await asyncpg.connect(
            user='postgres',
            password=password,
            host='127.0.0.1',
            port=5433,
            database='postgres'
        )
        logger.info("鉁?Connected to 'postgres' database.")
        
        # 2. CREATE DATABASE (if not exists)
        # Note: CREATE DATABASE cannot run inside a transaction
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'lumina_db'")
        if not db_exists:
            # We need to close and reopen or use a separate connection for non-transactional SQL
            # asyncpg doesn't support non-transactional commands easily on the same connection if it's already in one.
            # But wait, conn.execute is fine if we aren't in a manual transaction.
            await conn.execute("CREATE DATABASE lumina_db")
            logger.info("鉁?Created database 'lumina_db'.")
        else:
            logger.info("馃搼 Database 'lumina_db' already exists.")

        # 3. CREATE USER (if not exists)
        user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'lumina_user'")
        if not user_exists:
            await conn.execute("CREATE USER lumina_user WITH PASSWORD 'lumina_password'")
            logger.info("鉁?Created user 'lumina_user'.")
        
        await conn.execute("GRANT ALL PRIVILEGES ON DATABASE lumina_db TO lumina_user")
        # [Fix] PG 15+ needs explicit schema permissions
        await conn.execute("ALTER DATABASE lumina_db OWNER TO lumina_user")
        logger.info("鉁?Ensured lumina_user is OWNER of lumina_db.")

        await conn.close()

        # 4. Connect to 'lumina_db' to enable extension
        conn = await asyncpg.connect(
            user='postgres',
            password=password,
            host='127.0.0.1',
            port=5433,
            database='lumina_db'
        )
        
        logger.info("馃攧 Enabling pgvector extension in 'lumina_db'...")
        try:
            # Grant schema permission just in case
            await conn.execute("GRANT ALL ON SCHEMA public TO lumina_user")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("鉁?Extension 'vector' enabled.")
        except Exception as e:
            logger.error(f"鈿狅笍 Failed to enable extension: {e}")
            logger.info("馃挕 Make sure you copied the pgvector files to the PostgreSQL directory.")

        # 5. Verify
        ext_info = await conn.fetchrow("SELECT extname, extversion FROM pg_extension WHERE extname='vector'")
        if ext_info:
            logger.info(f"鉁?Verification: {ext_info['extname']} v{ext_info['extversion']} is ACTIVE.")
        
        await conn.close()
        logger.info("鉁?Initialization Complete.")

    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        logger.info("馃挕 Check your postgres password.")

if __name__ == "__main__":
    pw = sys.argv[1] if len(sys.argv) > 1 else 'lumina_password'
    asyncio.run(init_db(pw))
