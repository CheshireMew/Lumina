from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkerRuntimeOptions:
    capability: str
    host: str = "127.0.0.1"
    port: Optional[int] = None
    runtime_target: Optional[str] = None
