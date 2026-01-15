try:
    print("Importing app_config...")
    import app_config
    print("Importing main...")
    # We can't fully import main because it runs uvicorn maybe?
    # But checking imports is a good start.
    from services.system_plugin_manager import SystemPluginManager
    from  plugins.system.voice_security import VoiceSecurityPlugin
    from  plugins.base import BaseSystemPlugin
    from services.mcp_host import MCPHost
    print("Imports OK.")
    
    # Try instantiate VoiceSecurityPlugin to test abstract methods
    p = VoiceSecurityPlugin()
    p.initialize("mock_container")
    print("VoiceSecurityPlugin Instantiated OK")

except Exception as e:
    import traceback
    traceback.print_exc()
