
import logging
from typing import List, Dict, Tuple, Set
from core.manifest import PluginManifest

logger = logging.getLogger("PluginDeps")

class DependencySorter:
    """
    Sorts plugins based on dependencies using Topological Sort.
    """
    def __init__(self, manifests: List[PluginManifest]):
        self.manifests = manifests

    def sort(self) -> List[PluginManifest]:
        """
        Returns a sorted list of manifests (dependencies first).
        """
        # Map ID -> Manifest
        plugin_map = {m.id: m for m in self.manifests}
        in_degree = {m.id: 0 for m in self.manifests}
        dependents = {m.id: [] for m in self.manifests}
        
        # Build Graph
        for m in self.manifests:
            deps = getattr(m, 'dependencies', []) or []
            for dep_id in deps:
                if dep_id in plugin_map:
                    in_degree[m.id] += 1
                    dependents[dep_id].append(m.id)
                else:
                    logger.warning(f"Plugin '{m.id}' depends on missing plugin '{dep_id}'")

        # Kahn's Algorithm
        queue = [pid for pid, d in in_degree.items() if d == 0]
        result = []
        
        while queue:
            pid = queue.pop(0)
            result.append(plugin_map[pid])
            
            for dep_id in dependents[pid]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)
                    
        # Cycle Detection
        if len(result) != len(self.manifests):
            loaded_ids = {m.id for m in result}
            all_ids = {m.id for m in self.manifests}
            missing = all_ids - loaded_ids
            raise ValueError(f"Circular dependency detected involving: {missing}")
            
        return result
