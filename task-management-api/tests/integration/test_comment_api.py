import uuid

import pytest  # noqa: F401
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from httpx import AsyncClient
from tests.conftest import make_auth_header


class TestCommentCRUD:
    async def test_create_comment(self, client: AsyncClient, test_user: User, test_task: Task):
        headers = make_auth_header(test_user)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
            json={"content": "This is a comment"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "This is a comment"
        assert data["author"]["email"] == "testuser@example.com"

    async def test_create_comment_nonexistent_task(self, client: AsyncClient, test_user: User):
        headers = make_auth_header(test_user)
        response = await client.post(
            f"/api/v1/tasks/{uuid.uuid4()}/comments",
            headers=headers,
            json={"content": "Comment"},
        )
        assert response.status_code == 404

    async def test_create_comment_empty(
        self, client: AsyncClient, test_user: User, test_task: Task
    ):
        headers = make_auth_header(test_user)
        response = await client.post(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
            json={"content": ""},
        )
        assert response.status_code == 422

    async def test_list_comments(
        self, client: AsyncClient, test_user: User, test_task: Task, test_comment: Comment
    ):
        headers = make_auth_header(test_user)
        response = await client.get(
            f"/api/v1/tasks/{test_task.id}/comments",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_delete_comment_by_author(
        self, client: AsyncClient, test_user: User, test_task: Task, test_comment: Comment
    ):
        headers = make_auth_header(test_user)
        response = await client.delete(
            f"/api/v1/tasks/{test_task.id}/comments/{test_comment.id}",
            headers=headers,
        )
        assert response.status_code == 204

    async def test_delete_comment_by_admin(
        self, client: AsyncClient, test_admin: User, test_task: Task, test_comment: Comment
    ):
        headers = make_auth_header(test_admin)
        response = await client.delete(
            f"/api/v1/tasks/{test_task.id}/comments/{test_comment.id}",
            headers=headers,
        )
        assert response.status_code == 204

    async def test_delete_comment_unauthorized(
        self, client: AsyncClient, test_manager: User, test_task: Task, test_comment: Comment
    ):
        headers = make_auth_header(test_manager)
        response = await client.delete(
            f"/api/v1/tasks/{test_task.id}/comments/{test_comment.id}",
            headers=headers,
        )
        assert response.status_code == 403
