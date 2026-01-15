"""
DEPRECATED: Use core.interfaces.plugin instead.
This module is kept for backward compatibility and will be removed in future versions.
"""
import logging
import warnings

# Re-export from core
from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger(__name__)
warnings.warn(
    "Importing from 'plugins.base' is deprecated. Use 'core.interfaces.plugin' instead.",
    DeprecationWarning,
    stacklevel=2
)
