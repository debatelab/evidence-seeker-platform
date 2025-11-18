from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

# Create database engines for both sync and async
# Sync engine for Alembic and other sync operations
engine = create_engine(
    settings.database_url,
    echo=settings.sqlalchemy_echo,
    future=True,
)

# Async engine for FastAPI operations (using asyncpg)
async_database_url = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_engine = create_async_engine(
    async_database_url,
    echo=settings.sqlalchemy_echo,
    future=True,
)

# Create session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)

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
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        if not settings.auto_create_schema:
            return
        Base.metadata.create_all(bind=connection)


def drop_tables() -> None:
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)


def get_db_connection_string() -> str:
    """Get database connection string for external libraries like LlamaIndex"""
    return settings.database_url
