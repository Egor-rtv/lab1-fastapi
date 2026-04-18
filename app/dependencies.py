from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.jwt import get_user_id_from_access_token
from app.crud import UserService


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Dependency для получения текущего авторизованного пользователя.
    Извлекает Access Token из cookies, проверяет его и возвращает пользователя.
    Если токен невалиден или пользователь не найден — кидает 401.
    """
    # Извлекаем токен из cookies
    access_token = request.cookies.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Декодируем токен и получаем user_id
    user_id = get_user_id_from_access_token(access_token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
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