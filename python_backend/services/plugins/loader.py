
import os
import sys
import logging
import importlib.util
from typing import Optional, Type, Any
from pathlib import Path
from core.manifest import PluginManifest
from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger("PluginLoader")

class PluginLoader:
    """
    Handles dynamic importing of plugin modules.
    """
    
    def load_plugin_class(self, manifest: PluginManifest) -> Optional[BaseSystemPlugin]:
        """
        Import the module and instantiate the plugin class.
        Returns the INITIALIZED instance.
        """
        if getattr(manifest, "isolation_mode", "local") == "process":
            try:
                from core.isolation.proxy import RemotePluginProxy
                # Path needs to be string for pickling/compat
                manifest_data = manifest.dict() if hasattr(manifest, 'dict') else vars(manifest)
                return RemotePluginProxy(manifest_data, str(manifest.path) + "/manifest.yaml")
            except Exception as e:
                logger.error(f"Failed to create RemotePluginProxy for {manifest.id}: {e}")
                return None

        if not hasattr(manifest, 'path') or not manifest.path:
            logger.error(f"Manifest for {manifest.id} has no path.")
            return None

        plugin_dir = Path(manifest.path)
        
        # Resolve entry file
        if hasattr(manifest, 'entrypoint') and ':' in manifest.entrypoint:
            mod_name = manifest.entrypoint.split(":")[0]
            entry_file = plugin_dir / f"{mod_name}.py"
            # Fallback for packages
            if not entry_file.exists() and (plugin_dir / mod_name / "__init__.py").exists():
                 entry_file = plugin_dir / mod_name / "__init__.py"
        else:
             # Fallback/Legacy field
             entry_file = plugin_dir / getattr(manifest, 'entry', 'main.py')
        
        if not entry_file.exists():
            logger.error(f"Entry file missing for {manifest.id}: {entry_file}")
            return None

        module_name = f"plugins.system.{manifest.id}"
        
        try:
            # 1. Add to sys.path if needed (optional if structure is standard)
            # but usually good to ensure sub-imports work
            sys.path.insert(0, str(plugin_dir))
            
            # 2. Spec & Module
            spec = importlib.util.spec_from_file_location(module_name, entry_file)
            if not spec or not spec.loader:
                logger.error(f"Failed to create import spec for {manifest.id}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 3. Find Class
            # Look for a class that inherits from BaseSystemPlugin
            plugin_cls = None
            for name, obj in vars(module).items():
                if isinstance(obj, type) and issubclass(obj, BaseSystemPlugin) and obj is not BaseSystemPlugin:
                    plugin_cls = obj
                    break
            
            if not plugin_cls:
                logger.error(f"No BaseSystemPlugin subclass found in {entry_file}")
                return None
                
            # 4. Instantiate (No DI here yet, usually container passed later or in init)
            # Assuming BaseSystemPlugin __init__ takes manifest? or just empty?
            # Existing specific code suggests it might be simple.
            # We'll instantiate and let the Manager handle DI injection if needed.
            instance = plugin_cls()
            instance.manifest = manifest 
            instance.id = manifest.id # Ensure ID matches
            
            return instance

        except Exception as e:
            logger.error(f"Failed to load plugin {manifest.id}: {e}", exc_info=True)
            return None
        finally:
            if str(plugin_dir) in sys.path:
                sys.path.remove(str(plugin_dir))
