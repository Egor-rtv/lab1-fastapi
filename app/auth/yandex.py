import secrets
import httpx
from urllib.parse import urlencode
from typing import Dict, Any, Optional

from app.database import settings


def generate_yandex_auth_url(state: str) -> str:
    """
    Формирует URL для редиректа на страницу авторизации Яндекса.
    """
    params = {
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.yandex_redirect_uri,
        "state": state,
    }
    return f"https://oauth.yandex.ru/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Обменивает код авторизации на Access Token Яндекса.
    Возвращает JSON с токеном или None при ошибке.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.yandex_client_id,
                "client_secret": settings.yandex_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            return None
        
        return response.json()


async def get_yandex_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Получает информацию о пользователе от Яндекса.
    Возвращает JSON с email, name и другими полями.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://login.yandex.ru/info",
            params={"format": "json"},
            headers={"Authorization": f"OAuth {access_token}"}
        )
        
        if response.status_code != 200:
            return None
        
        return response.json()