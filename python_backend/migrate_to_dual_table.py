"""
数据迁移脚本：从旧的 conversation 表迁移到 conversation_log
- 所有旧数据 -> conversation_log (is_processed=False)
- 让 Extractor 统一处理

运行方式: python python_backend/migrate_to_dual_table.py
"""
import asyncio
from surrealdb import AsyncSurreal
from datetime import datetime

# SurrealDB 连接配置
SURREAL_URL = "ws://127.0.0.1:8000/rpc"
SURREAL_USER = "root"
SURREAL_PASS = "root"
NAMESPACE = "lumina"
DATABASE = "memory"


async def migrate():
    db = AsyncSurreal(SURREAL_URL)
    await db.connect()
    await db.signin({"username": SURREAL_USER, "password": SURREAL_PASS})
    await db.use(NAMESPACE, DATABASE)
    
    print("=" * 50)
    print("开始数据迁移: conversation -> conversation_log")
    print("=" * 50)
    
    # 1. 检查旧表是否存在
    try:
        old_data = await db.query("SELECT count() FROM conversation GROUP ALL;")
        print(f"DEBUG: count query result = {old_data}")
        
        # 解析不同格式的返回值
        count = 0
        if old_data:
            if isinstance(old_data, list) and len(old_data) > 0:
                first = old_data[0]
                if isinstance(first, dict):
                    if 'result' in first:
                        # 格式: [{'result': [{'count': N}]}]
                        res = first['result']
                        if isinstance(res, list) and len(res) > 0:
                            count = res[0].get('count', 0)
                    elif 'count' in first:
                        # 格式: [{'count': N}]
                        count = first.get('count', 0)
        
        if count == 0:
            print("⚠️ 旧表 'conversation' 不存在或为空")
            await db.close()
            return
        else:
            print(f"\n📊 旧表 'conversation' 中有 {count} 条记录")
            
    except Exception as e:
        print(f"❌ 无法读取旧表: {e}")
        await db.close()
        return
    
    # 2. 获取所有旧数据
    result = await db.query("SELECT * FROM conversation;")
    print(f"DEBUG: select result type = {type(result)}")
    
    old_records = []
    if result:
        if isinstance(result, list) and len(result) > 0:
            first = result[0]
            if isinstance(first, dict) and 'result' in first:
                old_records = first['result'] or []
            elif isinstance(first, dict):
                old_records = result
                
    if not old_records:
        print("⚠️ 没有数据需要迁移")
        await db.close()
        return
    
    
    print(f"📦 准备迁移 {len(old_records)} 条记录到 conversation_log...\n")
    
    log_count = 0
    
    for record in old_records:
        agent_id = record.get('agent_id', 'default')
        
        # 全部迁移到 conversation_log，标记为未处理
        log_data = {
            "character_id": agent_id,
            "narrative": record.get('narrative', ''),
            "created_at": record.get('created_at', datetime.now().isoformat()),
            "is_processed": False  # 全部标记为未处理，让 Extractor 处理
        }
        await db.create("conversation_log", log_data)
        log_count += 1
        
        if log_count % 50 == 0:
            print(f"   已迁移 {log_count} 条...")
    
    print(f"\n✅ 迁移完成! 共 {log_count} 条记录已写入 conversation_log")
    
    # 3. 验证新表数据
    log_check = await db.query("SELECT count() FROM conversation_log GROUP ALL;")
    log_total = log_check[0]['result'][0].get('count', 0) if log_check and log_check[0].get('result') else 0
    
    print(f"\n📊 验证: conversation_log 总计 {log_total} 条")
    
    # 4. 提示删除旧表
    print("\n" + "=" * 50)
    print("⚠️  迁移完成。如需删除旧表，请手动执行:")
    print("    surreal sql --user root --pass root --ns lumina --db memory")
    print("    > REMOVE TABLE conversation;")
    print("=" * 50)
    
    await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())

