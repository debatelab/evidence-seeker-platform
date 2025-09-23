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
from app.models.permission import Permission, UserRole
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
        username="testuser",
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
            # Update existing user if they don't have a username
            if not hasattr(user_exists, "username") or user_exists.username is None:
                user_exists.username = "testuser"
                await session.commit()
                print("✅ Updated existing test user with username")

            # Check if user already has platform admin permission
            existing_permission = await session.execute(
                select(Permission).where(
                    Permission.user_id == user_exists.id,
                    Permission.role == UserRole.PLATFORM_ADMIN,
                )
            )
            permission_exists = existing_permission.scalar_one_or_none()

            if permission_exists:
                print("✅ Test user already exists with PLATFORM_ADMIN role")
                return
            else:
                # Create platform admin permission for existing user
                platform_admin_permission = Permission(
                    user_id=user_exists.id,
                    evidence_seeker_id=None,
                    role=UserRole.PLATFORM_ADMIN,
                )
                session.add(platform_admin_permission)
                await session.commit()
                print("✅ Added PLATFORM_ADMIN role to existing test user")
                return

        # Create new user
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)

        # Store user ID before creating permission
        user_id = test_user.id

        # Create platform admin permission for the test user
        platform_admin_permission = Permission(
            user_id=user_id,
            evidence_seeker_id=None,  # Platform admin doesn't need specific evidence seeker
            role=UserRole.PLATFORM_ADMIN,
        )
        session.add(platform_admin_permission)
        await session.commit()

        print(f"✅ Test user created:")
        print(f"   Email: test@example.com")
        print(f"   Username: testuser")
        print(f"   Password: evidence123")
        print(f"   User ID: {user_id}")
        print(f"   Role: PLATFORM_ADMIN")


async def main():
    """Main initialization function"""
    print("🚀 Initializing database...")
    await create_test_user()
    print("🎉 Database initialization complete!")
    print("\n📝 Test user credentials:")
    print("   Email: test@example.com")
    print("   Username: testuser")
    print("   Password: evidence123")


if __name__ == "__main__":
    asyncio.run(main())
