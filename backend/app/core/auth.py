from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.email_service import EmailService
from app.models.user import User


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Custom user manager for fastapi-users"""

    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    def __init__(
        self, user_db: SQLAlchemyUserDatabase, email_service: EmailService | None = None
    ) -> None:
        super().__init__(user_db)
        self.email_service = email_service

    async def validate_username(self, username: str) -> None:
        """Validate username uniqueness"""
        # Access session through the database adapter
        session = getattr(self.user_db, "session", None)
        if session is None:
            # Fallback for SQLAlchemy adapter
            session = getattr(self.user_db, "_session", None)

        if session is None:
            return  # Skip validation if session can't be accessed

        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        """Create a new user with username validation"""
        # Validate username uniqueness before creating user
        if hasattr(user_create, "username"):
            await self.validate_username(user_create.username)

        # Call parent create method
        return await super().create(user_create, safe, request)

    async def on_after_register(
        self, user: User, request: Request | None = None
    ) -> None:
        """Hook called after user registration"""
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        """Hook called after forgot password request - sends password reset email"""
        try:
            # Extract scalar value to satisfy MyPy
            user_email = str(user.email)
            if self.email_service is not None:
                await self.email_service.send_password_reset_email(user_email, token)
            print(f"Password reset email sent to {user.email}")
        except Exception as e:
            print(f"Failed to send password reset email to {user.email}: {e}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        """Hook called after verification request - sends verification email"""
        try:
            # Extract scalar value to satisfy MyPy
            user_email = str(user.email)
            if self.email_service is not None:
                await self.email_service.send_verification_email(user_email, token)
            print(f"Verification email sent to {user.email}")
        except Exception as e:
            print(f"Failed to send verification email to {user.email}: {e}")

    async def validate_password(
        self, password: str, user: schemas.UC | User | None = None
    ) -> None:
        """Enforce a minimal password policy for registrations and updates.

        Returns HTTP 400 for weak passwords to align with test expectations.
        """
        # Basic checks: length >= 8
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password too short. Must be at least 8 characters.",
            )
        # Require at least one letter and one number
        has_letter = any(ch.isalpha() for ch in password)
        has_digit = any(ch.isdigit() for ch in password)
        if not (has_letter and has_digit):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must include at least one letter and one number.",
            )
        # You could add more checks here (e.g., special characters) in the future
        # Call parent (currently no-op, but future-safe)
        if user is not None:
            await super().validate_password(password, user)


async def get_user_db(
    session: AsyncSession = Depends(get_async_db),
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    """Get user database instance"""
    yield SQLAlchemyUserDatabase(session, User)


def get_email_service() -> EmailService:
    """Get email service instance"""
    return EmailService()


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy for authentication"""
    return JWTStrategy(
        secret=settings.jwt_secret_key,
        lifetime_seconds=settings.jwt_expiration,
        algorithm=settings.jwt_algorithm,
    )


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    email_service: EmailService = Depends(get_email_service),
) -> AsyncGenerator[UserManager, None]:
    """Get user manager instance"""
    yield UserManager(user_db, email_service)


# Bearer token transport
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])


# Dependency to get current user
async def get_current_user(user: User = Depends(fastapi_users.current_user())) -> User:
    """Get the current authenticated user"""
    return user


# Dependency to get current verified user
async def get_current_verified_user(user: User = Depends(get_current_user)) -> User:
    """Get the current user and ensure they are verified"""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )
    return user
