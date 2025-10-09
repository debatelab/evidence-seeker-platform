from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.main import create_application
from app.models.user import User

# Test database URL
TEST_DATABASE_URL = "postgresql://test_user:test_password@localhost:5432/test_db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def test_app():
    """Create test application"""
    app = create_application()
    return app


@pytest.fixture(scope="session")
def test_client(test_app):
    """Create test client"""
    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_user(test_db: AsyncSession):
    """Create test user"""
    from passlib.context import CryptContext  # type: ignore[import-untyped]

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("testpassword123")

    user = User(
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )

    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user


@pytest.fixture(scope="function")
def auth_headers(test_user) -> dict[str, str]:
    """Create authorization headers for test user"""

    from app.core.auth import get_jwt_strategy

    strategy = get_jwt_strategy()
    token = strategy.write_token(
        {
            "sub": str(test_user.id),
            "email": test_user.email,
            "aud": "fastapi-users:auth",
        }
    )

    return {"Authorization": f"Bearer {token}"}


# Custom markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
