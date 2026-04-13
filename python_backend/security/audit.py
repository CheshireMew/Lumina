import logging
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("AuditLogger")

class AuditAction(str, Enum):
    """Standard Audit Actions"""
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PLUGIN_LOAD = "plugin.load"
    PLUGIN_UNLOAD = "plugin.unload"
    SENSITIVE_CALL = "call.sensitive" # e.g. deleting files, network request
    
class AuditLogger:
    """
    [Architecture 6.0] Security Audit System.
    Records 'Who did What' to a persistent audit log.
    Current Setup: Local JSONL file.
    Future: unified database-backed audit stream.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AuditLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = "logs/audit"):
        if hasattr(self, "_initialized"):
            return
            
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self.log_dir / "audit.jsonl"
        self._initialized = True
        
        logger.info(f"🛡️ Audit Logger initialized at {self.current_log_file}")

    def log(self, 
            plugin_id: str, 
            action: AuditAction, 
            target: str, 
            status: str = "success", 
            metadata: Optional[Dict[str, Any]] = None):
        """
        Record an audit event.
        """
        event = {
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "plugin_id": plugin_id,
            "action": action.value,
            "target": target,
            "status": status,
            "metadata": metadata or {}
        }
        
        try:
            # Atomic append (OS dependent, but good enough for now)
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
                
            if status != "success":
                logger.warning(f"🛡️ AUDIT ALERT: {plugin_id} -> {action} on {target} ({status})")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

# Global Singleton Helper
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if not _audit_logger:
        # Default path relative to cwd (python_backend or project root)
        # Assuming python_backend based on current context
        _audit_logger = AuditLogger(log_dir="logs/audit")
    return _audit_logger
