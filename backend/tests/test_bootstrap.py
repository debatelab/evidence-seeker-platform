import pytest
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bootstrap import AdminBootstrapConfig, bootstrap_platform_admin
from app.models.permission import Permission, UserRole
from app.models.user import User, build_user

USER_EMAIL_COLUMN = User.__table__.c.email


def _hash(password: str) -> str:
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.hash(password)


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_when_empty(test_db: AsyncSession) -> None:
    config = AdminBootstrapConfig(
        email="bootstrap@example.com",
        password="SecurePass123",
        username="bootstrap_admin",
    )

    created = await bootstrap_platform_admin(
        config, require_empty_db=True, session=test_db
    )

    assert created
    result = await test_db.execute(
        select(User).where(USER_EMAIL_COLUMN == config.email)
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.username == "bootstrap_admin"
    assert user.is_superuser is True
    assert user.is_verified is True

    perm_result = await test_db.execute(
        select(Permission).where(
            Permission.user_id == user.id,
            Permission.role == UserRole.PLATFORM_ADMIN,
        )
    )
    assert perm_result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_bootstrap_skips_when_users_exist_without_matching_admin(
    test_db: AsyncSession,
) -> None:
    other_user = build_user(
        email="existing@example.com",
        username="existing",
        hashed_password=_hash("OtherPass123"),
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    test_db.add(other_user)
    await test_db.commit()

    config = AdminBootstrapConfig(
        email="bootstrap@example.com",
        password="SecurePass123",
        username="bootstrap_admin",
    )

    created = await bootstrap_platform_admin(
        config, require_empty_db=True, session=test_db
    )

    assert created is False
    result = await test_db.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].email == "existing@example.com"


@pytest.mark.asyncio
async def test_bootstrap_syncs_existing_admin_permissions(
    test_db: AsyncSession,
) -> None:
    admin_user = build_user(
        email="bootstrap@example.com",
        username="old_name",
        hashed_password=_hash("SecurePass123"),
        is_active=False,
        is_superuser=False,
        is_verified=False,
    )
    test_db.add(admin_user)
    await test_db.commit()

    config = AdminBootstrapConfig(
        email="bootstrap@example.com",
        password="NewSecurePass123",
        username="bootstrap_admin",
    )

    created = await bootstrap_platform_admin(
        config, require_empty_db=True, session=test_db
    )

    assert created is False
    refreshed = await test_db.execute(
        select(User).where(USER_EMAIL_COLUMN == "bootstrap@example.com")
    )
    user = refreshed.scalar_one()
    assert user.username == "bootstrap_admin"
    assert user.is_superuser is True
    assert user.is_verified is True
    assert user.is_active is True

    perm_result = await test_db.execute(
        select(Permission).where(
            Permission.user_id == user.id,
            Permission.role == UserRole.PLATFORM_ADMIN,
        )
    )
    assert perm_result.scalar_one_or_none() is not None
