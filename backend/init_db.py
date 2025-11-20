#!/usr/bin/env python3
"""
Database initialization script used in development.
Creates or syncs the default test user with platform admin access.
"""

import asyncio
import logging

from app.core.bootstrap import AdminBootstrapConfig, bootstrap_platform_admin

# Suppress the bcrypt version warning from passlib
logging.getLogger("passlib").setLevel(logging.ERROR)

TEST_ADMIN_CONFIG = AdminBootstrapConfig(
    email="test@example.com",
    password="evidence123",
    username="testuser",
    is_active=True,
    is_superuser=True,
    is_verified=True,
)


async def main() -> None:
    """Create or update the local test admin account."""
    print("🚀 Initializing development test user...")
    created = await bootstrap_platform_admin(
        TEST_ADMIN_CONFIG,
        require_empty_db=False,
    )
    if created:
        print("✅ Test user created:")
    else:
        print("✅ Test user synchronized:")
    print("   Email: test@example.com")
    print("   Username: testuser")
    print("   Password: evidence123")
    print("   Role: PLATFORM_ADMIN")


if __name__ == "__main__":
    asyncio.run(main())
