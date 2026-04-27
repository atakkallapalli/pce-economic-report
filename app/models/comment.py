from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
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

    task: Mapped["Task"] = relationship(back_populates="comments")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="comments")  # noqa: F821
