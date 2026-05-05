import uuid

import pytest
from app.schemas.comment import CommentCreateRequest
from app.schemas.task import TaskCreateRequest, TaskListParams, TaskSearchParams, TaskUpdateRequest
from app.schemas.user import UserRegisterRequest
from pydantic import ValidationError


class TestUserRegisterRequest:
    def test_valid_registration(self):
        data = UserRegisterRequest(
            email="test@example.com",
            password="ValidPass1",
            full_name="John Doe",
        )
        assert data.email == "test@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="not-an-email",
                password="ValidPass1",
                full_name="John",
            )

    def test_weak_password_no_uppercase(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                password="weakpass1",
                full_name="John",
            )

    def test_weak_password_no_digit(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                password="WeakPasss",
                full_name="John",
            )

    def test_weak_password_too_short(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                password="Ab1",
                full_name="John",
            )

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="test@example.com",
                password="ValidPass1",
                full_name="",
            )


class TestTaskCreateRequest:
    def test_valid_task(self):
        data = TaskCreateRequest(title="My Task")
        assert data.title == "My Task"
        assert data.priority.value == "MEDIUM"

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            TaskCreateRequest(title="x" * 201)

    def test_empty_title(self):
        with pytest.raises(ValidationError):
            TaskCreateRequest(title="")

    def test_title_stripped(self):
        data = TaskCreateRequest(title="  My Task  ")
        assert data.title == "My Task"

    def test_with_all_fields(self):
        data = TaskCreateRequest(
            title="Task",
            description="Description",
            priority="HIGH",
            assignee_id=uuid.uuid4(),
        )
        assert data.priority.value == "HIGH"
        assert data.description == "Description"


class TestTaskUpdateRequest:
    def test_partial_update(self):
        data = TaskUpdateRequest(title="New Title")
        assert data.title == "New Title"
        assert data.description is None

    def test_empty_update(self):
        data = TaskUpdateRequest()
        assert data.title is None


class TestTaskListParams:
    def test_defaults(self):
        params = TaskListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_invalid_page(self):
        with pytest.raises(ValidationError):
            TaskListParams(page=0)

    def test_invalid_page_size(self):
        with pytest.raises(ValidationError):
            TaskListParams(page_size=101)

    def test_invalid_sort_by(self):
        with pytest.raises(ValidationError):
            TaskListParams(sort_by="invalid")

    def test_invalid_sort_order(self):
        with pytest.raises(ValidationError):
            TaskListParams(sort_order="invalid")


class TestTaskSearchParams:
    def test_valid_search(self):
        params = TaskSearchParams(q="search term")
        assert params.q == "search term"

    def test_short_query(self):
        with pytest.raises(ValidationError):
            TaskSearchParams(q="a")


class TestCommentCreateRequest:
    def test_valid_comment(self):
        data = CommentCreateRequest(content="This is a comment")
        assert data.content == "This is a comment"

    def test_empty_comment(self):
        with pytest.raises(ValidationError):
            CommentCreateRequest(content="")

    def test_too_long_comment(self):
        with pytest.raises(ValidationError):
            CommentCreateRequest(content="x" * 5001)
