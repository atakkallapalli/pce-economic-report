import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.task import TaskPriority, TaskStatus
from app.schemas.user import UserBrief


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None
    assignee_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 200:
            raise ValueError("Title must be between 1 and 200 characters")
        return v


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 1 or len(v) > 200:
                raise ValueError("Title must be between 1 and 200 characters")
        return v


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


class TaskAssignRequest(BaseModel):
    assignee_id: uuid.UUID


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    creator: UserBrief
    assignee: UserBrief | None = None
    due_date: datetime | None = None
    is_overdue: bool = False
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListParams(BaseModel):
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_date_from: datetime | None = None
    due_date_to: datetime | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be >= 1")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("Page size must be between 1 and 100")
        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        allowed = {"created_at", "updated_at", "due_date", "priority", "title"}
        if v not in allowed:
            raise ValueError(f"sort_by must be one of: {', '.join(allowed)}")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class TaskSearchParams(BaseModel):
    q: str
    page: int = 1
    page_size: int = 20

    @field_validator("q")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Search query must be at least 2 characters")
        return v
