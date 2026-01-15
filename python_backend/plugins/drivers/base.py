"""
DEPRECATED: Use core.interfaces.driver instead.
This module is kept for backward compatibility and will be removed in future versions.
"""
import logging
import warnings

# Re-export from core
from core.interfaces.driver import (
    BaseDriver,
    BaseTTSDriver,
    BaseSTTDriver,
    BaseVoiceAuthDriver,
    BaseVisionDriver,
    BaseMemoryDriver,
    BaseLLMDriver
)

logger = logging.getLogger(__name__)
warnings.warn(
    "Importing from 'plugins.drivers.base' is deprecated. Use 'core.interfaces.driver' instead.",
    DeprecationWarning,
    stacklevel=2
)
