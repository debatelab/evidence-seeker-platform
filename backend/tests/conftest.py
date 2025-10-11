import os
import time
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:  # for type checkers only; avoids runtime import side effects
    from app.models.user import User

"""
Unified Test DB strategy (Postgres-only):
- Always use PostgreSQL for tests, locally and in CI.
- If DATABASE_URL isn't set, default to the docker-compose test DB on port 5433.
- Async engine uses asyncpg driver; sync engine uses standard psycopg driver.
"""

# Default to local docker-compose test_db service if env var is not provided
DEFAULT_TEST_DB = (
    "postgresql://evidence_user:evidence_password@localhost:5433/evidence_seeker_test"
)

RAW_DATABASE_URL = os.getenv("DATABASE_URL") or DEFAULT_TEST_DB

# Ensure DEBUG=true in tests so TrustedHostMiddleware is not enforced (TestClient uses 'testserver')
os.environ.setdefault("DEBUG", "true")

# Disable embeddings during tests to avoid downloading/loading heavy models
os.environ.setdefault("DISABLE_EMBEDDINGS", "true")

if not RAW_DATABASE_URL.startswith("postgresql://"):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL URL (postgresql://). SQLite is no longer supported in tests."
    )

# Ensure the application picks up the same DB URL (affects engines created at import time)
os.environ["DATABASE_URL"] = RAW_DATABASE_URL

from app.core.database import Base  # noqa: E402  now safe to import

# Build async URL matching RAW_DATABASE_URL
ASYNC_DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create test engine (async)
test_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    future=True,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)

# Create synchronous engine/session for tests that expect sync Session
SYNC_DATABASE_URL = RAW_DATABASE_URL
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    future=True,
)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def _import_all_models() -> None:
    """Import all model modules so SQLAlchemy registers tables on Base.metadata."""
    # Local imports avoid side effects at module import time
    import importlib

    modules = [
        "app.models.user",
        "app.models.permission",
        "app.models.evidence_seeker",
        "app.models.document",
        "app.models.embedding",
        "app.models.api_key",
        "app.models.game",
    ]
    for m in modules:
        importlib.import_module(m)


def _wait_for_db(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    """Wait for Postgres to accept connections."""
    last_exc: Exception | None = None
    for _ in range(max_attempts):
        try:
            with sync_engine.connect() as _:
                return
        except Exception as exc:  # pragma: no cover - only on startup
            last_exc = exc
            time.sleep(delay_seconds)
    if last_exc:
        raise last_exc


def _truncate_all_sync() -> None:
    """Truncate all tables and reset identities (sync)."""
    try:
        # Close all existing connections to prevent deadlocks
        sync_engine.dispose()

        with sync_engine.begin() as conn:
            # Disable triggers for faster truncation if necessary; here we just run TRUNCATE
            table_names = [t.name for t in Base.metadata.sorted_tables]
            if table_names:
                conn.exec_driver_sql(
                    "TRUNCATE TABLE "
                    + ", ".join(f'"{name}"' for name in table_names)
                    + " RESTART IDENTITY CASCADE"
                )
    except Exception as e:
        # Log error but don't fail the test suite
        print(f"Warning: Database cleanup failed: {e}")


async def _truncate_all_async() -> None:
    """Truncate all tables and reset identities (async)."""
    try:
        # Close all existing connections to prevent deadlocks
        await test_engine.dispose()

        async with test_engine.begin() as conn:
            table_names = [t.name for t in Base.metadata.sorted_tables]
            if table_names:
                await conn.exec_driver_sql(
                    "TRUNCATE TABLE "
                    + ", ".join(f'"{name}"' for name in table_names)
                    + " RESTART IDENTITY CASCADE"
                )
    except Exception as e:
        # Log error but don't fail the test suite
        print(f"Warning: Async database cleanup failed: {e}")


@pytest.fixture(autouse=True, scope="function")
def _auto_clean_db() -> None:
    """Ensure a clean database state for every test, even if it doesn't request a DB fixture.

    Creates schema (idempotent), ensures pgvector extension exists, and truncates all tables.
    """
    _import_all_models()
    _wait_for_db()
    with sync_engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(bind=conn)
    _truncate_all_sync()


@pytest.fixture(scope="function")
def test_app():
    """Create test application with DB dependency overrides bound to test engines."""
    # Defer heavy import until the fixture is actually used
    from sqlalchemy import text

    # Ensure DB is ready and pgvector extension is enabled before app startup creates tables
    _wait_for_db()
    with sync_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Import models so Base.metadata is populated for create_tables()
    _import_all_models()

    from app.core.database import get_async_db, get_db
    from app.main import create_application

    app = create_application()

    # Create fresh engines for each test to avoid connection conflicts
    async_test_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=None,  # Disable pooling for tests
    )

    async_test_session_local = async_sessionmaker(
        bind=async_test_engine, expire_on_commit=False
    )

    sync_test_engine = create_engine(
        SYNC_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=None,  # Disable pooling for tests
    )

    sync_test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=sync_test_engine
    )

    async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_test_session_local() as session:
            try:
                yield session
            finally:
                await session.close()

    def override_get_db() -> Generator[Session, None, None]:
        session = sync_test_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_db] = override_get_db

    # Store engines on app for cleanup
    app.state._test_engines = {"async": async_test_engine, "sync": sync_test_engine}

    return app


@pytest.fixture(scope="function")
def test_client(test_app):
    """Create test client"""
    try:
        with TestClient(test_app) as client:
            yield client
    finally:
        # Clean up test engines
        if hasattr(test_app.state, "_test_engines"):
            import asyncio

            if "async" in test_app.state._test_engines:
                asyncio.run(test_app.state._test_engines["async"].dispose())
            if "sync" in test_app.state._test_engines:
                test_app.state._test_engines["sync"].dispose()


@pytest.fixture(scope="function")
def client(test_app):
    """Alias fixture for tests expecting 'client' name."""
    try:
        with TestClient(test_app) as client:
            yield client
    finally:
        # Clean up test engines
        if hasattr(test_app.state, "_test_engines"):
            import asyncio

            if "async" in test_app.state._test_engines:
                asyncio.run(test_app.state._test_engines["async"].dispose())
            if "sync" in test_app.state._test_engines:
                test_app.state._test_engines["sync"].dispose()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Async DB session with per-test cleanup (truncate)."""
    # Ensure schema exists (idempotent)
    _import_all_models()
    _wait_for_db()
    async with test_engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)
    # Truncate data for isolation
    await _truncate_all_async()

    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Sync DB session with per-test cleanup (truncate)."""
    # Ensure tables exist (idempotent)
    _import_all_models()
    _wait_for_db()
    with sync_engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        Base.metadata.create_all(bind=conn)
    # Truncate data for isolation
    _truncate_all_sync()
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        # No drop_all — keep schema for the app across tests


@pytest.fixture(scope="function")
def test_user(db: Session):
    """Create test user (sync)"""
    from passlib.context import CryptContext

    from app.models.user import User as UserModel

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    # Match the password used across tests when logging in
    hashed_password = pwd_context.hash("testpassword")

    user = UserModel(
        email="test@example.com",
        username="testuser",
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@pytest.fixture(scope="function")
def test_evidence_seeker(db: Session, test_user: "User"):
    """Create a basic evidence seeker owned by test_user."""
    from app.models.evidence_seeker import EvidenceSeeker

    seeker = EvidenceSeeker(title="Test Seeker", created_by=test_user.id)
    db.add(seeker)
    db.commit()
    db.refresh(seeker)
    return seeker


@pytest.fixture(scope="function")
def auth_headers(test_user, test_client: TestClient) -> dict[str, str]:
    """Create authorization headers for test user by logging in via API."""
    resp = test_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": test_user.email, "password": "testpassword"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def other_user(db: Session):
    """Create a second user to represent a different owner (for FK correctness)."""
    from passlib.context import CryptContext

    from app.models.user import User as UserModel

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("otherpassword")

    user = UserModel(
        email="other@example.com",
        username="otheruser",
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Custom markers
@pytest.fixture(autouse=True)
def disable_email_service(monkeypatch):
    """Disable email service in tests to prevent hanging on email sends."""

    # Mock the EmailService class to prevent any SMTP connections
    class MockEmailService:
        def __init__(self, *args, **kwargs):
            pass

        async def send_verification_email(self, *args, **kwargs):
            pass

        async def send_password_reset_email(self, *args, **kwargs):
            pass

    # Mock both the EmailService constructor and the get_email_service function
    monkeypatch.setattr("app.core.auth.EmailService", MockEmailService)
    monkeypatch.setattr("app.core.auth.get_email_service", lambda: MockEmailService())
    monkeypatch.setattr("app.core.email_service.EmailService", MockEmailService)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
