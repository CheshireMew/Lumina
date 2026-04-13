"""
SDK Bootstrapper
================

Initializes Lumina SDK during system startup.
Plugin loading is handled by SystemPluginManager as the single source of truth.
"""

import logging
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.SDK")


class SDKBootstrapper(Bootstrapper):
    """SDK Initialization Bootstrapper"""
    
    @property
    def name(self) -> str:
        return "Lumina SDK"
    
    async def bootstrap(self, container):
        """Initialize SDK globals for plugins and services."""
        
        try:
            from lumina import lumina
            lumina._initialize(container)
            logger.info("✅ Lumina SDK Initialized")
        except Exception as e:
            logger.error(f"❌ SDK Initialization Failed: {e}")
            raise
