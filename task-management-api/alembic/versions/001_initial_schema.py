"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "MANAGER", "MEMBER", name="user_role"),
            nullable=False,
            server_default="MEMBER",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("TODO", "IN_PROGRESS", "IN_REVIEW", "DONE", "CANCELLED", name="task_status"),
            nullable=False,
            server_default="TODO",
        ),
        sa.Column(
            "priority",
            sa.Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="task_priority"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
    )
    op.create_index(
        "idx_tasks_status", "tasks", ["status"], postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        "idx_tasks_priority", "tasks", ["priority"], postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        "idx_tasks_assignee",
        "tasks",
        ["assignee_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_tasks_creator", "tasks", ["creator_id"], postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        "idx_tasks_due_date", "tasks", ["due_date"], postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        "idx_tasks_created_at",
        "tasks",
        [sa.text("created_at DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "task_history",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("changed_by", sa.UUID(), nullable=False),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=True),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"]),
    )
    op.create_index("idx_history_task", "task_history", ["task_id", sa.text("changed_at DESC")])

    op.create_table(
        "comments",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "idx_comments_task",
        "comments",
        ["task_id", "created_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_comments_user", "comments", ["user_id"], postgresql_where=sa.text("deleted_at IS NULL")
    )


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_table("task_history")
    op.drop_table("tasks")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS task_priority")
