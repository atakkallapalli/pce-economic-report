import uuid
from datetime import datetime

from app.schemas.user import UserBrief
from pydantic import BaseModel


class TaskHistoryResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    changed_by_user: UserBrief
    old_status: str | None = None
    new_status: str | None = None
    change_type: str
    details: str | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}
