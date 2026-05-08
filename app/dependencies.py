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
    """
    print("=" * 50)
    print("get_current_user CALLED")
    print(f"All cookies in request: {request.cookies}")
    
    # Извлекаем токен из cookies
    access_token = request.cookies.get("access_token")
    print(f"Access token from cookie: {access_token[:20] if access_token else 'None'}")
    
    if not access_token:
        print("No access token in cookies")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Декодируем токен и получаем user_id
    user_id = get_user_id_from_access_token(access_token)
    print(f"User_id from token: {user_id}")
    
    if not user_id:
        print("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Загружаем пользователя из БД
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    print(f"User from DB: {user.email if user else 'None'}")
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    print("get_current_user SUCCESS")
    print("=" * 50)
    return user