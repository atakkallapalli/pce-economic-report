import uuid

from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        count_query = select(User).where(User.is_active.is_(True))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        query = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
