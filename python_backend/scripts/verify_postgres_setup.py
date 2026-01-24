import asyncio
import asyncpg
import logging
import sys
import os

# Ensure python_backend is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app_config import config

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PostgresVerify")

async def verify_postgres():
    pg_conf = config.memory.postgres
    
    logger.info(f"🔍 Checking PostgreSQL Configuration: {pg_conf.host}:{pg_conf.port}")
    logger.info(f"   Target Database: {pg_conf.database}")
    logger.info(f"   User: {pg_conf.user}")

    # 1. Connect to default 'postgres' database to check/create target DB
    sys_conn = None
    try:
        sys_conn = await asyncpg.connect(
            user=pg_conf.user,
            password=pg_conf.password,
            database="postgres",
            host=pg_conf.host,
            port=pg_conf.port
        )
        logger.info("✅ Connected to system database 'postgres'")
    except Exception as e:
        logger.error(f"❌ Failed to connect to system database 'postgres'. Check credentials/server status. Error: {e}")
        return

    try:
        # Check if database exists
        exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", pg_conf.database)
        
        if not exists:
            logger.warning(f"⚠️ Database '{pg_conf.database}' does not exist. Attempting to create...")
            await sys_conn.execute(f'CREATE DATABASE "{pg_conf.database}"')
            logger.info(f"✅ Database '{pg_conf.database}' created successfully.")
        else:
            logger.info(f"✅ Database '{pg_conf.database}' exists.")
            
    except Exception as e:
        logger.error(f"❌ Error checking/creating database: {e}")
        return
    finally:
        await sys_conn.close()

    # 2. Connect to Target Database to Setup Extensions
    target_conn = None
    try:
        target_conn = await asyncpg.connect(
            user=pg_conf.user,
            password=pg_conf.password,
            database=pg_conf.database,
            host=pg_conf.host,
            port=pg_conf.port
        )
        logger.info(f"✅ Connected to target database '{pg_conf.database}'")
        
        # Check/Enable pgvector
        logger.info("🔧 Checking extensions...")
        await target_conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("✅ Extension 'vector' verified/enabled.")
        
        # Check privileges (Basic check likely covered by being able to create extension)
        
    except Exception as e:
        logger.error(f"❌ Error configuring target database: {e}")
    finally:
        if target_conn:
            await target_conn.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_postgres())
