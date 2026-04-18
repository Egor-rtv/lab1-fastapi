from fastapi import Response


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str
) -> None:
    """
    Устанавливает HttpOnly cookies с токенами.
    Cookies нельзя прочитать из JavaScript (безопасно).
    """
    # Access Token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,          # JS не может прочитать
        samesite="lax",         # Защита от CSRF
        secure=False,           # True для HTTPS, False для локальной разработки
        max_age=15 * 60,        # 15 минут в секундах
        path="/"
    )
    
    # Refresh Token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 60 * 60,  # 7 дней в секундах
        path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Удаляет cookies с токенами (при выходе из системы).
    """
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")