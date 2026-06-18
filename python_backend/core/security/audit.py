import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("AuditLogger")


class AuditLogger:
    """
    Asynchronous Security Audit Logger.
    Writes events to PostgreSQL 'security_audit' table.
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
        actor_id: Capability module ID or user ID
        action: e.g. "permission_request", "file_access"
        target: e.g. "system.filesystem", "/etc/passwd"
        status: "granted" or "blocked"
        """
        from services.infra.bus_factory import get_lifecycle_bus

        bus = get_lifecycle_bus()
        pool = await bus.get_pool()

        data = {
            "timestamp": datetime.now(),
            "actor_id": actor_id,
            "action": action,
            "target": target,
            "status": status,
            "metadata": json.dumps(metadata or {}),
        }

        await pool.execute(
            """
            INSERT INTO security_audit (timestamp, actor_id, action, target, status, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            data["timestamp"],
            data["actor_id"],
            data["action"],
            data["target"],
            data["status"],
            data["metadata"],
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
