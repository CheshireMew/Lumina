import jwt
import datetime
import secrets
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("TokenManager")

class TokenManager:
    _secret_key = None
    _algorithm = "HS256"

    @classmethod
    def get_secret(cls):
        if not cls._secret_key:
            # Try load from file
            import os
            key_file = "lumina.secret"
            if os.path.exists(key_file):
                try:
                    with open(key_file, "r", encoding="utf-8") as f:
                         cls._secret_key = f.read().strip()
                except Exception as e:
                    logger.warning(f"Failed to read key file, regenerating: {e}")
            
            if not cls._secret_key:
                # Generate new
                cls._secret_key = secrets.token_hex(32)
                # Save
                try:
                    with open(key_file, "w", encoding="utf-8") as f:
                        f.write(cls._secret_key)
                except Exception as e:
                    logger.error(f"Failed to save secret key: {e}")
                    
        return cls._secret_key

    @classmethod
    def create_token(cls, plugin_id: str, permissions: list, ttl_minutes: int = 60) -> str:
        """
        Create a Scoped JWT for a specific plugin.
        """
        payload = {
            "sub": plugin_id,
            "scope": "plugin",
            "permissions": permissions,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ttl_minutes)
        }
        
        token = jwt.encode(payload, cls.get_secret(), algorithm=cls._algorithm)
        return token

    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a token. Returns payload dict or None.
        """
        try:
            payload = jwt.decode(token, cls.get_secret(), algorithms=[cls._algorithm])
            if payload.get("scope") != "plugin":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
