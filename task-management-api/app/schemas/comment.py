import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.user import UserBrief


class CommentCreateRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 5000:
            raise ValueError("Comment must be between 1 and 5000 characters")
        return v


class CommentResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author: UserBrief
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
