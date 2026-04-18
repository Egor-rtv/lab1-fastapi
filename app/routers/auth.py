from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import hashlib

from app.database import get_db
from app.schemas import UserRegister, UserLogin, UserResponse, WhoamiResponse, AuthResponse
from app.crud import UserService, RefreshTokenService
from app.security.hashing import hash_password, verify_password
from app.security.jwt import create_access_token, create_refresh_token, decode_refresh_token, get_user_id_from_access_token
from app.security.cookies import set_auth_cookies, clear_auth_cookies
from app.database import settings
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


# ==================== POST /auth/register ====================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрация нового пользователя.
    """
    user_service = UserService(db)
    
    # Проверяем, не существует ли уже пользователь с таким email
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Хешируем пароль
    hashed_password = hash_password(user_data.password)
    
    # Создаём пользователя
    user = await user_service.create_user(user_data.email, hashed_password)
    
    # Генерируем токены
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # Хешируем Refresh Token для хранения в БД
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Сохраняем Refresh Token в БД
    refresh_service = RefreshTokenService(db)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_refresh_expiration)
    await refresh_service.create_token(user.id, refresh_token_hash, expires_at)
    
    # Устанавливаем cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return AuthResponse(
        message="Registration successful",
        user=UserResponse.model_validate(user)
    )


# ==================== POST /auth/login ====================

@router.post("/login", response_model=AuthResponse)
async def login(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Вход пользователя.
    """
    user_service = UserService(db)
    
    # Ищем пользователя по email
    user = await user_service.get_user_by_email(user_data.email)
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Проверяем пароль
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Генерируем токены
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # Хешируем Refresh Token для хранения в БД
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    # Сохраняем Refresh Token в БД
    refresh_service = RefreshTokenService(db)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_refresh_expiration)
    await refresh_service.create_token(user.id, refresh_token_hash, expires_at)
    
    # Устанавливаем cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return AuthResponse(
        message="Login successful",
        user=UserResponse.model_validate(user)
    )


# ==================== POST /auth/refresh ====================

@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление пары токенов.
    """
    # Получаем Refresh Token из cookies
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    # Декодируем Refresh Token
    payload = decode_refresh_token(refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = int(payload["sub"])
    
    # Проверяем, что токен есть в БД и не отозван
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_service = RefreshTokenService(db)
    stored_token = await refresh_service.get_active_token(refresh_token_hash)
    
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired"
        )
    
    # Генерируем новые токены
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    
    # Хешируем новый Refresh Token
    new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    
    # Отзываем старый токен и создаём новый
    await refresh_service.revoke_token(stored_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_refresh_expiration)
    await refresh_service.create_token(user_id, new_refresh_token_hash, expires_at)
    
    # Устанавливаем новые cookies
    set_auth_cookies(response, new_access_token, new_refresh_token)
    
    return {"message": "Tokens refreshed successfully"}


# ==================== GET /auth/whoami ====================

@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение информации о текущем пользователе.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user_id = get_user_id_from_access_token(access_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return WhoamiResponse(user=UserResponse.model_validate(user))


# ==================== POST /auth/logout ====================

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Завершение текущей сессии (отзыв текущего Refresh Token).
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        refresh_service = RefreshTokenService(db)
        stored_token = await refresh_service.get_active_token(refresh_token_hash)
        if stored_token:
            await refresh_service.revoke_token(stored_token)
    
    # Очищаем cookies
    clear_auth_cookies(response)
    
    return {"message": "Logged out successfully"}


# ==================== POST /auth/logout-all ====================

@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Завершение всех сессий пользователя (отзыв всех Refresh Token).
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user_id = get_user_id_from_access_token(access_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    # Отзываем все токены пользователя
    refresh_service = RefreshTokenService(db)
    await refresh_service.revoke_all_user_tokens(user_id)
    
    # Очищаем cookies
    clear_auth_cookies(response)
    
    return {"message": "All sessions terminated successfully"}
# ==================== OAuth Yandex ====================

import secrets
from app.auth.yandex import generate_yandex_auth_url, exchange_code_for_token, get_yandex_user_info


@router.get("/oauth/yandex")
async def oauth_yandex_login():
    """
    Перенаправляет пользователя на страницу авторизации Яндекса.
    """
    # Генерируем случайный state для защиты от CSRF
    state = secrets.token_urlsafe(32)
    
    # В реальном приложении state нужно сохранить в сессии или БД.
    # Для простоты будем передавать его как параметр (временно).
    # При callback'е проверим, что state совпадает.
    
    auth_url = generate_yandex_auth_url(state)
    
    # Для простоты: передаём state в URL редиректа.
    # В продакшене нужно сохранять state в БД или кэше.
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="oauth_state", value=state, httponly=True, max_age=600)
    return response


@router.get("/oauth/yandex/callback")
async def oauth_yandex_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    code: str = None,
    state: str = None,
):
    """
    Обработка callback'а от Яндекса после успешной авторизации.
    """
    # 1. Проверяем state (защита от CSRF)
    saved_state = request.cookies.get("oauth_state")
    if not saved_state or saved_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    # 2. Проверяем, что code есть
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    
    # 3. Обмениваем code на Access Token
    token_data = await exchange_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token"
        )
    
    access_token_yandex = token_data["access_token"]
    
    # 4. Получаем информацию о пользователе
    user_info = await get_yandex_user_info(access_token_yandex)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Yandex"
        )
    
    # 5. Извлекаем email и yandex_id
    email = user_info.get("default_email") or user_info.get("email")
    yandex_id = user_info.get("id")
    
    if not email or not yandex_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email or ID not provided by Yandex"
        )
    
    # 6. Ищем или создаём пользователя в БД
    user_service = UserService(db)
    user = await user_service.get_user_by_yandex_id(yandex_id)
    
    if not user:
        # Пробуем найти по email
        user = await user_service.get_user_by_email(email)
        
        if user:
            # Обновляем существующего пользователя: добавляем yandex_id
            user.yandex_id = yandex_id
            await db.commit()
            await db.refresh(user)
        else:
            # Создаём нового пользователя
            user = await user_service.create_user_yandex(email, yandex_id)
    
    # 7. Генерируем локальные JWT токены
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    # 8. Хешируем Refresh Token и сохраняем в БД
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_service = RefreshTokenService(db)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_refresh_expiration)
    await refresh_service.create_token(user.id, refresh_token_hash, expires_at)
    
    # 9. Устанавливаем cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    # 10. Удаляем временный state cookie
    response.delete_cookie("oauth_state")
    
    # 11. Редиректим на фронтенд (или возвращаем успех)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="http://localhost:4200/docs")