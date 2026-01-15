"""
Example Plugin Manager
Template for creating Lumina plugins.

Copy this directory and modify to create your own plugin.
"""

import logging
from typing import Any
from plugins.base import BaseSystemPlugin

logger = logging.getLogger("ExamplePlugin")


class ExampleManager(BaseSystemPlugin):
    """
    Example plugin demonstrating Lumina plugin architecture.
    
    Plugins receive a LuminaContext (or SandboxedContext) in initialize().
    Use context.bus to subscribe to events and register services.
    """
    
    @property
    def id(self) -> str:
        return "lumina.example_plugin"
    
    @property
    def name(self) -> str:
        return "Example Plugin"
    
    @property
    def description(self) -> str:
        return "A template plugin for demonstration."
    
    @property
    def enabled(self) -> bool:
        # You can load this from saved data or config
        return False  # Disabled by default
    
    def initialize(self, context: Any):
        """
        Called when the plugin is loaded.
        
        Args:
            context: LuminaContext or SandboxedContext instance
        """
        super().initialize(context)
        
        # Store context for later use
        self.context = context
        
        # Subscribe to events via EventBus
        context.bus.subscribe("system.tick", self._on_tick)
        context.bus.subscribe("plugin.*", self._on_plugin_event)
        
        # Register this plugin as a service for other plugins to discover
        context.register_service("example_service", self)
        
        # Load saved data (persisted JSON)
        saved_data = self.load_data()
        self.counter = saved_data.get("counter", 0)
        
        logger.info(f"鉁?{self.name} initialized (counter: {self.counter})")
    
    def _on_tick(self, event):
        """Called every second by the global ticker."""
        # Example: increment counter every tick
        self.counter += 1
        
        # Save periodically (every 60 ticks)
        if self.counter % 60 == 0:
            self.save_data({"counter": self.counter})
            logger.debug(f"Saved counter: {self.counter}")
    
    def _on_plugin_event(self, event):
        """Called for any event matching 'plugin.*'."""
        logger.debug(f"Received plugin event: {event.type}")
    
    def start(self):
        """Called when the plugin is enabled."""
        logger.info(f"鈻讹笍 {self.name} started")
    
    def stop(self):
        """Called when the plugin is disabled."""
        logger.info(f"鈴癸笍 {self.name} stopped")
    
    # --- Public API for other plugins ---
    
    def get_counter(self) -> int:
        """Example API method that other plugins can call."""
        return self.counter
    
    def reset_counter(self):
        """Reset the counter to zero."""
        self.counter = 0
        self.save_data({"counter": 0})
