import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskHistory(Base):
    __tablename__ = "task_history"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    old_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    task: Mapped["Task"] = relationship(back_populates="history")  # noqa: F821
    user: Mapped["User"] = relationship()  # noqa: F821
