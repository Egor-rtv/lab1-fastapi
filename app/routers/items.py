from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, settings
from app.schemas import ItemCreate, ItemUpdate, ItemResponse, PaginationParams, PaginatedResponse
from app.crud import ItemService
from app.dependencies import get_current_user
from app.models import User
from app.services.cache_service import get_cache_service, CacheService

router = APIRouter(
    prefix="/items",
    tags=[" Управление предметами"],
    responses={
        401: {"description": "Не авторизован"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Предмет не найден"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)


# ==================== Вспомогательная функция инвалидации ====================

async def invalidate_items_cache(cache: CacheService):
    """Удаляет все кешированные списки items"""
    await cache.delete_pattern("wp:items:list:*")


# ==================== GET /items ====================

@router.get("/", response_model=PaginatedResponse)
async def get_items(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    # Формируем ключ кеша
    cache_key = f"wp:items:list:page:{pagination.page}:limit:{pagination.limit}"
    
    # Пытаемся получить из кеша
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Если нет в кеше — запрос к БД
    service = ItemService(db)
    items, total = await service.get_active_items(pagination)
    
    total_pages = (total + pagination.limit - 1) // pagination.limit if total > 0 else 0
    
    # Преобразуем SQLAlchemy объекты в Pydantic схемы для сериализации
    items_serialized = [ItemResponse.model_validate(item).model_dump() for item in items]
    
    response_data = {
        "data": items_serialized,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages
        }
    }
    
    # Сохраняем в кеш
    await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL_DEFAULT)
    
    return response_data
async def get_items(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    # Формируем ключ кеша
    cache_key = f"wp:items:list:page:{pagination.page}:limit:{pagination.limit}"
    
    # Пытаемся получить из кеша
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Если нет в кеше — запрос к БД
    service = ItemService(db)
    items, total = await service.get_active_items(pagination)
    
    total_pages = (total + pagination.limit - 1) // pagination.limit if total > 0 else 0
    
    response_data = {
        "data": items,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages
        }
    }
    
    # Сохраняем в кеш
    await cache.set(cache_key, response_data, ttl=settings.CACHE_TTL_DEFAULT)
    
    return response_data


# ==================== GET /items/{id} ====================

@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary=" Получить предмет по ID",
    description="""
    Возвращает один предмет по его уникальному идентификатору.

    **Требования:**
    - Только авторизованные пользователи
    - Предмет должен существовать и не быть удалённым (soft delete)
    """,
    responses={
        200: {
            "description": "Предмет найден",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Ноутбук",
                        "description": "Игровой ноутбук RTX 4060",
                        "status": "active",
                        "created_at": "2026-05-15T12:00:00Z",
                        "updated_at": None
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {
            "description": "Предмет не найден или удалён",
            "content": {
                "application/json": {
                    "example": {"detail": "Item not found"}
                }
            }
        }
    }
)
async def get_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    item = await service.get_active_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


# ==================== POST /items ====================

@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary=" Создать новый предмет",
    description="""
    Создаёт новый предмет в системе.

    **Поля:**
    - `name` (обязательное) — название предмета
    - `description` (опциональное) — описание
    - `status` (опциональное, default: "active") — статус

    **Автоматически устанавливаются:**
    - `id` — автоинкремент
    - `created_at` — текущая дата и время

    **Требования:**
    - Только авторизованные пользователи
    - При создании кеш списков инвалидируется
    """,
    responses={
        201: {
            "description": "Предмет успешно создан",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Новый предмет",
                        "description": "Описание нового предмета",
                        "status": "active",
                        "created_at": "2026-05-15T12:00:00Z",
                        "updated_at": None
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        422: {
            "description": "Ошибка валидации",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "name"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    service = ItemService(db)
    result = await service.create_item(item_data)
    
    # Инвалидируем кеш списков
    await invalidate_items_cache(cache)
    
    return result


# ==================== PUT /items/{id} ====================

@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    summary=" Полное обновление предмета",
    description="""
    Полностью заменяет предмет новыми данными.

    **Важно:** PUT заменяет ВСЕ поля. Если какое-то поле не передано, оно станет `null`.

    **Отличие от PATCH:** PUT требует полный объект, PATCH — только изменяемые поля.

    **Требования:**
    - Только авторизованные пользователи
    - Предмет должен существовать и не быть удалённым
    - При обновлении кеш списков инвалидируется
    """,
    responses={
        200: {
            "description": "Предмет обновлён",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Обновлённое название",
                        "description": "Новое описание",
                        "status": "inactive",
                        "created_at": "2026-05-15T12:00:00Z",
                        "updated_at": "2026-05-15T13:00:00Z"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Предмет не найден"}
    }
)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    service = ItemService(db)
    item = await service.update_item(item_id, item_data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Инвалидируем кеш списков
    await invalidate_items_cache(cache)
    
    return item


# ==================== PATCH /items/{id} ====================

@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary=" Частичное обновление предмета",
    description="""
    Обновляет только указанные поля предмета.

    **Отличие от PUT:** PATCH обновляет только переданные поля, остальные остаются без изменений.

    **Требования:**
    - Только авторизованные пользователи
    - Предмет должен существовать и не быть удалённым
    - При обновлении кеш списков инвалидируется
    """,
    responses={
        200: {
            "description": "Предмет обновлён",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Ноутбук",
                        "description": "Игровой ноутбук RTX 4060",
                        "status": "inactive",
                        "created_at": "2026-05-15T12:00:00Z",
                        "updated_at": "2026-05-15T13:00:00Z"
                    }
                }
            }
        },
        401: {"description": "Не авторизован"},
        404: {"description": "Предмет не найден"}
    }
)
async def patch_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    service = ItemService(db)
    item = await service.patch_item(item_id, item_data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Инвалидируем кеш списков
    await invalidate_items_cache(cache)
    
    return item


# ==================== DELETE /items/{id} ====================

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary=" Мягкое удаление предмета",
    description="""
    Помечает предмет как удалённый (Soft Delete).

    **Что происходит:**
    - Запись НЕ удаляется из базы данных
    - Устанавливается поле `deleted_at` = текущая дата
    - Предмет перестаёт отображаться в GET /items и GET /items/{id}

    **Преимущества:**
    - Данные можно восстановить
    - Сохраняется история
    - Нет проблем с внешними ключами

    **Требования:**
    - Только авторизованные пользователи
    - Предмет должен существовать и не быть уже удалённым
    - При удалении кеш списков инвалидируется
    """,
    responses={
        204: {"description": "Предмет успешно удалён (тело ответа пустое)"},
        401: {"description": "Не авторизован"},
        404: {"description": "Предмет не найден"}
    }
)
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service)
):
    service = ItemService(db)
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    
    # Инвалидируем кеш списков
    await invalidate_items_cache(cache)
    
    return None