"""
Consolidation Batch Manager
管理检索-整合周期的记忆 ID 跟踪
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import uuid
import logging

logger = logging.getLogger("ConsolidationBatch")


@dataclass
class ConsolidationBatch:
    """
    跟踪一次检索-整合周期的记忆 ID
    
    生命周期:
    1. 创建时：记录 retrieved_ids（检索命中）
    2. 发送 LLM 时：记录 sent_to_llm_ids（实际发送）
    3. 整合完成：删除/归档 sent_to_llm_ids 中的旧记忆
    """
    
    batch_id: str = field(default_factory=lambda: f"batch_{uuid.uuid4().hex[:8]}")
    character_id: str = ""
    
    # 阶段 1：检索命中的记忆 ID
    retrieved_ids: List[str] = field(default_factory=list)
    
    # 阶段 2：实际发送给 LLM 的记忆 ID（用于后续删除/归档）
    sent_to_llm_ids: List[str] = field(default_factory=list)
    
    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    
    # 状态：pending / processing / completed / failed
    status: str = "pending"
    
    def __repr__(self):
        return f"<Batch {self.batch_id} [{self.status}] retrieved={len(self.retrieved_ids)} sent={len(self.sent_to_llm_ids)}>"


class BatchManager:
    """
    管理所有待处理的整合批次
    
    使用场景:
    1. search_hybrid() 检索后创建批次
    2. Consolidator 处理批次中的记忆
    3. 整合完成后清理批次
    """
    
    def __init__(self):
        self.pending_batches: Dict[str, ConsolidationBatch] = {}
        logger.info("[BatchManager] Initialized")
    
    def create_batch(self, character_id: str, retrieved_ids: List[str]) -> ConsolidationBatch:
        """
        创建新的整合批次
        
        Args:
            character_id: 角色 ID
            retrieved_ids: 检索命中的记忆 ID 列表
            
        Returns:
            新创建的 ConsolidationBatch
        """
        batch = ConsolidationBatch(
            character_id=character_id.lower(),
            retrieved_ids=retrieved_ids
        )
        self.pending_batches[batch.batch_id] = batch
        logger.info(f"[BatchManager] Created batch {batch.batch_id} with {len(retrieved_ids)} memories for '{character_id}'")
        return batch
    
    def mark_sent_to_llm(self, batch_id: str, sent_ids: List[str]):
        """
        记录发送给 LLM 的记忆 ID
        
        Args:
            batch_id: 批次 ID
            sent_ids: 实际发送给 LLM 的记忆 ID 列表
        """
        if batch_id in self.pending_batches:
            self.pending_batches[batch_id].sent_to_llm_ids = sent_ids
            self.pending_batches[batch_id].status = "processing"
            logger.debug(f"[BatchManager] Batch {batch_id} marked as processing with {len(sent_ids)} sent IDs")
    
    def get_batch(self, batch_id: str) -> Optional[ConsolidationBatch]:
        """获取指定批次"""
        return self.pending_batches.get(batch_id)
    
    def get_pending_batches(self, character_id: str) -> List[ConsolidationBatch]:
        """
        获取某角色的所有待处理批次
        
        Args:
            character_id: 角色 ID
            
        Returns:
            待处理批次列表（按创建时间排序）
        """
        batches = [
            b for b in self.pending_batches.values() 
            if b.character_id == character_id.lower() and b.status == "pending"
        ]
        return sorted(batches, key=lambda x: x.created_at)
    
    def get_oldest_pending_batch(self, character_id: str) -> Optional[ConsolidationBatch]:
        """获取某角色最旧的待处理批次"""
        batches = self.get_pending_batches(character_id)
        return batches[0] if batches else None
    
    def complete_batch(self, batch_id: str):
        """
        标记批次为完成并移除
        
        Args:
            batch_id: 批次 ID
        """
        if batch_id in self.pending_batches:
            batch = self.pending_batches.pop(batch_id)
            logger.info(f"[BatchManager] Batch {batch_id} completed and removed")
            return batch
        return None
    
    def fail_batch(self, batch_id: str, reason: str = ""):
        """标记批次失败"""
        if batch_id in self.pending_batches:
            self.pending_batches[batch_id].status = "failed"
            logger.warning(f"[BatchManager] Batch {batch_id} failed: {reason}")
    
    def get_stats(self) -> Dict:
        """获取批次统计信息"""
        stats = {
            "total_batches": len(self.pending_batches),
            "by_status": {},
            "by_character": {}
        }
        for batch in self.pending_batches.values():
            stats["by_status"][batch.status] = stats["by_status"].get(batch.status, 0) + 1
            stats["by_character"][batch.character_id] = stats["by_character"].get(batch.character_id, 0) + 1
        return stats
