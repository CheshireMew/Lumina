"""
数据迁移脚本：将所有旧记忆归属给 hiyori

运行方法：
python migrate_memory_character_id.py

注意：这会遍历所有 Qdrant collection 中的记忆，为缺少 character_id 的记忆标记为 hiyori。
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
from pathlib import Path

def migrate_to_hiyori():
    """将所有旧记忆数据标记为 hiyori"""
    
    # 1. 连接到 Qdrant（使用绝对路径）
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    qdrant_path = os.path.join(project_root, "lite_memory_db")
    
    print(f"[Migration] 连接到 Qdrant: {qdrant_path}")
    
    client = QdrantClient(path=qdrant_path)
    
    print(f"[Migration] 将所有旧记忆归属给: hiyori\n")
    
    # 2. 获取所有 collections
    collections = client.get_collections()
    print(f"[Migration] 找到 {len(collections.collections)} 个 collections")
    
    total_updated = 0
    total_processed = 0
    
    for collection in collections.collections:
        col_name = collection.name
        print(f"\n[Migration] 处理 collection: {col_name}")
        
        # 3. 获取所有 points（分批处理）
        offset = None
        updated_count = 0
        processed_count = 0
        
        while True:
            # 每次获取 100 个 points
            scroll_result = client.scroll(
                collection_name=col_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False  # 不需要 vectors
            )
            
            points = scroll_result[0]
            next_offset = scroll_result[1]
            
            if not points:
                break
            
            # 4. 检查并更新缺少 character_id 的 points
            for point in points:
                processed_count += 1
                payload = point.payload or {}
                
                # 如果没有 character_id，标记为 hiyori
                if "character_id" not in payload:
                    payload["character_id"] = "hiyori"
                    
                    # 使用 set_payload 更新（不重新计算 vector）
                    client.set_payload(
                        collection_name=col_name,
                        payload=payload,
                        points=[point.id]
                    )
                    updated_count += 1
                    
                    if updated_count % 10 == 0:
                        print(f"[Migration]   已更新 {updated_count} 个记忆...")
            
            # 5. 继续下一批
            if next_offset is None:
                break
            offset = next_offset
        
        print(f"[Migration] ✅ Collection '{col_name}' 完成")
        print(f"[Migration]    总计: {processed_count} 个记忆")
        print(f"[Migration]    更新: {updated_count} 个记忆")
        
        total_processed += processed_count
        total_updated += updated_count
    
    print(f"\n[Migration] ========== 迁移完成 ==========")
    print(f"[Migration] 总处理: {total_processed} 个记忆")
    print(f"[Migration] 总更新: {total_updated} 个记忆")
    print(f"[Migration] 所有旧记忆已归属给 hiyori ✅")

if __name__ == "__main__":
    try:
        migrate_to_hiyori()
    except Exception as e:
        print(f"[Migration] ❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
