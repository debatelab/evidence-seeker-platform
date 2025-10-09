from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

# Create database engines for both sync and async
# Sync engine for Alembic and other sync operations
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

# Async engine for FastAPI operations (using asyncpg)
async_database_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_engine = create_async_engine(
    async_database_url,
    echo=settings.debug,
    future=True,
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Sync database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_tables() -> None:
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)


def get_db_connection_string() -> str:
    """Get database connection string for external libraries like LlamaIndex"""
    return settings.database_url
