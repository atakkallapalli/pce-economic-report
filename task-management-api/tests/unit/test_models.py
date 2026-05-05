import uuid
from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401

from app.models.task import VALID_TRANSITIONS, Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole


class TestUserModel:
    def test_user_role_values(self):
        assert UserRole.ADMIN.value == "ADMIN"
        assert UserRole.MANAGER.value == "MANAGER"
        assert UserRole.MEMBER.value == "MEMBER"

    def test_user_defaults(self):
        user = User(
            email="test@example.com",
            password_hash="hash",
            full_name="Test",
            role=UserRole.MEMBER,
            is_active=True,
        )
        assert user.role == UserRole.MEMBER
        assert user.is_active is True


class TestTaskModel:
    def test_task_status_values(self):
        assert TaskStatus.TODO.value == "TODO"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.IN_REVIEW.value == "IN_REVIEW"
        assert TaskStatus.DONE.value == "DONE"
        assert TaskStatus.CANCELLED.value == "CANCELLED"

    def test_task_priority_values(self):
        assert TaskPriority.LOW.value == "LOW"
        assert TaskPriority.MEDIUM.value == "MEDIUM"
        assert TaskPriority.HIGH.value == "HIGH"
        assert TaskPriority.URGENT.value == "URGENT"

    def test_valid_transitions_from_todo(self):
        allowed = VALID_TRANSITIONS[TaskStatus.TODO]
        assert TaskStatus.IN_PROGRESS in allowed
        assert TaskStatus.CANCELLED in allowed
        assert TaskStatus.DONE not in allowed

    def test_valid_transitions_from_in_progress(self):
        allowed = VALID_TRANSITIONS[TaskStatus.IN_PROGRESS]
        assert TaskStatus.IN_REVIEW in allowed
        assert TaskStatus.TODO in allowed
        assert TaskStatus.CANCELLED in allowed

    def test_valid_transitions_from_in_review(self):
        allowed = VALID_TRANSITIONS[TaskStatus.IN_REVIEW]
        assert TaskStatus.DONE in allowed
        assert TaskStatus.IN_PROGRESS in allowed
        assert TaskStatus.CANCELLED in allowed

    def test_valid_transitions_from_done(self):
        allowed = VALID_TRANSITIONS[TaskStatus.DONE]
        assert TaskStatus.CANCELLED in allowed
        assert len(allowed) == 1

    def test_valid_transitions_from_cancelled(self):
        allowed = VALID_TRANSITIONS[TaskStatus.CANCELLED]
        assert len(allowed) == 0

    def test_is_overdue_no_due_date(self):
        task = Task(
            title="Test",
            creator_id=uuid.uuid4(),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
        assert task.is_overdue is False

    def test_is_overdue_future_date(self):
        task = Task(
            title="Test",
            creator_id=uuid.uuid4(),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.now(timezone.utc) + timedelta(days=1),
        )
        assert task.is_overdue is False

    def test_is_overdue_past_date(self):
        task = Task(
            title="Test",
            creator_id=uuid.uuid4(),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert task.is_overdue is True

    def test_is_overdue_done_task(self):
        task = Task(
            title="Test",
            creator_id=uuid.uuid4(),
            status=TaskStatus.DONE,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert task.is_overdue is False

    def test_is_overdue_cancelled_task(self):
        task = Task(
            title="Test",
            creator_id=uuid.uuid4(),
            status=TaskStatus.CANCELLED,
            priority=TaskPriority.MEDIUM,
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert task.is_overdue is False
