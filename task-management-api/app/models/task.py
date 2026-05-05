from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.core.database import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.task_history import TaskHistory
    from app.models.user import User


class TaskStatus(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.IN_REVIEW, TaskStatus.TODO, TaskStatus.CANCELLED},
    TaskStatus.IN_REVIEW: {TaskStatus.DONE, TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.DONE: {TaskStatus.CANCELLED},
    TaskStatus.CANCELLED: set(),
}


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.TODO,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
        index=True,
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    creator: Mapped["User"] = relationship(  # noqa: F821
        back_populates="created_tasks",
        foreign_keys=[creator_id],
    )
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="assigned_tasks",
        foreign_keys=[assignee_id],
    )
    history: Mapped[list["TaskHistory"]] = relationship(  # noqa: F821
        back_populates="task",
        order_by="TaskHistory.changed_at.desc()",
    )
    comments: Mapped[list["Comment"]] = relationship(  # noqa: F821
        back_populates="task",
    )

    @property
    def is_overdue(self) -> bool:
        if self.due_date is None:
            return False
        if self.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            return False
        return datetime.now(timezone.utc) > self.due_date
