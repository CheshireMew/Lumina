"""
Worker Control WebSocket Protocol.
Defines message types and schemas for Main <-> Worker real-time communication.
"""

import struct
import json
import time
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WsMessageType(str, Enum):
    """WebSocket message types for Worker Control Channel."""
    # Worker -> Main
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    REGISTER = "register"
    
    # Main -> Worker
    CONFIG_UPDATE = "config_update"
    LIFECYCLE = "lifecycle"
    
    # Bidirectional
    ACK = "ack"
    ERROR = "error"


class PluginStatusPayload(BaseModel):
    """Plugin status included in status reports."""
    id: str
    name: str
    enabled: bool
    status: str = "unknown"  # healthy, degraded, error
    kind: Optional[str] = None
    category: str = "other"
    desired_enabled: Optional[bool] = None
    active: Optional[bool] = None
    active_status: Optional[str] = None
    computed_status: Optional[str] = None
    group_id: Optional[str] = None
    group_policy: Optional[str] = None
    active_in_group: Optional[bool] = None
    version: Optional[str] = None
    capability: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    runtime_target: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    current_config: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    load_time_ms: Optional[int] = None
    service_url: Optional[str] = None
    driver_id: Optional[str] = None


class WorkerRegisterPayload(BaseModel):
    """Payload for worker registration."""
    worker_id: str
    worker_type: str  # stt, tts, vision, memory
    runtime_target: Optional[str] = None
    host: str = "127.0.0.1"
    port: int
    version: Optional[str] = None


class HeartbeatPayload(BaseModel):
    """Payload for heartbeat messages."""
    worker_id: str
    load: float = 0.0  # 0.0 - 1.0


class StatusPayload(BaseModel):
    """Detailed status report from worker."""
    worker_id: str
    status: str = "healthy"  # healthy, degraded, error
    load: float = 0.0
    plugins: List[PluginStatusPayload] = Field(default_factory=list)
    uptime_seconds: Optional[float] = None


class ConfigUpdatePayload(BaseModel):
    """Config update pushed from Main."""
    section: Optional[str] = None  # e.g., "stt", "tts", or None for full
    data: Dict[str, Any] = Field(default_factory=dict)
    reload_required: bool = False


class LifecyclePayload(BaseModel):
    """Lifecycle command from Main."""
    action: str  # enable, disable, restart
    target_id: str  # plugin_id or "worker"


class WsMessage(BaseModel):
    """
    Universal WebSocket message envelope.
    All messages through the Worker Control Channel use this format.
    """
    type: WsMessageType
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)
    
    @classmethod
    def heartbeat(cls, worker_id: str, load: float = 0.0) -> "WsMessage":
        return cls(
            type=WsMessageType.HEARTBEAT,
            payload=HeartbeatPayload(worker_id=worker_id, load=load).model_dump()
        )
    
    @classmethod
    def status(cls, worker_id: str, plugins: List[PluginStatusPayload], 
               load: float = 0.0, uptime: float = None) -> "WsMessage":
        return cls(
            type=WsMessageType.STATUS,
            payload=StatusPayload(
                worker_id=worker_id,
                load=load,
                plugins=plugins,
                uptime_seconds=uptime
            ).model_dump()
        )
    
    @classmethod
    def register(cls, worker_id: str, worker_type: str, port: int, runtime_target: str | None = None) -> "WsMessage":
        return cls(
            type=WsMessageType.REGISTER,
            payload=WorkerRegisterPayload(
                worker_id=worker_id,
                worker_type=worker_type,
                port=port,
                runtime_target=runtime_target,
            ).model_dump()
        )
    
    @classmethod
    def config_update(cls, data: Dict[str, Any], section: str = None) -> "WsMessage":
        return cls(
            type=WsMessageType.CONFIG_UPDATE,
            payload=ConfigUpdatePayload(section=section, data=data).model_dump()
        )
    
    @classmethod
    def lifecycle(cls, action: str, target_id: str) -> "WsMessage":
        return cls(
            type=WsMessageType.LIFECYCLE,
            payload=LifecyclePayload(action=action, target_id=target_id).model_dump()
        )
    
    @classmethod
    def ack(cls, session_id: str = None) -> "WsMessage":
        return cls(type=WsMessageType.ACK, session_id=session_id)
    
    @classmethod
    def error(cls, message: str) -> "WsMessage":
        return cls(type=WsMessageType.ERROR, payload={"message": message})

    # --- Binary Protocol (v1.5) ---

    def pack_binary(self, binary_body: bytes) -> bytes:
        """
        Pack this WsMessage (Metadata) + Binary Body into a single byte stream.
        Format: [4-byte Header Len (BE)] [JSON Metadata] [Binary Body]
        """
        metadata_json = self.model_dump_json().encode('utf-8')
        header_len = len(metadata_json)
        
        # Struct: I = unsigned int (4 bytes)
        # > = Big Endian
        header_bytes = struct.pack(">I", header_len)
        
        return header_bytes + metadata_json + binary_body

    @classmethod
    def unpack_binary(cls, data: bytes) -> tuple["WsMessage", bytes]:
        """
        Unpack a binary frame into (WsMessage, BinaryBody).
        Raises ValueError if format is invalid.
        """
        if len(data) < 4:
            raise ValueError("Data too short for header length")
            
        header_len = struct.unpack(">I", data[:4])[0]
        
        if len(data) < 4 + header_len:
            raise ValueError("Data too short for headers")
            
        metadata_bytes = data[4 : 4 + header_len]
        body_bytes = data[4 + header_len :]
        
        ws_msg = cls.model_validate_json(metadata_bytes)
        return ws_msg, body_bytes
