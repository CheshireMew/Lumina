import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("AuditLogger")

class AuditLogger:
    """
    Asynchronous Security Audit Logger.
    Writes events to SurrealDB 'security_audit' table.
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
        actor_id: Plugin ID or User ID
        action: e.g. "permission_request", "file_access"
        target: e.g. "system.filesystem", "/etc/passwd"
        status: "granted" or "blocked"
        """
        try:
            from services.infra.bus_factory import get_lifecycle_bus
            bus = get_lifecycle_bus()
            
            # Ensure bus is connected
            if not getattr(bus, "_is_connected", False):
                await bus.connect()
            
            # We use the underlying DB if reachable
            # Note: SurrealLifecycleBus has a .db (AsyncSurreal) instance
            # PostgresLifecycleBus has a .db (asyncpg.Pool) instance
            if hasattr(bus, "db") and bus.db:
                data = {
                    "timestamp": datetime.now(),
                    "actor_id": actor_id,
                    "action": action,
                    "target": target,
                    "status": status,
                    "metadata": json.dumps(metadata or {}) if not hasattr(bus.db, "create") else (metadata or {})
                }
                
                # SurrealDB (Legacy)
                if hasattr(bus.db, "create"):
                    data["timestamp"] = data["timestamp"].isoformat()
                    await bus.db.create("security_audit", data)
                # PostgreSQL (New)
                else:
                    await bus.db.execute("""
                        INSERT INTO security_audit (timestamp, actor_id, action, target, status, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, data["timestamp"], data["actor_id"], data["action"], data["target"], data["status"], data["metadata"])
                
                logger.info(f"🛡️ [Audit] {status.upper()}: {actor_id} -> {action} on {target}")
            else:
                # Log to console at least
                logger.warning(f"⚠️ [Audit] Bus/DB not available. Event: {actor_id} {action}")
                
        except Exception as e:
            logger.error(f"❌ Failed to write audit log: {e}")

    @staticmethod
    def log_event_sync(
        actor_id: str,
        action: str,
        target: str,
        status: str = "granted",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Sync wrapper to schedule log in existing loop"""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(AuditLogger.log_event(actor_id, action, target, status, metadata))
            else:
                asyncio.run(AuditLogger.log_event(actor_id, action, target, status, metadata))
        except RuntimeError:
            # Fallback if no loop
            try:
                asyncio.run(AuditLogger.log_event(actor_id, action, target, status, metadata))
            except:
                pass
