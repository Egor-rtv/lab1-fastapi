from fastapi import Response
from datetime import datetime, timedelta


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str
) -> None:
    # Access Token cookie (15 минут)
    expires_access = datetime.utcnow() + timedelta(minutes=15)
    
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        expires=expires_access.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        path="/"
    )
    
    # Refresh Token cookie (7 дней)
    expires_refresh = datetime.utcnow() + timedelta(days=7)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        expires=expires_refresh.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    """Удаляет cookies с токенами (при выходе из системы)."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")