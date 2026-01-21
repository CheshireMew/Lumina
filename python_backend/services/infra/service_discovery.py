
import logging
import time
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("ServiceDiscovery")

class WorkerNode(BaseModel):
    id: str
    host: str
    port: int
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

    def register(self, worker_id: str, host: str, port: int, capabilities: List[str] = []):
        """Register or update a worker node."""
        node = WorkerNode(
            id=worker_id,
            host=host,
            port=port,
            capabilities=capabilities,
            last_seen=time.time()
        )
        self.nodes[worker_id] = node
        logger.info(f"🛰️ Registered worker: {worker_id} at {node.base_url} (Caps: {capabilities})")

    def get_node(self, worker_id: str) -> Optional[WorkerNode]:
        """Get node by ID, pruning if stale."""
        node = self.nodes.get(worker_id)
        if node and (time.time() - node.last_seen) > self.ttl:
            logger.warning(f"👻 Worker {worker_id} is stale. Removing.")
            del self.nodes[worker_id]
            return None
        return node

    def get_url(self, worker_id: str, fallback_port: int = None) -> str:
        """Resolve worker URL with local fallback."""
        node = self.get_node(worker_id)
        if node:
            return node.base_url
        
        # Fallback to localhost if not registered
        if fallback_port:
             return f"http://127.0.0.1:{fallback_port}"
        
        raise ValueError(f"Worker {worker_id} not discovered and no fallback provided")

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
