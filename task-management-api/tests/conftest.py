import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import timezone  # noqa: F401
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from app.core.database import Base, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.comment import Comment
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.task_history import TaskHistory  # noqa: F401
from app.models.user import User, UserRole
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.core.rabbitmq.publish_notification", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        password_hash=hash_password("TestPass123"),
        full_name="Test User",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        password_hash=hash_password("AdminPass123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_manager(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager@example.com",
        password_hash=hash_password("ManagerPass123"),
        full_name="Manager User",
        role=UserRole.MANAGER,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_user: User) -> Task:
    task = Task(
        id=uuid.uuid4(),
        title="Test Task",
        description="Test task description",
        creator_id=test_user.id,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_comment(db_session: AsyncSession, test_task: Task, test_user: User) -> Comment:
    comment = Comment(
        id=uuid.uuid4(),
        task_id=test_task.id,
        user_id=test_user.id,
        content="Test comment content",
    )
    db_session.add(comment)
    await db_session.flush()
    await db_session.refresh(comment)
    return comment


def make_auth_header(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}
