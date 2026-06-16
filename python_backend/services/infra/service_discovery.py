
import logging
import time
from typing import Dict, List, Optional
from pydantic import BaseModel

from core.runtime import (
    MAIN_RUNTIME_TARGET,
    normalize_runtime_target,
    runtime_target_for_capability,
)

logger = logging.getLogger("ServiceDiscovery")

class WorkerNode(BaseModel):
    id: str
    host: str
    port: int
    runtime_target: str = MAIN_RUNTIME_TARGET
    capabilities: List[str] = []
    last_seen: float = 0.0

    @property
    def base_url(self) -> str:
        # Standardize URL construction
        return f"http://{self.host}:{self.port}"

class ServiceDiscovery:
    """
    [Architecture 5.2] Dynamic Service Registry.
    Tracks distributed worker locations and capabilities.
    """
    _instance = None

    def __init__(self):
        self.nodes: Dict[str, WorkerNode] = {}
        self.ttl = 30 # Seconds until a node is considered stale

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ServiceDiscovery()
        return cls._instance

    def register(self, worker_id: str, host: str, port: int, capabilities: List[str] = None, runtime_target: str = None):
        """Register or update a worker node."""
        normalized_target = normalize_runtime_target(runtime_target or worker_id)
        node = WorkerNode(
            id=worker_id,
            host=host,
            port=port,
            runtime_target=normalized_target,
            capabilities=capabilities or [],
            last_seen=time.time()
        )
        self.nodes[worker_id] = node
        logger.info(f"🛰️ Registered worker: {worker_id} at {node.base_url} (Caps: {node.capabilities})")

    def get_node(self, worker_id: str) -> Optional[WorkerNode]:
        """Get node by ID, pruning if stale."""
        node = self.nodes.get(worker_id)
        if node and (time.time() - node.last_seen) > self.ttl:
            logger.warning(f"👻 Worker {worker_id} is stale. Removing.")
            del self.nodes[worker_id]
            return None
        return node

    def get_url(self, worker_id: str) -> str:
        """Resolve a URL for a registered worker node."""
        normalized_target = normalize_runtime_target(worker_id)
        node = self.get_node(worker_id)
        if node:
            return node.base_url

        for candidate in self.nodes.values():
            if normalize_runtime_target(candidate.runtime_target) == normalized_target:
                return candidate.base_url

        raise ValueError(f"Worker {worker_id} is not registered in service discovery")

    def get_url_for_capability(self, capability: str) -> str:
        runtime_target = runtime_target_for_capability(capability)
        return self.get_url(runtime_target)

    def find_by_capability(self, capability: str) -> List[WorkerNode]:
        """Find all nodes providing a specific capability."""
        matches = []
        now = time.time()
        for wid, node in list(self.nodes.items()):
            if (now - node.last_seen) > self.ttl:
                del self.nodes[wid]
                continue
            if capability in node.capabilities:
                matches.append(node)
        return matches

# Global singleton
discovery = ServiceDiscovery.get_instance()
