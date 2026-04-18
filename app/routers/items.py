from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ItemCreate, ItemUpdate, ItemResponse, PaginationParams, PaginatedResponse
from app.crud import ItemService
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/items", tags=["items"])

# GET /items — список с пагинацией
@router.get("/", response_model=PaginatedResponse)
async def get_items(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    items, total = await service.get_active_items(pagination)
    
    total_pages = (total + pagination.limit - 1) // pagination.limit if total > 0 else 0
    
    return {
        "data": items,
        "meta": {
            "total": total,
            "page": pagination.page,
            "limit": pagination.limit,
            "totalPages": total_pages
        }
    }

# GET /items/{id}
@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    item = await service.get_active_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

# POST /items
@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    return await service.create_item(item_data)

# PUT /items/{id}
@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    item = await service.update_item(item_id, item_data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

# PATCH /items/{id}
@router.patch("/{item_id}", response_model=ItemResponse)
async def patch_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    item = await service.patch_item(item_id, item_data)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

# DELETE /items/{id}
@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),  # ← добавить
    db: AsyncSession = Depends(get_db)
):
    service = ItemService(db)
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return None