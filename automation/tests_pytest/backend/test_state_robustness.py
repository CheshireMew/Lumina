import pytest
import asyncpg
import json
import httpx
from app_config import config

@pytest.mark.backend
@pytest.mark.anyio
async def test_plugin_state_corruption_recovery():
    """验证手动篡改数据库数据后，后端是否能健壮处理而不崩溃"""
    pg_config = config.memory.postgres
    
    plugin_id = "test.corrupt_plugin"
    record_id = f"plugin_state:{plugin_id.replace('.', '_')}"
    
    try:
        conn = await asyncpg.connect(
            user=pg_config.user,
            password=pg_config.password,
            database=pg_config.database,
            host=pg_config.host,
            port=pg_config.port
        )
        try:
            print(f"\n[Test] Injecting corrupt JSON into 'plugin_state' for {plugin_id}...")
            corrupt_data = "{\"enabled\": \"invalid_boolean_string\", \"metadata\": [1,2,3]}"
            
            await conn.execute("""
                INSERT INTO plugin_state (id, plugin_id, desired_enabled, active_status, data)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET data = $5
            """, record_id, plugin_id, None, "corrupt", corrupt_data)
        finally:
            await conn.close()
        
        print("[Test] Corruption injected. Fetching plugin list via API...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://127.0.0.1:8010/plugins/list")
            assert response.status_code == 200
            
            plugins = response.json()
            corrupt_plugin = next((p for p in plugins if p['id'] == plugin_id), None)
            
            if corrupt_plugin:
                print(f"[Test] Corrupt plugin found in list. Status: {corrupt_plugin.get('status')}")
            else:
                print("[Test] Corrupt plugin filtered out by backend.")
                
    finally:
        # Cleanup connection
        conn = await asyncpg.connect(
            user=pg_config.user,
            password=pg_config.password,
            database=pg_config.database,
            host=pg_config.host,
            port=pg_config.port
        )
        await conn.execute("DELETE FROM plugin_state WHERE id = $1", record_id)
        await conn.close()

@pytest.mark.backend
@pytest.mark.anyio
async def test_null_value_resilience():
    """验证关键字段为 NULL 时的容错性"""
    pg_config = config.memory.postgres
    
    plugin_id = "test.null_plugin"
    record_id = f"plugin_state:{plugin_id.replace('.', '_')}"
    
    try:
        conn = await asyncpg.connect(
            user=pg_config.user,
            password=pg_config.password,
            database=pg_config.database,
            host=pg_config.host,
            port=pg_config.port
        )
        try:
            print(f"\n[Test] Injecting NULL active_status for {plugin_id}...")
            await conn.execute("""
                INSERT INTO plugin_state (id, plugin_id, desired_enabled, active_status, data)
                VALUES ($1, $2, $3, $4, $5)
            """, record_id, plugin_id, None, None, "{}")
        finally:
            await conn.close()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://127.0.0.1:8010/plugins/list")
            assert response.status_code == 200
            print("[Test] API handles NULL fields gracefully.")
            
    finally:
        conn = await asyncpg.connect(
            user=pg_config.user,
            password=pg_config.password,
            database=pg_config.database,
            host=pg_config.host,
            port=pg_config.port
        )
        await conn.execute("DELETE FROM plugin_state WHERE id = $1", record_id)
        await conn.close()
