import os
import re
from pathlib import Path
from typing import Union, Optional

class SecurityException(Exception):
    """Raised when a security violation is detected (Path Traversal, etc.)"""
    pass

class SafePath:
    """
    [Architecture 11.0] Unified File System Security Guard.
    
    Prevents Path Traversal and File Inclusion vulnerabilities by enforcing
    strict containment checks.
    """

    @staticmethod
    def resolve_child(base: Union[str, Path], *user_paths: str) -> Path:
        """
        Safely resolves a child path relative to a base directory.
        
        Args:
            base: The trusted root directory (e.g. plugin_dir, data_dir)
            *user_paths: Potentially untrusted path components provided by user/api
            
        Returns:
            Resolved absolute Path object
            
        Raises:
            SecurityException: If the resolved path escapes the base directory.
        """
        try:
            base_path = Path(base).resolve()
            # Join all components
            target_path = base_path.joinpath(*user_paths).resolve()
            
            # Enforce Containment
            if not SafePath._is_relative_to(target_path, base_path):
                raise SecurityException(f"Path Traversal Detected: '{target_path}' is not inside '{base_path}'")
                
            return target_path
            
        except Exception as e:
            if isinstance(e, SecurityException):
                raise
            raise SecurityException(f"Path Resolution Error: {str(e)}")

    @staticmethod
    def validate_filename(filename: str, allow_unicode: bool = True) -> str:
        """
        Validates a filename (basename only, no directory separators).
        
        Args:
            filename: The filename to check
            allow_unicode: If True, allows non-ascii characters (Japanese, etc.)
            
        Returns:
            The valid filename
            
        Raises:
            SecurityException: If filename contains illegal characters or path separators.
        """
        if not filename or len(filename) > 255:
            raise SecurityException("Invalid filename length")
            
        # 1. Block Path Separators
        if os.sep in filename or (os.altsep and os.altsep in filename):
             raise SecurityException(f"Filename cannot contain path separators: {filename}")
        
        # 2. Block Control Characters (Null byte, etc)
        if any(ord(c) < 31 for c in filename):
             raise SecurityException("Filename contains control characters")
             
        # 3. Block ".." and "."
        if filename in (".", ".."):
             raise SecurityException("Filename cannot be '.' or '..'")
             
        # 4. Regex Validation (Optional but recommended)
        # Windows forbidden chars: < > : " / \ | ? *
        if re.search(r'[<>:"/\\|?*]', filename):
             raise SecurityException(f"Filename contains illegal characters: {filename}")
             
        return filename

    @staticmethod
    def _is_relative_to(child: Path, parent: Path) -> bool:
        """
        Polyfill for check if child is inside parent.
        Uses pathlib.relative_to if available (Python 3.9+), else manual check.
        """
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False
