#!/usr/bin/env python3
"""
Database initialization script.
Creates a test user for development purposes.
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

# Suppress the bcrypt version warning from passlib
logging.getLogger("passlib").setLevel(logging.ERROR)

from app.core.database import async_engine, Base
from app.models.user import User
from app.core.config import settings


# Tables are now created by Alembic migrations
# This function is no longer needed


async def create_test_user():
    """Create a test user for development"""
    from sqlalchemy import text, select

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash("evidence123")

    test_user = User(
        email="test@example.com",
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )

    async with AsyncSession(async_engine) as session:
        # Check if user already exists using proper ORM query
        existing_user = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user_exists = existing_user.scalar_one_or_none()

        if user_exists:
            print("✅ Test user already exists")
            return

        # Create new user
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)

        print(f"✅ Test user created:")
        print(f"   Email: test@example.com")
        print(f"   Password: evidence123")
        print(f"   User ID: {test_user.id}")


async def main():
    """Main initialization function"""
    print("🚀 Initializing database...")
    await create_test_user()
    print("🎉 Database initialization complete!")
    print("\n📝 Test user credentials:")
    print("   Email: test@example.com")
    print("   Password: evidence123")


if __name__ == "__main__":
    asyncio.run(main())
