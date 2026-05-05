import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task_history import TaskHistory


class TaskHistoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, history: TaskHistory) -> TaskHistory:
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_by_task(self, task_id: uuid.UUID) -> list[TaskHistory]:
        result = await self.db.execute(
            select(TaskHistory)
            .options(selectinload(TaskHistory.user))
            .where(TaskHistory.task_id == task_id)
            .order_by(TaskHistory.changed_at.desc())
        )
        return list(result.scalars().all())
