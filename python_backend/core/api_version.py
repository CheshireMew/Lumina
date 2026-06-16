import logging

logger = logging.getLogger("API")

PLUGIN_API_VERSION = "1.0"
CONTEXT_PROTOCOL_VERSION = "1.0"


def is_supported_manifest_api_version(manifest_api_version: str) -> bool:
    """Return True when a plugin manifest targets this plugin API major version."""
    try:
        manifest_major = int(manifest_api_version.split(".")[0])
        current_major = int(PLUGIN_API_VERSION.split(".")[0])
        return manifest_major == current_major
    except (AttributeError, ValueError, IndexError):
        logger.warning(f"Invalid api_version format: {manifest_api_version}")
        return False
