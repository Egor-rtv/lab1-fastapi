import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from app.database import settings


def create_access_token(user_id: int) -> str:
    """
    Создаёт Access Token (короткоживущий).
    Время жизни берётся из .env (по умолчанию 15 минут).
    """
    expires_delta = timedelta(minutes=settings.jwt_access_expiration)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access"
    }
    
    return jwt.encode(payload, settings.jwt_access_secret, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    """
    Создаёт Refresh Token (долгоживущий).
    Время жизни берётся из .env (по умолчанию 7 дней).
    """
    expires_delta = timedelta(minutes=settings.jwt_refresh_expiration)
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh"
    }
    
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm="HS256")


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