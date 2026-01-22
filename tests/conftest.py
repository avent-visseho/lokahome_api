"""
Pytest configuration and fixtures for LOKAHOME API tests.
"""
import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_async_session
from app.core.security import get_password_hash
from app.main import app
from app.models.user import User, UserRole

# Test database URL (use a separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.unicode_string().replace(
    "/lokahome", "/lokahome_test"
)

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False,
)

# Create session factory for tests
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.
    Rolls back all changes after test completes.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create async HTTP client for testing API endpoints.
    """

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123"),
        first_name="Test",
        last_name="User",
        role=UserRole.TENANT,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_landlord(db_session: AsyncSession) -> User:
    """Create a test landlord user."""
    user = User(
        email="landlord@example.com",
        hashed_password=get_password_hash("TestPassword123"),
        first_name="Landlord",
        last_name="User",
        role=UserRole.LANDLORD,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Get authorization headers for test user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def landlord_auth_headers(test_landlord: User) -> dict[str, str]:
    """Get authorization headers for landlord user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(test_landlord.id),
            "email": test_landlord.email,
            "role": test_landlord.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(test_admin: User) -> dict[str, str]:
    """Get authorization headers for admin user."""
    from app.core.security import create_access_token

    token = create_access_token(
        data={
            "sub": str(test_admin.id),
            "email": test_admin.email,
            "role": test_admin.role.value,
        }
    )
    return {"Authorization": f"Bearer {token}"}
