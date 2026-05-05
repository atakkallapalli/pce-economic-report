import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment, attribute_names=["user"])
        return comment

    async def get_by_id(self, comment_id: uuid.UUID) -> Comment | None:
        result = await self.db.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.id == comment_id, Comment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_task(
        self,
        task_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Comment], int]:
        base = select(Comment).where(
            Comment.task_id == task_id,
            Comment.deleted_at.is_(None),
        )
        count_result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        total = count_result.scalar_one()

        result = await self.db.execute(
            base.options(selectinload(Comment.user))
            .order_by(Comment.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def soft_delete(self, comment: Comment) -> None:
        comment.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
