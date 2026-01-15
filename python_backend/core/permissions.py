"""
Lumina Plugin Permission System
Security & Sandboxing

Defines standardized permissions that plugins can request.
"""

from enum import Enum
from typing import List, Set


class Permission(str, Enum):
    """
    Standard permission types for Lumina plugins.
    
    Plugins must declare required permissions in their manifest.yaml:
    
    permissions:
      - filesystem.read
      - network.outbound
    """
    
    # File System Access
    FILESYSTEM_READ = "filesystem.read"       # Read files from plugin data directory
    FILESYSTEM_WRITE = "filesystem.write"     # Write files to plugin data directory
    FILESYSTEM_EXTERNAL = "filesystem.external"  # Access files outside plugin directory
    
    # Network Access
    NETWORK_OUTBOUND = "network.outbound"     # Make outbound HTTP/WebSocket requests
    NETWORK_LISTEN = "network.listen"         # Listen on network ports
    
    # Memory System
    MEMORY_READ = "memory.read"               # Read from memory system (SurrealDB)
    MEMORY_WRITE = "memory.write"             # Write to memory system
    
    # LLM Access
    LLM_INVOKE = "llm.invoke"                 # Invoke LLM API calls
    
    # Time-based Events
    TICKER_SUBSCRIBE = "ticker.subscribe"     # Subscribe to tick events
    
    # Plugin Interaction
    PLUGIN_DISCOVERY = "plugin.discovery"     # Discover and interact with other plugins
    
    # System Events
    EVENT_SUBSCRIBE = "event.subscribe"       # Subscribe to system events
    EVENT_EMIT = "event.emit"                 # Emit custom events

    # System Interactions
    SYSTEM_NOTIFICATION = "system.notification" # Send user notifications

    # Soul/Character Access
    SOUL_MODIFY = "soul.modify"           # Modify character personality/mood


# Default permissions granted to all plugins
DEFAULT_PERMISSIONS: Set[str] = {
    Permission.EVENT_SUBSCRIBE,
    Permission.EVENT_EMIT,
    Permission.PLUGIN_DISCOVERY,
}

# Dangerous permissions that require explicit user approval
DANGEROUS_PERMISSIONS: Set[str] = {
    Permission.FILESYSTEM_EXTERNAL,
    Permission.NETWORK_OUTBOUND,
    Permission.NETWORK_LISTEN,
}


def validate_permissions(requested: List[str]) -> List[str]:
    """
    Validate a list of permission strings.
    
    Returns list of invalid permission strings.
    """
    valid_perms = {p.value for p in Permission}
    invalid = [p for p in requested if p not in valid_perms]
    return invalid


def has_dangerous_permissions(requested: List[str]) -> bool:
    """Check if any requested permissions are dangerous."""
    return bool(set(requested) & DANGEROUS_PERMISSIONS)
