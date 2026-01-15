
import os
import logging
import yaml
from pathlib import Path
from typing import List, Optional
from core.manifest import PluginManifest

logger = logging.getLogger("PluginDiscovery")

class PluginScanner:
    """
    Scans the file system for plugin manifests.
    """
    def __init__(self, plugins_root: Path):
        self.root = plugins_root

    def scan(self) -> List[PluginManifest]:
        """
        Scan for unique plugins (manifest.yaml).
        Returns a list of loaded PluginManifest objects.
        """
        discovered = []
        
        if not self.root.exists():
            logger.warning(f"Plugins root not found: {self.root}")
            return []

        for item in self.root.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                manifest_path = item / "manifest.yaml"
                if manifest_path.exists():
                    try:
                        manifest = self._load_manifest(manifest_path)
                        if manifest:
                            # Attach path for loader use
                            manifest.path = str(item) 
                            discovered.append(manifest)
                    except Exception as e:
                        logger.error(f"Failed to load manifest at {manifest_path}: {e}")
                else:
                    # Legacy support: No manifest, but is directory with code?
                    if (item / "__init__.py").exists() or (item / "main.py").exists():
                         # Create synthetic manifest
                         logger.info(f"Detected Legacy Plugin (No Manifest): {item.name}")
                         try:
                             # Determine entry
                             if (item / "main.py").exists(): e_point = "main:Legacy"
                             else: e_point = "__init__:Legacy"
                             
                             manifest = PluginManifest(
                                 id=item.name,
                                 version="0.0.0",
                                 name=item.name,
                                 entrypoint=e_point,
                                 dependencies=[],  # Legacy assumed no deps
                                 path=str(item)
                             )
                             discovered.append(manifest)
                         except Exception as e:
                             logger.warning(f"Failed to create synthetic manifest for {item.name}: {e}")
            
            elif item.is_file() and item.suffix == ".py":
                # Legacy single-file plugin
                try:
                     logger.info(f"Detected Legacy Single-File Plugin: {item.stem}")
                     manifest = PluginManifest(
                         id=item.stem,
                         version="0.0.0",
                         name=item.stem,
                         entrypoint=f"{item.stem}:Legacy",
                         dependencies=[],
                         path=str(self.root) 
                     )
                     discovered.append(manifest)
                except Exception as e:
                     logger.warning(f"Failed to create synthetic manifest for {item.name}: {e}")
                    
        return discovered

    def _load_manifest(self, path: Path) -> Optional[PluginManifest]:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        # Basic validation or Pydantic parsing
        # Assuming PluginManifest is a Pydantic model or dataclass
        # that roughly matches the dict structure
        try:
            return PluginManifest(**data)
        except Exception as e:
            logger.error(f"Invalid manifest format at {path}: {e}")
            return None
