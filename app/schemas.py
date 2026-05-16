from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any


# ==================== ITEM SCHEMAS ====================

class ItemBase(BaseModel):
    """Базовая схема предмета"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название предмета (обязательное поле)",
        example="Ноутбук"
    )
    description: Optional[str] = Field(
        None,
        description="Описание предмета (опциональное)",
        example="Мощный игровой ноутбук с RTX 4060"
    )
    status: str = Field(
        "active",
        description="Статус предмета",
        example="active",
        pattern="^(active|inactive)$"
    )


class ItemCreate(ItemBase):
    """Схема для создания предмета (POST /items)"""
    pass


class ItemUpdate(BaseModel):
    """Схема для обновления предмета (PUT / PATCH)"""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Название предмета",
        example="Игровой ноутбук"
    )
    description: Optional[str] = Field(
        None,
        description="Описание предмета",
        example="RTX 4060, 32GB RAM"
    )
    status: Optional[str] = Field(
        None,
        description="Статус предмета",
        example="inactive"
    )


class ItemResponse(ItemBase):
    """Схема ответа с данными предмета"""
    id: int = Field(..., description="Уникальный идентификатор", example=1)
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата последнего обновления")
    
    class Config:
        from_attributes = True


# ==================== AUTH SCHEMAS ====================

class UserRegister(BaseModel):
    """Схема для регистрации пользователя"""
    email: str = Field(
        ...,
        description="Email пользователя",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Пароль (минимум 6 символов)",
        example="strongpassword123"
    )
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Простая проверка email"""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: str = Field(..., description="Email пользователя", example="user@example.com")
    password: str = Field(..., description="Пароль", example="strongpassword123")


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя (без пароля и токенов)"""
    id: int = Field(..., description="Уникальный идентификатор", example=1)
    email: str = Field(..., description="Email пользователя", example="user@example.com")
    created_at: datetime = Field(..., description="Дата регистрации")
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Схема ответа при успешной аутентификации"""
    message: str = Field(..., description="Сообщение о результате", example="Login successful")
    user: UserResponse = Field(..., description="Данные пользователя")


class WhoamiResponse(BaseModel):
    """Схема ответа для эндпоинта /whoami"""
    user: UserResponse = Field(..., description="Данные текущего пользователя")


# ==================== PAGINATION SCHEMAS ====================

class PaginationParams(BaseModel):
    """Параметры пагинации для GET /items"""
    page: int = Field(
        1,
        ge=1,
        description="Номер страницы (начинается с 1)",
        example=2
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Количество элементов на странице (от 1 до 100)",
        example=20
    )
    
    @property
    def offset(self) -> int:
        """Смещение для SQL запроса"""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel):
    """Схема ответа с пагинированным списком предметов"""
    data: List[ItemResponse] = Field(..., description="Массив предметов")
    meta: Dict[str, Any] = Field(
        ...,
        description="Мета-информация о пагинации",
        example={
            "total": 25,
            "page": 2,
            "limit": 10,
            "totalPages": 3
        }
    )