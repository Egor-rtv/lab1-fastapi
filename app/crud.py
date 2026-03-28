from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional, Tuple

from app.models import Item
from app.schemas import ItemCreate, ItemUpdate, PaginationParams

class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Получить активный (не удалённый) элемент по ID
    async def get_active_item(self, item_id: int) -> Optional[Item]:
        result = await self.db.execute(
            select(Item).where(
                Item.id == item_id,
                Item.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    
    # Получить список активных элементов с пагинацией
    async def get_active_items(self, pagination: PaginationParams) -> Tuple[list[Item], int]:
        # Запрос для подсчёта общего количества
        count_query = select(func.count()).select_from(Item).where(Item.deleted_at.is_(None))
        total = await self.db.scalar(count_query)
        
        # Запрос для получения данных
        query = select(Item).where(Item.deleted_at.is_(None))
        query = query.offset(pagination.offset).limit(pagination.limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    # Создать новый элемент
    async def create_item(self, item_data: ItemCreate) -> Item:
        new_item = Item(**item_data.model_dump())
        self.db.add(new_item)
        await self.db.commit()
        await self.db.refresh(new_item)
        return new_item
    
    # Полностью обновить элемент (PUT)
    async def update_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        item = await self.get_active_item(item_id)
        if not item:
            return None
        
        # Обновляем только переданные поля
        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        
        await self.db.commit()
        await self.db.refresh(item)
        return item
    
    # Частично обновить элемент (PATCH)
    async def patch_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        return await self.update_item(item_id, item_data)
    
    # Мягкое удаление (soft delete)
    async def delete_item(self, item_id: int) -> bool:
        item = await self.get_active_item(item_id)
        if not item:
            return False
        
        item.deleted_at = datetime.utcnow()
        await self.db.commit()
        return True