
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
        # 1. Headless Check (Resource/Driver Packs)
        if not manifest.entrypoint or manifest.entrypoint.lower() == "none":
            return None

        # 2. Isolation Check
        isolation_mode = getattr(manifest, "isolation_mode", "local")
        if isolation_mode == "process":
            try:
                from core.isolation.proxy import RemotePluginProxy
                # Path needs to be string for pickling/compat
                if hasattr(manifest, 'dict'):
                     manifest_data = manifest.dict() 
                else: 
                     manifest_data = vars(manifest)
                
                # Create Proxy
                instance = RemotePluginProxy(manifest_data)
                return instance
            except Exception as e:
                logger.error(f"Failed to create RemotePluginProxy for {manifest.id}: {e}")
                return None

        # 3. Local Load
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

        # Determine correct module prefix based on file location
        # If in 'extensions', verify path exists.
        
        safe_id = manifest.id.replace("system.", "").replace("extensions.", "") # Normalize
        
        if "extensions" in str(plugin_dir):
             prefix = "plugins.extensions"
        else:
             prefix = "plugins.system"
             
        module_name = f"{prefix}.{safe_id}.{entry_file.stem}"
        
        try:
            # 1. Spec & Module
            # ensure 'plugins' is in path (it is), so we don't need to add plugin_dir to sys.path
            # If we add plugin_dir to sys.path, imports like 'import utils' work, but absolute imports 'plugins.system.x' might break if names collide.
            # Local imports 'from . import x' rely on __package__.
            
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
            # We'll instantiate and let the Manager handle DI injection if needed.
            instance = plugin_cls()
            instance.manifest = manifest 
            
            # Only set ID if valid (and not a property preventing set)
            try:
                if getattr(instance, 'id', None) != manifest.id:
                     # Warn if mismatch, but don't force if it's read-only
                     # logger.warning(f"Plugin ID mismatch: Instance says '{instance.id}', Manifest says '{manifest.id}'")
                     # instance.id = manifest.id 
                     pass
            except AttributeError:
                pass # Read-only property
            
            return instance

        except SyntaxError as e:
             logger.error(f"❌ Syntax Error in plugin {manifest.id} (File: {entry_file}): {e}")
             return None
        except ImportError as e:
             logger.error(f"❌ Import Error in plugin {manifest.id}: {e}")
             return None
        except AttributeError as e:
             logger.error(f"❌ Plugin Class Error in {manifest.id}: Missing BaseSystemPlugin subclass or attribute? ({e})")
             return None
        except Exception as e:
            logger.critical(f"🔥 Unexpected Crash loading plugin {manifest.id}: {e}", exc_info=True)
            return None
        finally:
            pass
