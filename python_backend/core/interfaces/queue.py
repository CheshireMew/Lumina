"""
Job Queue Interface
===================
Defines the contract for asynchronous task processing.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import contextvars
from typing import Generic, TypeVar, Optional, Any, Dict

# Late import or direct import if safe. logger_setup has no heavy deps.
try:
    from logger_setup import request_id_ctx, session_id_ctx
except ImportError:
    # Fallback mocks if logger_setup not available
    request_id_ctx = contextvars.ContextVar("request_id", default="-")
    session_id_ctx = contextvars.ContextVar("session_id", default="-")

@dataclass(order=True)
class Job:
    priority: int
    id: str = field(compare=False)
    type: str = field(compare=False)
    payload: Any = field(compare=False)
    created_at: float = field(compare=False, default_factory=lambda: datetime.now().timestamp())
    trace_context: Dict[str, str] = field(compare=False, default_factory=dict)
    
    @staticmethod
    def create(type: str, payload: Any, priority: int = 10, request_id: str = None) -> "Job":
        ctx = {
            "request_id": request_id or request_id_ctx.get(),
            "session_id": session_id_ctx.get()
        }
        return Job(priority, str(uuid.uuid4()), type, payload, trace_context=ctx)

class IJobQueue(ABC):
    """Generic Job Queue Interface."""
    
    @abstractmethod
    async def enqueue(self, job: Job) -> bool:
        """Add job to queue."""
        pass
    
    @abstractmethod
    async def dequeue(self) -> Optional[Job]:
        """Get next job. Waits if empty."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Current queue size."""
        pass
