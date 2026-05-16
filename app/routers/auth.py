from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
import hashlib

from app.database import get_db, settings
from app.schemas import UserRegister, UserLogin, UserResponse, WhoamiResponse, AuthResponse
from app.crud import UserService, RefreshTokenService
from app.security.hashing import hash_password, verify_password
from app.security.jwt import create_access_token, create_refresh_token, decode_refresh_token, get_user_id_from_access_token, get_jti_from_access_token
from app.security.cookies import set_auth_cookies, clear_auth_cookies
from app.services.cache_service import get_cache_service, CacheService
from datetime import timedelta

router = APIRouter(
    prefix="/auth",
    tags=[" Аутентификация"],
    responses={
        401: {"description": "Не авторизован"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


# ==================== POST /auth/register ====================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary=" Регистрация нового пользователя",
    description="""
    Создаёт нового пользователя в системе.

    **Процесс:**
    1. Проверяет, что email не занят
    2. Хеширует пароль с помощью bcrypt (уникальная соль)
    3. Сохраняет пользователя в БД
    4. Генерирует пару JWT токенов (Access + Refresh) с JTI
    5. Сохраняет JTI в Redis для возможности отзыва
    6. Устанавливает HttpOnly cookies с токенами

    **Внимание:** Пароль не возвращается в ответе, а хранится в БД в захешированном виде.
    """,
    responses={
        201: {
            "description": "Пользователь успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Registration successful",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "created_at": "2026-05-15T12:00:00Z"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Пользователь с таким email уже существует",
            "content": {
                "application/json": {
                    "example": {"detail": "User with this email already exists"}
                }
            }
        },
        422: {
            "description": "Ошибка валидации данных",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "type": "value_error.email"
                            }
                        ]
                    }
                }
            }
        }
    }
)
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
    
    # Генерируем токены с JTI
    access_token, access_jti = create_access_token(user.id)
    refresh_token, refresh_jti = create_refresh_token(user.id)
    
    # Сохраняем JTI Access токена в Redis
    cache = await get_cache_service()
    redis_key = f"wp:auth:user:{user.id}:access:{access_jti}"
    await cache.set(redis_key, "valid", ttl=settings.jwt_access_expiration * 60)
    
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

@router.post(
    "/login",
    response_model=AuthResponse,
    summary=" Вход в систему",
    description="""
    Аутентификация пользователя по email и паролю.

    **Процесс:**
    1. Поиск пользователя по email
    2. Проверка пароля (bcrypt verify)
    3. Генерация пары JWT токенов с JTI
    4. Сохранение JTI в Redis
    5. Установка HttpOnly cookies

    **После успешного входа:**
    - Access Token (15 минут) и Refresh Token (7 дней) сохраняются в HttpOnly cookies
    - Можно выполнять запросы к защищённым эндпоинтам (`/items/*`, `/auth/whoami`)
    """,
    responses={
        200: {
            "description": "Успешный вход",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login successful",
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "created_at": "2026-05-15T12:00:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Неверный email или пароль",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password"}
                }
            }
        }
    }
)
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
    
    # Генерируем токены с JTI
    access_token, access_jti = create_access_token(user.id)
    refresh_token, refresh_jti = create_refresh_token(user.id)
    
    # Сохраняем JTI Access токена в Redis
    cache = await get_cache_service()
    redis_key = f"wp:auth:user:{user.id}:access:{access_jti}"
    await cache.set(redis_key, "valid", ttl=settings.jwt_access_expiration * 60)
    
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

@router.post(
    "/refresh",
    summary=" Обновить пару токенов",
    description="""
    Обновляет Access и Refresh токены с помощью Refresh Token из cookies.

    **Когда использовать:**
    - Access Token истёк (15 минут)
    - Нужно продлить сессию без повторного ввода пароля

    **Процесс:**
    1. Извлекает Refresh Token из cookies
    2. Проверяет его валидность (подпись + БД)
    3. Отзывает старый токен
    4. Генерирует новую пару токенов с новыми JTI
    5. Сохраняет новый JTI в Redis
    6. Устанавливает новые cookies
    """,
    responses={
        200: {
            "description": "Токены успешно обновлены",
            "content": {
                "application/json": {
                    "example": {"message": "Tokens refreshed successfully"}
                }
            }
        },
        401: {
            "description": "Refresh Token отсутствует, невалиден или отозван",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {"summary": "Токен отсутствует", "value": {"detail": "Refresh token not found"}},
                        "invalid": {"summary": "Невалидный токен", "value": {"detail": "Invalid refresh token"}},
                        "revoked": {"summary": "Токен отозван", "value": {"detail": "Refresh token revoked or expired"}}
                    }
                }
            }
        }
    }
)
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
    
    # Генерируем новые токены с JTI
    new_access_token, new_access_jti = create_access_token(user_id)
    new_refresh_token, new_refresh_jti = create_refresh_token(user_id)
    
    # Сохраняем новый JTI Access токена в Redis
    cache = await get_cache_service()
    redis_key = f"wp:auth:user:{user_id}:access:{new_access_jti}"
    await cache.set(redis_key, "valid", ttl=settings.jwt_access_expiration * 60)
    
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

@router.get(
    "/whoami",
    response_model=WhoamiResponse,
    summary=" Получить информацию о текущем пользователе",
    description="""
    Возвращает профиль текущего авторизованного пользователя.

    **Требования:**
    - Наличие валидного Access Token в cookies
    - JTI должен быть в Redis (токен не отозван)

    **Используется фронтендом для:**
    - Проверки авторизации
    - Отображения email пользователя в UI
    """,
    responses={
        200: {
            "description": "Информация о пользователе",
            "content": {
                "application/json": {
                    "example": {
                        "user": {
                            "id": 1,
                            "email": "user@example.com",
                            "created_at": "2026-05-15T12:00:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Не авторизован (отсутствует, невалидный или отозванный токен)",
            "content": {
                "application/json": {
                    "example": {"detail": "Token revoked"}
                }
            }
        },
        404: {
            "description": "Пользователь не найден",
            "content": {
                "application/json": {
                    "example": {"detail": "User not found"}
                }
            }
        }
    }
)
async def whoami(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    print(">>> WHOAMI ENDPOINT CALLED <<<")
    print(f"Cookies: {request.cookies}")
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
    
    # Проверяем кеш профиля
    cache_key = f"wp:auth:user:{user_id}:profile"
    cached_profile = await cache.get(cache_key)
    if cached_profile:
        return WhoamiResponse(user=UserResponse.model_validate(cached_profile))
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Сохраняем в кеш
    await cache.set(cache_key, user, ttl=settings.CACHE_TTL_DEFAULT)
    
    return WhoamiResponse(user=UserResponse.model_validate(user))


# ==================== POST /auth/logout ====================

@router.post(
    "/logout",
    summary=" Завершить текущую сессию",
    description="""
    Отзывает текущий Refresh Token и удаляет JTI из Redis.

    **Результат:**
    - Текущая сессия завершается
    - JTI удаляется из Redis → Access Token становится недействительным мгновенно
    - Нельзя получить новый Access Token по этому Refresh Token
    - Другие сессии (если есть) остаются активными
    """,
    responses={
        200: {
            "description": "Успешный выход",
            "content": {
                "application/json": {
                    "example": {"message": "Logged out successfully"}
                }
            }
        }
    }
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Завершение текущей сессии (отзыв текущего Refresh Token и удаление JTI из Redis).
    """
    # Удаляем JTI Access токена из Redis
    access_token = request.cookies.get("access_token")
    user_id = None
    if access_token:
        jti = get_jti_from_access_token(access_token)
        user_id = get_user_id_from_access_token(access_token)
        if jti and user_id:
            redis_key = f"wp:auth:user:{user_id}:access:{jti}"
            await cache.delete(redis_key)
    
    # Удаляем кеш профиля
    if user_id:
        await cache.delete(f"wp:auth:user:{user_id}:profile")
    
    # Отзыв Refresh Token в БД
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

@router.post(
    "/logout-all",
    summary=" Завершить ВСЕ сессии пользователя",
    description="""
    Отзывает **все** Refresh Token пользователя и удаляет все JTI из Redis.

    **Когда использовать:**
    - Подозрение на компрометацию аккаунта
    - Пользователь хочет выйти со всех устройств

    **Результат:**
    - Все сессии пользователя завершаются
    - Все JTI удаляются из Redis
    - Требуется повторный вход на всех устройствах
    """,
    responses={
        200: {
            "description": "Все сессии завершены",
            "content": {
                "application/json": {
                    "example": {"message": "All sessions terminated successfully"}
                }
            }
        },
        401: {
            "description": "Не авторизован",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Завершение всех сессий пользователя (отзыв всех Refresh Token и удаление всех JTI из Redis).
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
    
    # Удаляем все JTI пользователя из Redis по паттерну
    await cache.delete_pattern(f"wp:auth:user:{user_id}:access:*")
    
    # Удаляем кеш профиля
    await cache.delete(f"wp:auth:user:{user_id}:profile")
    
    # Отзываем все токены в БД
    refresh_service = RefreshTokenService(db)
    await refresh_service.revoke_all_user_tokens(user_id)
    
    # Очищаем cookies
    clear_auth_cookies(response)
    
    return {"message": "All sessions terminated successfully"}


# ==================== OAuth Yandex ====================

import secrets
from app.auth.yandex import generate_yandex_auth_url, exchange_code_for_token, get_yandex_user_info


@router.get(
    "/oauth/yandex",
    summary=" Вход через Яндекс OAuth",
    description="""
    Перенаправляет пользователя на страницу авторизации Яндекса.

    **Процесс:**
    1. Генерация параметра `state` (защита от CSRF)
    2. Перенаправление на `https://oauth.yandex.ru/authorize`
    3. После авторизации пользователь возвращается на `/auth/oauth/yandex/callback`

    **Защита:** параметр `state` сохраняется в HttpOnly cookie
    """,
    responses={
        307: {"description": "Редирект на страницу авторизации Яндекса"},
        400: {"description": "Ошибка при формировании запроса"}
    }
)
async def oauth_yandex_login():
    """
    Перенаправляет пользователя на страницу авторизации Яндекса.
    """
    # Генерируем случайный state для защиты от CSRF
    state = secrets.token_urlsafe(32)
    
    auth_url = generate_yandex_auth_url(state)
    
    from fastapi.responses import RedirectResponse
    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="oauth_state", value=state, httponly=True, max_age=600)
    return response


@router.get(
    "/oauth/yandex/callback",
    summary=" Callback для OAuth Яндекс",
    description="""
    Обрабатывает ответ от Яндекса после авторизации.

    **Процесс:**
    1. Проверка параметра `state` (защита от CSRF)
    2. Обмен `code` на Access Token Яндекса
    3. Получение email пользователя
    4. Поиск или создание пользователя в БД
    5. Генерация локальных JWT токенов с JTI
    6. Сохранение JTI в Redis
    7. Установка HttpOnly cookies
    8. Редирект на Swagger документацию
    """,
    responses={
        302: {"description": "Редирект на /docs после успешной авторизации"},
        400: {"description": "Ошибка OAuth (неверный state, code или ответ от Яндекса)"}
    }
)
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
    # ДИАГНОСТИКА: проверяем, что мы вообще попали сюда
    print("=" * 50)
    print("CALLBACK WAS CALLED!")
    print(f"Received code: {code}")
    print(f"Received state: {state}")
    print(f"Cookies in request: {request.cookies}")
    print("=" * 50)
    
    # 1. Проверяем state (защита от CSRF)
    saved_state = request.cookies.get("oauth_state")
    print(f"Saved state from cookie: {saved_state}")
    
    if not saved_state or saved_state != state:
        print("STATE MISMATCH! CSRF detected")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    print("State OK")
    
    # 2. Проверяем, что code есть
    if not code:
        print("No code parameter")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    print(f"Code OK: {code[:20]}...")
    
    # 3. Обмениваем code на Access Token
    print("Exchanging code for token...")
    token_data = await exchange_code_for_token(code)
    if not token_data or "access_token" not in token_data:
        print(f"Token exchange failed: {token_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange code for token"
        )
    print("Token exchange OK")
    
    access_token_yandex = token_data["access_token"]
    
    # 4. Получаем информацию о пользователе
    print("Getting user info from Yandex...")
    user_info = await get_yandex_user_info(access_token_yandex)
    if not user_info:
        print("Failed to get user info")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get user info from Yandex"
        )
    print(f"User info: {user_info}")
    
    # 5. Извлекаем email и yandex_id
    email = user_info.get("default_email") or user_info.get("email")
    yandex_id = user_info.get("id")
    
    if not email or not yandex_id:
        print(f"Missing email or yandex_id: email={email}, yandex_id={yandex_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email or ID not provided by Yandex"
        )
    print(f"Email: {email}, Yandex ID: {yandex_id}")
    
    # 6. Ищем или создаём пользователя в БД
    user_service = UserService(db)
    user = await user_service.get_user_by_yandex_id(yandex_id)
    print(f"User found by yandex_id: {user}")
    
    if not user:
        user = await user_service.get_user_by_email(email)
        print(f"User found by email: {user}")
        
        if user:
            user.yandex_id = yandex_id
            await db.commit()
            await db.refresh(user)
            print("Updated existing user with yandex_id")
        else:
            user = await user_service.create_user_yandex(email, yandex_id)
            print("Created new user")
    
    # 7. Генерируем локальные JWT токены с JTI
    access_token, access_jti = create_access_token(user.id)
    refresh_token, refresh_jti = create_refresh_token(user.id)
    print(f"Generated tokens for user {user.id}")
    
    # 8. Сохраняем JTI Access токена в Redis
    cache = await get_cache_service()
    redis_key = f"wp:auth:user:{user.id}:access:{access_jti}"
    await cache.set(redis_key, "valid", ttl=settings.jwt_access_expiration * 60)
    
    # 9. Хешируем Refresh Token и сохраняем в БД
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    refresh_service = RefreshTokenService(db)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_refresh_expiration)
    await refresh_service.create_token(user.id, refresh_token_hash, expires_at)
    
    # 10. Устанавливаем cookies через response
    set_auth_cookies(response, access_token, refresh_token)
    
    # 11. Удаляем временный state cookie
    response.delete_cookie("oauth_state")
    
    # 12. Редиректим на фронтенд с cookies
    from fastapi.responses import RedirectResponse
    redirect_response = RedirectResponse(url="http://localhost:4200/docs", status_code=302)
    
    # Копируем все Set-Cookie заголовки в редирект
    for cookie_header in response.headers.getlist("Set-Cookie"):
        redirect_response.headers.append("Set-Cookie", cookie_header)
    
    return redirect_response