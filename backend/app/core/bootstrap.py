from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi_users.password import PasswordHelper
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.permission import Permission, UserRole, build_permission
from app.models.user import User, build_user, ensure_user_id

logger = logging.getLogger(__name__)

USER_EMAIL_COLUMN = User.__table__.c.email


@dataclass(slots=True)
class AdminBootstrapConfig:
    """Configuration describing the bootstrap admin account."""

    email: str
    password: str
    username: str
    is_active: bool = True
    is_superuser: bool = True
    is_verified: bool = True


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(USER_EMAIL_COLUMN == email))
    return result.scalar_one_or_none()


async def _ensure_platform_admin_permission(
    session: AsyncSession,
    user_id: int,
) -> bool:
    result = await session.execute(
        select(Permission).where(
            Permission.user_id == user_id,
            Permission.role == UserRole.PLATFORM_ADMIN,
        )
    )
    if result.scalar_one_or_none():
        return False

    session.add(
        build_permission(
            user_id=user_id,
            role=UserRole.PLATFORM_ADMIN,
            evidence_seeker_id=None,
        )
    )
    return True


def _derive_username(email: str) -> str:
    local_part = email.split("@", 1)[0]
    return local_part or "admin"


async def _sync_admin_flags(user: User, config: AdminBootstrapConfig) -> bool:
    updated = False

    if getattr(user, "is_superuser", False) is not True and config.is_superuser:
        user.is_superuser = True
        updated = True

    if getattr(user, "is_verified", False) is not True and config.is_verified:
        user.is_verified = True
        updated = True

    if getattr(user, "is_active", True) is not True and config.is_active:
        user.is_active = True
        updated = True

    # Align username if a different one was provided
    if getattr(user, "username", None) != config.username:
        user.username = config.username
        updated = True

    return updated


async def bootstrap_platform_admin(
    config: AdminBootstrapConfig,
    *,
    require_empty_db: bool = True,
) -> bool:
    """Ensure a platform admin user matching config exists.

    Returns True when a new user was created, False otherwise.
    """
    async with AsyncSessionLocal() as session:
        existing_admin = await _get_user_by_email(session, config.email)
        if existing_admin is not None:
            updated = await _sync_admin_flags(existing_admin, config)
            permission_added = await _ensure_platform_admin_permission(
                session, ensure_user_id(existing_admin)
            )
            if updated or permission_added:
                await session.commit()
                logger.info("Synchronized existing admin user '%s'", config.email)
            else:
                logger.info("Admin user '%s' already configured", config.email)
            return False

        if require_empty_db:
            user_count = await session.scalar(select(func.count()).select_from(User))
            if user_count and user_count > 0:
                logger.info(
                    "Skipping initial admin bootstrap because %s user(s) already exist",
                    user_count,
                )
                return False

        password_helper = PasswordHelper()
        hashed_password = password_helper.hash(config.password)
        admin_user = build_user(
            email=config.email,
            username=config.username,
            hashed_password=hashed_password,
            is_active=config.is_active,
            is_superuser=config.is_superuser,
            is_verified=config.is_verified,
        )
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)

        await _ensure_platform_admin_permission(session, ensure_user_id(admin_user))
        await session.commit()
        logger.info("Created initial admin user '%s'", config.email)
        return True


async def ensure_initial_admin_from_settings() -> None:
    """Bootstrap the admin user using environment driven settings."""
    if not settings.auto_bootstrap_initial_admin:
        logger.info("Initial admin bootstrap disabled via settings.")
        return

    email = settings.initial_admin_email
    password = settings.initial_admin_password
    username = settings.initial_admin_username or (
        _derive_username(email) if email else None
    )

    if not email or not password or not username:
        logger.warning(
            "Initial admin bootstrap skipped due to missing credentials. "
            "Set INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD (and optionally "
            "INITIAL_ADMIN_USERNAME) in the environment."
        )
        return

    config = AdminBootstrapConfig(
        email=email,
        password=password,
        username=username,
    )
    await bootstrap_platform_admin(config, require_empty_db=True)
