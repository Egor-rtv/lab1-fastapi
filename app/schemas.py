from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Базовая схема для ответа
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    status: str = "active"

# Схема для создания (POST)
class ItemCreate(ItemBase):
    pass

# Схема для обновления (PUT/PATCH) — все поля опциональны
class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = None

# Схема для ответа (возвращаем клиенту)
class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Схема для пагинации
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    
    @property
    def offset(self):
        return (self.page - 1) * self.limit

# Схема для ответа с пагинацией
class PaginatedResponse(BaseModel):
    data: list[ItemResponse]
    meta: dict
# ==================== AUTH SCHEMAS ====================

class UserRegister(BaseModel):
    """Схема для регистрации нового пользователя"""
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: str
    password: str


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя (без пароля)"""
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class WhoamiResponse(BaseModel):
    """Схема ответа для эндпоинта /whoami"""
    user: UserResponse


class AuthResponse(BaseModel):
    """Схема ответа при успешной аутентификации"""
    message: str
    user: UserResponse