import uuid

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.task import (
    TaskAssignRequest,
    TaskCreateRequest,
    TaskListParams,
    TaskResponse,
    TaskSearchParams,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)
from app.schemas.task_history import TaskHistoryResponse
from app.services.task_service import TaskService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a task",
    description="Create a new task with title, description, priority, and optional assignee.",
)
async def create_task(
    data: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task. Initial status is always TODO."""
    service = TaskService(db)
    return await service.create_task(data, current_user)


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks",
    description="List tasks with filtering, sorting, and pagination.",
)
async def list_tasks(
    status: TaskStatus | None = Query(None, description="Filter by status"),
    priority: TaskPriority | None = Query(None, description="Filter by priority"),
    assignee_id: uuid.UUID | None = Query(None, description="Filter by assignee"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all non-deleted tasks with optional filters and pagination."""
    params = TaskListParams(
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    service = TaskService(db)
    return await service.list_tasks(params)


@router.get(
    "/search",
    response_model=PaginatedResponse[TaskResponse],
    summary="Search tasks",
    description="Full-text search on task titles and descriptions.",
)
async def search_tasks(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search tasks by title and description using full-text search."""
    params = TaskSearchParams(q=q, page=page, page_size=page_size)
    service = TaskService(db)
    return await service.search_tasks(params)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
    description="Retrieve a single task by its unique identifier.",
)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a task by ID. Returns 404 for deleted or non-existent tasks."""
    service = TaskService(db)
    return await service.get_task(task_id)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update task fields (title, description, priority, due_date).",
)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task. Only creator, assignee, manager, or admin can update."""
    service = TaskService(db)
    return await service.update_task(task_id, data, current_user)


@router.delete(
    "/{task_id}",
    status_code=204,
    summary="Delete task",
    description="Soft delete a task. Only creator, manager, or admin can delete.",
)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a task by setting deleted_at timestamp."""
    service = TaskService(db)
    await service.delete_task(task_id, current_user)


@router.post(
    "/{task_id}/assign",
    response_model=TaskResponse,
    summary="Assign task",
    description="Assign a task to a user. Triggers notification to assignee.",
)
async def assign_task(
    task_id: uuid.UUID,
    data: TaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a task to a user by their ID."""
    service = TaskService(db)
    return await service.assign_task(task_id, data, current_user)


@router.put(
    "/{task_id}/reassign",
    response_model=TaskResponse,
    summary="Reassign task",
    description="Reassign a task to a different user. Notifies both old and new assignee.",
)
async def reassign_task(
    task_id: uuid.UUID,
    data: TaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reassign a task to a different user."""
    service = TaskService(db)
    return await service.reassign_task(task_id, data, current_user)


@router.put(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Update task status",
    description="Update task status with transition validation.",
)
async def update_status(
    task_id: uuid.UUID,
    data: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task status. Validates transitions per workflow rules."""
    service = TaskService(db)
    return await service.update_status(task_id, data, current_user)


@router.get(
    "/{task_id}/history",
    response_model=list[TaskHistoryResponse],
    summary="Get task history",
    description="Get the full status change history for a task.",
)
async def get_task_history(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chronological history of all changes to a task."""
    service = TaskService(db)
    return await service.get_task_history(task_id)
