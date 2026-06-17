"""
Lumina Capability Permission System
Security & Sandboxing

Defines standardized permissions that capability modules can request.
"""

from enum import Enum
from typing import List, Set


class Permission(str, Enum):
    """
    Standard permission types for Lumina capability modules.
    
    Modules must declare required permissions in their manifest.yaml:
    
    permissions:
      - filesystem.data_read
      - network.external
    """
    
    # File System Access
    FILESYSTEM_DATA_READ = "filesystem.data_read"    # Read files from plugin data directory
    FILESYSTEM_DATA_WRITE = "filesystem.data_write"  # Write files to plugin data directory
    FILESYSTEM_EXTERNAL = "filesystem.external"  # Access files outside plugin directory
    FILESYSTEM_ASSETS = "filesystem.read_assets" # Read own assets [Mapped from filesystem:read_assets]
    FILESYSTEM_USER = "filesystem.read_user"     # Read user documents [Mapped from filesystem:read_user]
    FILESYSTEM_SYSTEM = "filesystem.write_system" # Write to system folders [Mapped from filesystem:write_system]
    
    # Network Access
    NETWORK_LISTEN = "network.listen"         # Listen on network ports
    NETWORK_INTERNAL = "network.lumina_internal" # Access internal Lumina APIs [Mapped from network:lumina_internal]
    NETWORK_EXTERNAL = "network.external"        # Access public internet [Mapped from network:external]
    
    # OS / Input
    OS_PROCESS = "os.process"             # Read process list [Mapped from os:process]
    OS_EXEC = "os.exec"                   # Execute system commands [Mapped from os:exec]
    INPUT_SIMULATE = "input.simulate"     # Simulate Keyboard/Mouse [Mapped from input:simulate]

    # Memory System
    MEMORY_READ = "memory.read"               # Read from memory system
    MEMORY_WRITE = "memory.write"             # Write to memory system
    DATABASE_POSTGRES = "database.postgres"   # Access configured Postgres backend
    
    # LLM Access
    LLM_INVOKE = "llm.invoke"                 # Invoke LLM API calls
    
    # Time-based Events
    TICKER_SUBSCRIBE = "ticker.subscribe"     # Subscribe to tick events
    
    # Capability Interaction
    CAPABILITY_DISCOVERY = "capability.discovery"
    
    # System Events
    EVENT_SUBSCRIBE = "event.subscribe"       # Subscribe to system events
    EVENT_EMIT = "event.emit"                 # Emit custom events

    # Network Extras
    NETWORK_UDP = "network.udp"               # UDP Socket access

    # Soul/Character Access
    SOUL_MODIFY = "soul.modify"           # Modify character personality/mood


# --- Permission Tiers (SSOT) ---

TIER_SAFE: Set[str] = {
    Permission.NETWORK_INTERNAL.value,
    Permission.FILESYSTEM_DATA_READ.value,
    Permission.FILESYSTEM_DATA_WRITE.value,
    Permission.FILESYSTEM_ASSETS.value,
    Permission.EVENT_SUBSCRIBE.value,
    Permission.EVENT_EMIT.value,
    Permission.CAPABILITY_DISCOVERY.value,
}

TIER_TRUSTED: Set[str] = {
    Permission.NETWORK_EXTERNAL.value,
    Permission.DATABASE_POSTGRES.value,
    Permission.FILESYSTEM_USER.value,
    Permission.NETWORK_UDP.value,
}

TIER_SYSTEM: Set[str] = {
    Permission.OS_PROCESS.value,
    Permission.OS_EXEC.value,
    Permission.FILESYSTEM_SYSTEM.value,
    Permission.INPUT_SIMULATE.value,
    Permission.FILESYSTEM_EXTERNAL.value,
    Permission.NETWORK_LISTEN.value,
}

# Default permissions granted to all modules (Alias to SAFE)
DEFAULT_PERMISSIONS: Set[str] = TIER_SAFE

# Dangerous permissions that require explicit user approval (Union of TRUSTED and SYSTEM)
DANGEROUS_PERMISSIONS: Set[str] = TIER_TRUSTED | TIER_SYSTEM


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
