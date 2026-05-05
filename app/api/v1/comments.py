import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.comment import CommentCreateRequest, CommentResponse
from app.schemas.common import PaginatedResponse
from app.services.comment_service import CommentService

router = APIRouter(prefix="/tasks/{task_id}/comments", tags=["Comments"])


@router.post(
    "",
    response_model=CommentResponse,
    status_code=201,
    summary="Add comment",
    description="Add a comment to a task.",
)
async def create_comment(
    task_id: uuid.UUID,
    data: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a task. Any authenticated user can comment."""
    service = CommentService(db)
    return await service.create_comment(task_id, data, current_user)


@router.get(
    "",
    response_model=PaginatedResponse[CommentResponse],
    summary="List comments",
    description="List all comments for a task with pagination.",
)
async def list_comments(
    task_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all non-deleted comments for a task in chronological order."""
    service = CommentService(db)
    return await service.list_comments(task_id, page, page_size)


@router.delete(
    "/{comment_id}",
    status_code=204,
    summary="Delete comment",
    description="Soft delete a comment. Only author or admin can delete.",
)
async def delete_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a comment. Only comment author or admin can delete."""
    service = CommentService(db)
    await service.delete_comment(task_id, comment_id, current_user)
