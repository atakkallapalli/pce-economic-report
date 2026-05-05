import uuid
from datetime import datetime, timezone

from app.models.comment import Comment
from app.models.task import Task, TaskPriority, TaskStatus
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class TaskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task, attribute_names=["creator", "assignee"])
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.creator),
                selectinload(Task.assignee),
            )
            .where(Task.id == task_id, Task.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def update(self, task: Task) -> Task:
        task.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(task, attribute_names=["creator", "assignee"])
        return task

    async def soft_delete(self, task: Task) -> None:
        task.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: uuid.UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        base_query = select(Task).where(Task.deleted_at.is_(None))

        if status is not None:
            base_query = base_query.where(Task.status == status)
        if priority is not None:
            base_query = base_query.where(Task.priority == priority)
        if assignee_id is not None:
            base_query = base_query.where(Task.assignee_id == assignee_id)
        if due_date_from is not None:
            base_query = base_query.where(Task.due_date >= due_date_from)
        if due_date_to is not None:
            base_query = base_query.where(Task.due_date <= due_date_to)

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        sort_column = getattr(Task, sort_by, Task.created_at)
        if sort_order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

        query = (
            base_query.options(
                selectinload(Task.creator),
                selectinload(Task.assignee),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def search(
        self,
        query_text: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        search_query = select(Task).where(
            Task.deleted_at.is_(None),
            text(
                "to_tsvector('english', tasks.title || ' ' || COALESCE(tasks.description, '')) "
                "@@ plainto_tsquery('english', :q)"
            ),
        )

        count_result = await self.db.execute(
            select(func.count()).select_from(search_query.params(q=query_text).subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            search_query.params(q=query_text)
            .options(
                selectinload(Task.creator),
                selectinload(Task.assignee),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_comment_count(self, task_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                Comment.task_id == task_id,
                Comment.deleted_at.is_(None),
            )
        )
        return result.scalar_one()
