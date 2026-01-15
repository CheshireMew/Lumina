import logging
from typing import Dict, Any, Optional
from pythonosc import udp_client

logger = logging.getLogger("VMCProtocol")

class VMCClient:
    """
    VMC (Virtual Motion Capture) Protocol Client via OSC.
    Follows VMC 2.0 Spec for BlendShapes and Root Transform.
    """
    def __init__(self, ip: str = "127.0.0.1", port: int = 39539):
        self.ip = ip
        self.port = port
        self.client = None
        self._connect()

    def _connect(self):
        try:
            self.client = udp_client.SimpleUDPClient(self.ip, self.port)
            logger.info(f"VMC OSC Client initialized at {self.ip}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to initialize OSC Client: {e}")
            self.client = None

    def send_blendshape(self, name: str, value: float):
        """
        Sends a BlendShape value.
        Address: /VMC/Ext/Blend/Val
        """
        if not self.client: return
        try:
            # VMC Standard: /VMC/Ext/Blend/Val (String name) (Float value)
            self.client.send_message("/VMC/Ext/Blend/Val", [name, float(value)])
        except Exception as e:
            logger.debug(f"OSC Send Error: {e}")

    def send_emotion(self, emotion_name: str, mapping: Dict[str, str]):
        """
        Sends a mapped blendshape for an emotion.
        e.g. "joy" -> "Fun" = 1.0
        """
        target_blendshape = mapping.get(emotion_name)
        if target_blendshape:
            # Reset others? (Naive implementation for now)
            # Ideally we might want to fade out others, but for VMC often "Fun" overrides.
            # We'll just send the trigger.
            logger.info(f"[VMC] Sending Emotion: {emotion_name} -> {target_blendshape}")
            self.send_blendshape(target_blendshape, 1.0)
            
            # Send a "reset" for this blendshape after a duration? 
            # Or assume the external app handles decay?
            # VSeeFace usually expects sustained values or triggers.
            # Let's assume this is a 'Set' operation.
        else:
            logger.warning(f"[VMC] No mapping found for emotion: {emotion_name}")

    def send_root_pos(self, x: float, y: float, z: float):
        """
        Moves the avatar root.
        """
        if not self.client: return
        self.client.send_message("/VMC/Ext/Root/Pos", ["root", float(x), float(y), float(z), 0.0, 0.0, 0.0, 1.0])
