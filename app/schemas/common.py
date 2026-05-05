from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database: str = "unknown"
    redis: str = "unknown"
    rabbitmq: str = "unknown"
