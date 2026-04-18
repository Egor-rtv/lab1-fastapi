from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from app.models import Item, User, RefreshToken
from app.schemas import ItemCreate, ItemUpdate, PaginationParams


# ==================== ITEM SERVICES ====================

class ItemService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_item(self, item_id: int) -> Optional[Item]:
        result = await self.db.execute(
            select(Item).where(
                Item.id == item_id,
                Item.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_active_items(self, pagination: PaginationParams) -> Tuple[list[Item], int]:
        count_query = select(func.count()).select_from(Item).where(Item.deleted_at.is_(None))
        total = await self.db.scalar(count_query)
        
        query = select(Item).where(Item.deleted_at.is_(None))
        query = query.offset(pagination.offset).limit(pagination.limit)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def create_item(self, item_data: ItemCreate) -> Item:
        new_item = Item(**item_data.model_dump())
        self.db.add(new_item)
        await self.db.commit()
        await self.db.refresh(new_item)
        return new_item
    
    async def update_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        item = await self.get_active_item(item_id)
        if not item:
            return None
        
        update_data = item_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        
        await self.db.commit()
        await self.db.refresh(item)
        return item
    
    async def patch_item(self, item_id: int, item_data: ItemUpdate) -> Optional[Item]:
        return await self.update_item(item_id, item_data)
    
    async def delete_item(self, item_id: int) -> bool:
        item = await self.get_active_item(item_id)
        if not item:
            return False
        
        item.deleted_at = datetime.utcnow()
        await self.db.commit()
        return True


# ==================== AUTH SERVICES ====================

class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Найти пользователя по email"""
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Найти пользователя по ID"""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, email: str, password_hash: str) -> User:
        """Создать нового пользователя"""
        new_user = User(
            email=email,
            password_hash=password_hash
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user
    async def get_user_by_yandex_id(self, yandex_id: str) -> Optional[User]:
        """Найти пользователя по yandex_id"""
        result = await self.db.execute(
            select(User).where(
                User.yandex_id == yandex_id,
                User.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()


    async def create_user_yandex(self, email: str, yandex_id: str) -> User:
        """Создать пользователя через Yandex OAuth (без пароля)"""
        new_user = User(
            email=email,
            yandex_id=yandex_id,
            password_hash=None  # У OAuth-пользователя нет пароля
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return new_user


class RefreshTokenService:
    """Сервис для работы с Refresh токенами"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_token(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        """Сохранить Refresh токен в БД"""
        new_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(new_token)
        await self.db.commit()
        await self.db.refresh(new_token)
        return new_token
    
    async def get_active_token(self, token_hash: str) -> Optional[RefreshToken]:
        """Найти активный (не отозванный и не просроченный) токен"""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now
            )
        )
        return result.scalar_one_or_none()
    
    async def revoke_token(self, token: RefreshToken) -> None:
        """Отозвать конкретный токен"""
        token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
    
    async def revoke_all_user_tokens(self, user_id: int) -> None:
        """Отозвать все токены пользователя"""
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.db.commit()