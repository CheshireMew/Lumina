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
            import os
            from app_config import DATA_ROOT
            key_file = os.path.join(str(DATA_ROOT), "lumina.secret")
            if os.path.exists(key_file):
                try:
                    with open(key_file, "r", encoding="utf-8") as f:
                         cls._secret_key = f.read().strip()
                except Exception as e:
                    logger.warning(f"Failed to read key file, regenerating: {e}")

            if not cls._secret_key:
                cls._secret_key = secrets.token_hex(32)
                try:
                    with open(key_file, "w", encoding="utf-8") as f:
                        f.write(cls._secret_key)
                except Exception as e:
                    logger.error(f"Failed to save secret key: {e}")
                    
        return cls._secret_key

    @classmethod
    def create_token(cls, subject: str, permissions: list, ttl_minutes: int = 60, scope: str = "runtime_client") -> str:
        """
        Create a scoped JWT for a runtime client or worker.
        """
        payload = {
            "sub": subject,
            "scope": scope,
            "permissions": permissions,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ttl_minutes)
        }

        token = jwt.encode(payload, cls.get_secret(), algorithm=cls._algorithm)
        return token

    @classmethod
    def verify_token(cls, token: str, expected_scope: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a token. Returns payload dict or None.
        Rejects tokens with a different scope.
        """
        try:
            payload = jwt.decode(token, cls.get_secret(), algorithms=[cls._algorithm])
            scope = payload.get("scope")
            if scope != expected_scope:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
