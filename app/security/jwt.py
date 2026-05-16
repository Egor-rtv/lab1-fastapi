import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from app.database import settings


def create_access_token(user_id: int) -> Tuple[str, str]:
    """
    Создаёт Access Token (короткоживущий).
    Возвращает (token, jti)
    """
    jti = str(uuid.uuid4())
    expires_delta = timedelta(minutes=settings.jwt_access_expiration)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "jti": jti
    }
    
    token = jwt.encode(payload, settings.jwt_access_secret, algorithm="HS256")
    return token, jti


def create_refresh_token(user_id: int) -> Tuple[str, str]:
    """
    Создаёт Refresh Token (долгоживущий).
    Возвращает (token, jti)
    """
    jti = str(uuid.uuid4())
    expires_delta = timedelta(minutes=settings.jwt_refresh_expiration)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": jti
    }
    
    token = jwt.encode(payload, settings.jwt_refresh_secret, algorithm="HS256")
    return token, jti


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирует и проверяет Access Token.
    Возвращает payload или None (если токен невалидный или просрочен).
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_access_secret,
            algorithms=["HS256"]
        )
        # Проверяем, что это действительно access токен
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирует и проверяет Refresh Token.
    Возвращает payload или None (если токен невалидный или просрочен).
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_refresh_secret,
            algorithms=["HS256"]
        )
        # Проверяем, что это действительно refresh токен
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_access_token(token: str) -> Optional[int]:
    """
    Извлекает user_id из Access Token.
    """
    payload = decode_access_token(token)
    if payload and "sub" in payload:
        return int(payload["sub"])
    return None


def get_jti_from_access_token(token: str) -> Optional[str]:
    """Извлекает jti из Access Token"""
    payload = decode_access_token(token)
    if payload and "jti" in payload:
        return payload["jti"]
    return None