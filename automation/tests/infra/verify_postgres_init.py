import asyncio
import logging
import sys
import os

# Add python_backend to path
sys.path.append(os.path.join(os.getcwd(), "python_backend"))

from memory.factory import MemoryDriverFactory
from app_config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBVerify")

async def verify_postgres():
    logger.info("馃攧 Starting PostgreSQL Verification...")
    
    # 1. Force reload config to pick up NEW provider
    config.load_configs()
    logger.info(f"馃搼 Active Provider: {config.get_selected_provider('memory')}")
    
    # 2. Create Driver via Factory
    try:
        # Debug: List all discovered drivers
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Manual scan to see what's happening
        logger.info("Checking for postgres provider driver...")
        
        driver = MemoryDriverFactory.create_driver(
            config.get_selected_provider("memory"),
            driver_config=config.memory.model_dump(),
        )
        logger.info(f"鉁?Driver Loaded: {driver.name} ({driver.id})")
        
        if driver.id != "driver.memory.postgres":
            logger.error(f"鈿狅笍 Expected 'driver.memory.postgres' but got '{driver.id}'")
            logger.info("Checking config object directly:")
            logger.info(f"selected memory provider: {config.get_selected_provider('memory')}")
            # Try to force it
            logger.info("Attempting to force postgres driver...")
            driver = MemoryDriverFactory.create_driver(
                "driver.memory.postgres",
                driver_config=config.memory.model_dump(),
            )
            logger.info(f"鉁?Forced Driver Loaded: {driver.name} ({driver.id})")
        
        # 3. Connect (Initializes Schema)
        await driver.connect()
        logger.info("鉁?Database Connected & Schema Initialized.")
        
        # 4. Test CRUD
        test_data = {
            "character_id": "test_bot",
            "scope": "relationship",
            "memory_type": "episode",
            "content": "Hello, this is a test memory from Lumina!",
            "embedding": [0.1] * 384, # 384 dimensions
            "status": "active"
        }
        mem_id = await driver.create("memory_items", test_data)
        logger.info(f"鉁?Memory Created. ID: {mem_id}")
        
        # 5. Test Vector Search
        logger.info("馃攧 Testing Vector Search...")
        query_vec = [0.1] * 384
        results = await driver.search_vector("memory_items", query_vec, limit=5, threshold=0.1)
        
        if results:
            logger.info(f"鉁?Vector Search Success! Hits: {len(results)}")
            for r in results:
                logger.info(f"   - [{r.get('id')}] Content: {r.get('content')} (Score: {r.get('score'):.4f})")
        else:
            logger.error("鉂?Vector Search returned NO results.")
            
        # 6. Cleanup
        await driver.close()
        logger.info("鉁?Verification Complete.")

    except Exception as e:
        logger.error(f"鉂?Verification Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_postgres())
