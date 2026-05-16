from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.jwt import get_user_id_from_access_token, get_jti_from_access_token
from app.crud import UserService
from app.services.cache_service import get_cache_service, CacheService


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    """
    Dependency для получения текущего авторизованного пользователя.
    Проверяет Access Token и наличие JTI в Redis.
    """
    # Извлекаем токен из cookies
    access_token = request.cookies.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Декодируем токен и получаем user_id и jti
    user_id = get_user_id_from_access_token(access_token)
    jti = get_jti_from_access_token(access_token)
    
    if not user_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Проверяем, что jti есть в Redis (токен не отозван)
    redis_key = f"wp:auth:user:{user_id}:access:{jti}"
    is_valid = await cache.get(redis_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked"
        )
    
    # Загружаем пользователя из БД
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user