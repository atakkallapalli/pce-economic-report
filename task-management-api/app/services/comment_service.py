import uuid

from app.core.logging import get_logger
from app.models.comment import Comment
from app.models.user import User, UserRole
from app.repositories.comment_repo import CommentRepository
from app.repositories.task_repo import TaskRepository
from app.schemas.comment import CommentCreateRequest, CommentResponse
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserBrief
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class CommentService:
    def __init__(self, db: AsyncSession) -> None:
        self.comment_repo = CommentRepository(db)
        self.task_repo = TaskRepository(db)

    async def create_comment(
        self,
        task_id: uuid.UUID,
        data: CommentCreateRequest,
        current_user: User,
    ) -> CommentResponse:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        comment = Comment(
            task_id=task_id,
            user_id=current_user.id,
            content=data.content,
        )
        comment = await self.comment_repo.create(comment)

        logger.info(
            "comment_created",
            comment_id=str(comment.id),
            task_id=str(task_id),
        )
        return self._to_response(comment)

    async def list_comments(
        self,
        task_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CommentResponse]:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        comments, total = await self.comment_repo.list_by_task(
            task_id=task_id,
            page=page,
            page_size=page_size,
        )
        items = [self._to_response(c) for c in comments]
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def delete_comment(
        self,
        task_id: uuid.UUID,
        comment_id: uuid.UUID,
        current_user: User,
    ) -> None:
        comment = await self.comment_repo.get_by_id(comment_id)
        if not comment or comment.task_id != task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )

        if current_user.role != UserRole.ADMIN and comment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment",
            )

        await self.comment_repo.soft_delete(comment)
        logger.info("comment_deleted", comment_id=str(comment_id))

    def _to_response(self, comment: Comment) -> CommentResponse:
        return CommentResponse(
            id=comment.id,
            task_id=comment.task_id,
            author=UserBrief.model_validate(comment.user),
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
