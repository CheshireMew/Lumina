from core.interfaces.plugin import BaseSystemPlugin

class RemotePluginStub(BaseSystemPlugin):
    """
    [Architecture 2.0] Unified Remote Stub
    Used for plugins running in Worker Processes (STT/TTS).
    It serves as a placeholder in the Main Process Registry.
    """
    def __init__(self, manifest):
        self._manifest = manifest

    # [Architecture 4.1] Satisfy ABC
    @property
    def id(self): return self._manifest.id
    @property
    def name(self): return self._manifest.name
    
    # [Architecture 4.1] Dynamic Proxy
    # Automatically forwards category, group_id, etc. from manifest
    def __getattr__(self, name):
        return getattr(self._manifest, name)
    
    def initialize(self, context): 
        pass # No-op (Logic runs in Worker)

    def get_status(self):
        """
        [Scheme C] Remote Stubs are passive. 
        Truth comes from Worker Registry Reports.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": getattr(self, 'description', ''),
            "version": getattr(self, 'version', '0.0.0'),
            "enabled": False, # Registry override handles true state
            "status": "remote_managed",
            "runtime_target": getattr(self, 'runtime_target', 'unknown'),
            # [Fix] Proxy metadata for UI filtering
            "category": getattr(self, 'category', 'system'),
            "group_id": getattr(self, 'group_id', None),
            "group_exclusive": getattr(self, 'group_exclusive', False),
            "func_tag": getattr(self, 'func_tag', None),
            "tags": getattr(self, 'tags', [])
        }
