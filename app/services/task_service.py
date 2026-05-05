import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.rabbitmq import publish_notification
from app.models.task import VALID_TRANSITIONS, Task, TaskStatus
from app.models.task_history import TaskHistory
from app.models.user import User, UserRole
from app.repositories.task_history_repo import TaskHistoryRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.user_repo import UserRepository
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
from app.schemas.user import UserBrief

logger = get_logger(__name__)


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.history_repo = TaskHistoryRepository(db)
        self.user_repo = UserRepository(db)

    async def create_task(self, data: TaskCreateRequest, current_user: User) -> TaskResponse:
        if data.assignee_id:
            assignee = await self.user_repo.get_by_id(data.assignee_id)
            if not assignee or not assignee.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee not found or inactive",
                )

        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            creator_id=current_user.id,
            assignee_id=data.assignee_id,
            status=TaskStatus.TODO,
        )
        task = await self.task_repo.create(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                new_status=TaskStatus.TODO.value,
                change_type="CREATED",
            )
        )

        if data.assignee_id:
            assignee_user = await self.user_repo.get_by_id(data.assignee_id)
            await publish_notification(
                "task_assigned",
                {
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assignee_id": str(data.assignee_id),
                    "assignee_email": assignee_user.email if assignee_user else "",
                    "assigned_by": current_user.full_name,
                },
            )

        logger.info("task_created", task_id=str(task.id), creator=str(current_user.id))
        return await self._to_response(task)

    async def get_task(self, task_id: uuid.UUID) -> TaskResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return await self._to_response(task)

    async def update_task(
        self,
        task_id: uuid.UUID,
        data: TaskUpdateRequest,
        current_user: User,
    ) -> TaskResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._check_task_permission(task, current_user, "update")

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(task, field, value)

        task = await self.task_repo.update(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                change_type="UPDATED",
                details=json.dumps(list(update_fields.keys())),
            )
        )

        logger.info("task_updated", task_id=str(task_id))
        return await self._to_response(task)

    async def delete_task(self, task_id: uuid.UUID, current_user: User) -> None:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._check_task_permission(task, current_user, "delete")
        await self.task_repo.soft_delete(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                change_type="DELETED",
            )
        )
        logger.info("task_deleted", task_id=str(task_id))

    async def list_tasks(self, params: TaskListParams) -> PaginatedResponse[TaskResponse]:
        tasks, total = await self.task_repo.list_tasks(
            status=params.status,
            priority=params.priority,
            assignee_id=params.assignee_id,
            due_date_from=params.due_date_from,
            due_date_to=params.due_date_to,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            page=params.page,
            page_size=params.page_size,
        )
        items = [await self._to_response(t) for t in tasks]
        pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )

    async def search_tasks(self, params: TaskSearchParams) -> PaginatedResponse[TaskResponse]:
        tasks, total = await self.task_repo.search(
            query_text=params.q,
            page=params.page,
            page_size=params.page_size,
        )
        items = [await self._to_response(t) for t in tasks]
        pages = (total + params.page_size - 1) // params.page_size if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
        )

    async def assign_task(
        self,
        task_id: uuid.UUID,
        data: TaskAssignRequest,
        current_user: User,
    ) -> TaskResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._check_task_permission(task, current_user, "assign")

        assignee = await self.user_repo.get_by_id(data.assignee_id)
        if not assignee or not assignee.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee not found or inactive",
            )

        task.assignee_id = data.assignee_id
        task = await self.task_repo.update(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                change_type="ASSIGNMENT",
                details=json.dumps({"assignee_id": str(data.assignee_id)}),
            )
        )

        await publish_notification(
            "task_assigned",
            {
                "task_id": str(task.id),
                "task_title": task.title,
                "assignee_id": str(data.assignee_id),
                "assignee_email": assignee.email,
                "assigned_by": current_user.full_name,
            },
        )

        logger.info("task_assigned", task_id=str(task_id), assignee=str(data.assignee_id))
        return await self._to_response(task)

    async def reassign_task(
        self,
        task_id: uuid.UUID,
        data: TaskAssignRequest,
        current_user: User,
    ) -> TaskResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._check_task_permission(task, current_user, "assign")

        old_assignee_id = task.assignee_id
        assignee = await self.user_repo.get_by_id(data.assignee_id)
        if not assignee or not assignee.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee not found or inactive",
            )

        task.assignee_id = data.assignee_id
        task = await self.task_repo.update(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                change_type="REASSIGNMENT",
                details=json.dumps(
                    {
                        "old_assignee_id": str(old_assignee_id) if old_assignee_id else None,
                        "new_assignee_id": str(data.assignee_id),
                    }
                ),
            )
        )

        await publish_notification(
            "task_reassigned",
            {
                "task_id": str(task.id),
                "task_title": task.title,
                "old_assignee_id": str(old_assignee_id) if old_assignee_id else None,
                "new_assignee_id": str(data.assignee_id),
                "assignee_email": assignee.email,
                "reassigned_by": current_user.full_name,
            },
        )

        logger.info("task_reassigned", task_id=str(task_id))
        return await self._to_response(task)

    async def update_status(
        self,
        task_id: uuid.UUID,
        data: TaskStatusUpdateRequest,
        current_user: User,
    ) -> TaskResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        self._check_task_permission(task, current_user, "update")

        allowed = VALID_TRANSITIONS.get(task.status, set())
        if data.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from {task.status.value} to {data.status.value}. "
                f"Allowed transitions: {', '.join(s.value for s in allowed) or 'none'}",
            )

        old_status = task.status
        task.status = data.status
        task = await self.task_repo.update(task)

        await self.history_repo.create(
            TaskHistory(
                task_id=task.id,
                changed_by=current_user.id,
                old_status=old_status.value,
                new_status=data.status.value,
                change_type="STATUS_CHANGE",
            )
        )

        creator = await self.user_repo.get_by_id(task.creator_id)
        assignee = await self.user_repo.get_by_id(task.assignee_id) if task.assignee_id else None
        await publish_notification(
            "status_changed",
            {
                "task_id": str(task.id),
                "task_title": task.title,
                "old_status": old_status.value,
                "new_status": data.status.value,
                "changed_by": current_user.full_name,
                "creator_id": str(task.creator_id),
                "creator_email": creator.email if creator else "",
                "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                "assignee_email": assignee.email if assignee else "",
            },
        )

        logger.info(
            "task_status_changed",
            task_id=str(task_id),
            old_status=old_status.value,
            new_status=data.status.value,
        )
        return await self._to_response(task)

    async def get_task_history(self, task_id: uuid.UUID) -> list[TaskHistoryResponse]:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        history = await self.history_repo.get_by_task(task_id)
        return [
            TaskHistoryResponse(
                id=h.id,
                task_id=h.task_id,
                changed_by_user=UserBrief.model_validate(h.user),
                old_status=h.old_status,
                new_status=h.new_status,
                change_type=h.change_type,
                details=h.details,
                changed_at=h.changed_at,
            )
            for h in history
        ]

    async def get_tasks_by_user(
        self,
        user_id: uuid.UUID,
        params: TaskListParams,
        current_user: User,
    ) -> PaginatedResponse[TaskResponse]:
        if (
            current_user.role not in (UserRole.ADMIN, UserRole.MANAGER)
            and current_user.id != user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this user's tasks",
            )

        params.assignee_id = user_id
        return await self.list_tasks(params)

    def _check_task_permission(self, task: Task, user: User, action: str) -> None:
        if user.role in (UserRole.ADMIN, UserRole.MANAGER):
            return

        if action == "update":
            if task.creator_id != user.id and task.assignee_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this task",
                )
        elif action == "delete":
            if task.creator_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete this task",
                )
        elif action == "assign":
            if task.creator_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to assign this task",
                )

    async def _to_response(self, task: Task) -> TaskResponse:
        comment_count = await self.task_repo.get_comment_count(task.id)
        creator_brief = UserBrief.model_validate(task.creator)
        assignee_brief = UserBrief.model_validate(task.assignee) if task.assignee else None

        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            creator=creator_brief,
            assignee=assignee_brief,
            due_date=task.due_date,
            is_overdue=task.is_overdue,
            comment_count=comment_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
