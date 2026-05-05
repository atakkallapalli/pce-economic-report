import uuid

from app.core.database import get_db
from app.middleware.auth import get_current_user, require_roles
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.task import TaskListParams, TaskResponse
from app.schemas.user import UserResponse
from app.services.task_service import TaskService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List users",
    description="List all active users. Manager and Admin only.",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """List all active users. Requires Manager or Admin role."""
    repo = UserRepository(db)
    users, total = await repo.list_users(page=page, page_size=page_size)
    items = [UserResponse.model_validate(u) for u in users]
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{user_id}/tasks",
    response_model=PaginatedResponse[TaskResponse],
    summary="Get user's tasks",
    description="Get all tasks assigned to a specific user.",
)
async def get_user_tasks(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tasks assigned to a user. Users can see own tasks; Managers/Admins can see anyone's."""
    params = TaskListParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    service = TaskService(db)
    return await service.get_tasks_by_user(user_id, params, current_user)
