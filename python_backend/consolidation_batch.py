"""
Consolidation Batch Manager
Consolidation Batch Manager
Manage retrieval/consolidation cycle IDs
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
    Track IDs for one retrieval/consolidation cycle
    
    Lifecycle:
    1. Created: Record retrieved_ids (Search hits)
    2. Sent to LLM: Record sent_to_llm_ids
    3. Completed: Delete/Archive old memories
    """
    
    batch_id: str = field(default_factory=lambda: f"batch_{uuid.uuid4().hex[:8]}")
    character_id: str = ""
    
    # Stage 1: Retrieved IDs
    retrieved_ids: List[str] = field(default_factory=list)
    
    # Stage 2: Sent to LLM IDs
    sent_to_llm_ids: List[str] = field(default_factory=list)
    
    # Timestamp
    created_at: datetime = field(default_factory=datetime.now)
    
    # Status: pending / processing / completed / failed
    status: str = "pending"
    
    def __repr__(self):
        return f"<Batch {self.batch_id} [{self.status}] retrieved={len(self.retrieved_ids)} sent={len(self.sent_to_llm_ids)}>"


class BatchManager:
    """
    Manage all pending consolidation batches
    
    Usage:
    1. search_hybrid() creates batch
    2. Consolidator processes batch
    3. Cleanup on completion
    """
    
    def __init__(self):
        self.pending_batches: Dict[str, ConsolidationBatch] = {}
        logger.info("[BatchManager] Initialized")
    
    def create_batch(self, character_id: str, retrieved_ids: List[str]) -> ConsolidationBatch:
        """
        Create new batch
        
        Args:
            character_id: Character ID
            retrieved_ids: List of retrieved IDs
            
        Returns:
            Created ConsolidationBatch
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
        Record IDs sent to LLM
        
        Args:
            batch_id: 鎵规 ID
            sent_ids: 瀹為檯鍙戦€佺粰 LLM 鐨勮蹇?ID 鍒楄〃
        """
        if batch_id in self.pending_batches:
            self.pending_batches[batch_id].sent_to_llm_ids = sent_ids
            self.pending_batches[batch_id].status = "processing"
            logger.debug(f"[BatchManager] Batch {batch_id} marked as processing with {len(sent_ids)} sent IDs")
    
    def get_batch(self, batch_id: str) -> Optional[ConsolidationBatch]:
        """Get specific batch"""
        return self.pending_batches.get(batch_id)
    
    def get_pending_batches(self, character_id: str) -> List[ConsolidationBatch]:
        """
        Get all pending batches for character
        
        Args:
            character_id: Character ID
            
        Returns:
            List of pending batches (sorted)
        """
        batches = [
            b for b in self.pending_batches.values() 
            if b.character_id == character_id.lower() and b.status == "pending"
        ]
        return sorted(batches, key=lambda x: x.created_at)
    
    def get_oldest_pending_batch(self, character_id: str) -> Optional[ConsolidationBatch]:
        """Get oldest pending batch"""
        batches = self.get_pending_batches(character_id)
        return batches[0] if batches else None
    
    def complete_batch(self, batch_id: str):
        """
        Mark batch as complete and remove
        
        Args:
            batch_id: 鎵规 ID
        """
        if batch_id in self.pending_batches:
            batch = self.pending_batches.pop(batch_id)
            logger.info(f"[BatchManager] Batch {batch_id} completed and removed")
            return batch
        return None
    
    def fail_batch(self, batch_id: str, reason: str = ""):
        """Mark batch as failed"""
        if batch_id in self.pending_batches:
            self.pending_batches[batch_id].status = "failed"
            logger.warning(f"[BatchManager] Batch {batch_id} failed: {reason}")
    
    def get_stats(self) -> Dict:
        """Get batch statistics"""
        stats = {
            "total_batches": len(self.pending_batches),
            "by_status": {},
            "by_character": {}
        }
        for batch in self.pending_batches.values():
            stats["by_status"][batch.status] = stats["by_status"].get(batch.status, 0) + 1
            stats["by_character"][batch.character_id] = stats["by_character"].get(batch.character_id, 0) + 1
        return stats
