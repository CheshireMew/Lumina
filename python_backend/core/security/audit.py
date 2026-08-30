import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("AuditLogger")


class AuditLogger:
    """
    Asynchronous Security Audit Logger.
    Writes events to Lumina's managed local database.
    """
    
    @staticmethod
    async def log_event(
        actor_id: str,
        action: str,
        target: str,
        status: str = "granted",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a security event.
        actor_id: Service ID, worker ID, or user ID
        action: e.g. "permission_request", "file_access"
        target: e.g. "system.filesystem", "/etc/passwd"
        status: "granted" or "blocked"
        """
        from services.infra.local_state_store import get_local_state_store

        await get_local_state_store().write_audit_event(
            actor_id=actor_id,
            action=action,
            target=target,
            status=status,
            metadata=metadata,
        )

    @staticmethod
    async def _try_log_event(
        actor_id: str,
        action: str,
        target: str,
        status: str = "granted",
        metadata: Optional[Dict[str, Any]] = None
    ):
        try:
            await AuditLogger.log_event(actor_id, action, target, status, metadata)
        except Exception as e:
            logger.error(f"❌ Failed to write audit log: {e}")

    @staticmethod
    def schedule_event(
        actor_id: str,
        action: str,
        target: str,
        status: str = "granted",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Schedule a best-effort audit write without blocking the caller."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(AuditLogger._try_log_event(actor_id, action, target, status, metadata))
            else:
                asyncio.run(AuditLogger._try_log_event(actor_id, action, target, status, metadata))
        except RuntimeError:
            asyncio.run(AuditLogger._try_log_event(actor_id, action, target, status, metadata))
