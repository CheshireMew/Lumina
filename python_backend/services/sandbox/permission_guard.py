"""
Permission Guard.
Fine-grained permission checking for sandboxed plugins.
"""

import os
import re
import logging
from typing import Set, List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger("PermissionGuard")


class Permission(Enum):
    """Standard permission types for plugins."""
    
    # Filesystem
    FILESYSTEM_DATA_READ = "filesystem.data_read"
    FILESYSTEM_DATA_WRITE = "filesystem.data_write"
    FILESYSTEM_EXECUTE = "filesystem.execute"
    
    # Network
    NETWORK_EXTERNAL = "network.external"
    NETWORK_LISTEN = "network.listen"
    NETWORK_LOCAL_ONLY = "network.local_only"
    
    # Process
    SUBPROCESS_SPAWN = "subprocess.spawn"
    SUBPROCESS_SHELL = "subprocess.shell"
    
    # System
    SYSTEM_ENV_READ = "system.env.read"
    SYSTEM_ENV_WRITE = "system.env.write"
    
    # IPC
    IPC_EVENT_BUS = "ipc.event_bus"
    IPC_CONTAINER = "ipc.container"
    
    # Data
    DATA_USER_MEMORY = "data.user_memory"
    DATA_PLUGIN_STATE = "data.plugin_state"


@dataclass
class PluginPermissions:
    """
    Permission configuration for a plugin.
    Parsed from plugin manifest.yaml permissions section.
    """
    allowed: Set[str] = field(default_factory=set)
    
    # Scoped permissions
    filesystem_paths: Set[str] = field(default_factory=set)  # Allowed paths for write
    network_hosts: Set[str] = field(default_factory=set)     # Allowed hosts for outbound
    network_ports: Set[int] = field(default_factory=set)     # Allowed ports to listen on
    env_vars: Set[str] = field(default_factory=set)          # Allowed env vars to read
    
    @classmethod
    def from_manifest(cls, permissions: List[str]) -> "PluginPermissions":
        """
        Parse permissions from manifest format.
        
        Examples:
            - "filesystem.data_read" -> basic permission
            - "filesystem.data_write:plugins/{id}/data" -> scoped to path
            - "network.external:api.example.com" -> scoped to host
            - "resource.memory:512mb" -> resource limit (handled separately)
        """
        result = cls()
        
        for perm in permissions:
            if ":" in perm:
                base, scope = perm.split(":", 1)
                result.allowed.add(base)
                
                # Parse scoped permissions
                if base == "filesystem.data_write":
                    result.filesystem_paths.add(scope)
                elif base == "network.external":
                    result.network_hosts.add(scope)
                elif base == "network.listen":
                    try:
                        result.network_ports.add(int(scope))
                    except ValueError:
                        pass
                elif base == "system.env.read":
                    result.env_vars.add(scope)
            else:
                result.allowed.add(perm)
        
        return result
    
    def has_permission(self, permission: str) -> bool:
        """Check if a basic permission is granted."""
        return permission in self.allowed


class PermissionGuard:
    """
    Guards access to protected resources based on plugin permissions.
    
    Usage:
        guard = PermissionGuard(plugin_permissions)
        
        if guard.check_filesystem("/path/to/file", write=True):
            # Allowed
        else:
            raise PermissionError("Write access denied")
    """
    
    def __init__(self, permissions: PluginPermissions, plugin_id: str = None):
        self.permissions = permissions
        self.plugin_id = plugin_id or "unknown"
        
        # Allowed base paths for all plugins (read-only)
        self._safe_read_paths = {
            Path("plugins").resolve(),      # Plugin assets
            Path("public").resolve(),       # Public assets
            Path("data/models").resolve(),  # ML models
        }
        
        # Paths always denied (even with permissions)
        self._blacklisted_paths = {
            Path(".git"),
            Path(".env"),
            Path("config/secrets"),
        }
        
        # Blacklisted network hosts
        self._blacklisted_hosts = {
            "localhost",
            "127.0.0.1",
            "::1",
            "0.0.0.0",
            # Cloud metadata endpoints
            "169.254.169.254",
            "metadata.google.internal",
        }
    
    # ================================================================
    # Filesystem Checks
    # ================================================================
    
    def check_filesystem(self, path: str, write: bool = False) -> bool:
        """
        Check if filesystem access is allowed.
        
        Args:
            path: Path to check
            write: True for write access, False for read
            
        Returns:
            True if access is allowed
        """
        try:
            target = Path(path).resolve()
        except Exception:
            return False
        
        # Always deny blacklisted paths
        for bp in self._blacklisted_paths:
            if bp in target.parts or str(bp) in str(target):
                logger.warning(f"🚫 Denied access to blacklisted path: {path}")
                return False
        
        if write:
            # Need explicit write permission
            if not self.permissions.has_permission(Permission.FILESYSTEM_DATA_WRITE.value):
                return False
            
            # Check scoped paths
            if self.permissions.filesystem_paths:
                for allowed in self.permissions.filesystem_paths:
                    # Expand {id} placeholder
                    allowed_path = allowed.replace("{id}", self.plugin_id)
                    try:
                        allowed_resolved = Path(allowed_path).resolve()
                        if target == allowed_resolved or allowed_resolved in target.parents:
                            return True
                    except Exception:
                        continue
                return False
            
            # If no scoped paths, allow only plugin data directory
            plugin_data = Path(f"plugins/{self.plugin_id}/data").resolve()
            return target == plugin_data or plugin_data in target.parents
        
        else:
            # Read access
            if not self.permissions.has_permission(Permission.FILESYSTEM_DATA_READ.value):
                # Check if in safe read paths
                for safe in self._safe_read_paths:
                    if target == safe or safe in target.parents:
                        return True
                return False
            
            return True
    
    # ================================================================
    # Network Checks
    # ================================================================
    
    def check_network_outbound(self, host: str, port: int = None) -> bool:
        """
        Check if outbound network access is allowed.
        
        Args:
            host: Target hostname or IP
            port: Target port (optional)
            
        Returns:
            True if access is allowed
        """
        # Check basic permission
        if not self.permissions.has_permission(Permission.NETWORK_EXTERNAL.value):
            return False
        
        # Always deny blacklisted hosts
        host_lower = host.lower()
        for bh in self._blacklisted_hosts:
            if bh in host_lower:
                logger.warning(f"🚫 Denied network access to blacklisted host: {host}")
                return False
        
        # Check scoped hosts
        if self.permissions.network_hosts:
            for allowed in self.permissions.network_hosts:
                # Support wildcard: *.example.com
                if allowed.startswith("*."):
                    domain = allowed[2:]
                    if host_lower.endswith(domain):
                        return True
                elif allowed == host_lower or allowed == "*":
                    return True
            return False
        
        # No scope = all non-blacklisted hosts allowed
        return True
    
    def check_network_listen(self, port: int) -> bool:
        """Check if listening on a port is allowed."""
        if not self.permissions.has_permission(Permission.NETWORK_LISTEN.value):
            return False
        
        # Deny privileged ports
        if port < 1024:
            return False
        
        # Check scoped ports
        if self.permissions.network_ports:
            return port in self.permissions.network_ports
        
        # Allow high ports by default
        return port > 10000
    
    # ================================================================
    # Subprocess Checks
    # ================================================================
    
    def check_subprocess(self, command: str, use_shell: bool = False) -> bool:
        """
        Check if spawning a subprocess is allowed.
        
        Args:
            command: Command to execute
            use_shell: True if using shell=True
        """
        if use_shell:
            if not self.permissions.has_permission(Permission.SUBPROCESS_SHELL.value):
                return False
        else:
            if not self.permissions.has_permission(Permission.SUBPROCESS_SPAWN.value):
                return False
        
        # Additional safety: deny dangerous commands
        dangerous = ["rm", "del", "format", "mkfs", "dd", "shutdown", "reboot"]
        cmd_lower = command.lower()
        for d in dangerous:
            if d in cmd_lower.split():
                logger.warning(f"🚫 Denied dangerous command: {command}")
                return False
        
        return True
    
    # ================================================================
    # Environment Checks
    # ================================================================
    
    def check_env_read(self, var_name: str) -> bool:
        """Check if reading an environment variable is allowed."""
        if not self.permissions.has_permission(Permission.SYSTEM_ENV_READ.value):
            return False
        
        # Deny sensitive env vars
        sensitive = {"API_KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL"}
        var_upper = var_name.upper()
        for s in sensitive:
            if s in var_upper:
                logger.warning(f"🚫 Denied access to sensitive env var: {var_name}")
                return False
        
        # Check scoped vars
        if self.permissions.env_vars:
            return var_name in self.permissions.env_vars or var_name.upper() in self.permissions.env_vars
        
        return True
    
    # ================================================================
    # IPC Checks
    # ================================================================
    
    def check_ipc_event_bus(self, event_type: str) -> bool:
        """Check if accessing event bus is allowed."""
        return self.permissions.has_permission(Permission.IPC_EVENT_BUS.value)
    
    def check_ipc_container(self, service_name: str) -> bool:
        """Check if accessing service container is allowed."""
        return self.permissions.has_permission(Permission.IPC_CONTAINER.value)


# Convenience function
def create_guard_from_manifest(manifest: Dict[str, Any], plugin_id: str) -> PermissionGuard:
    """
    Create a PermissionGuard from a plugin manifest.
    
    Args:
        manifest: Parsed manifest dict
        plugin_id: Plugin identifier
        
    Returns:
        Configured PermissionGuard
    """
    perms_list = manifest.get("permissions", [])
    if isinstance(perms_list, list):
        permissions = PluginPermissions.from_manifest(perms_list)
    else:
        permissions = PluginPermissions()
    
    return PermissionGuard(permissions, plugin_id)
