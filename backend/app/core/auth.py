from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, IntegerIDMixin, schemas, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
import secrets

from app.core.database import get_async_db, get_db
from app.models.user import User
from app.core.config import settings


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Custom user manager for fastapi-users"""

    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    async def validate_username(self, username: str) -> None:
        """Validate username uniqueness"""
        result = await self.user_db.session.execute(
            select(User).where(User.username == username)
        )
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
        request: Optional[Request] = None,
    ) -> User:
        """Create a new user with username validation"""
        # Validate username uniqueness before creating user
        if hasattr(user_create, "username"):
            await self.validate_username(user_create.username)

        # Call parent create method
        return await super().create(user_create, safe, request)

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Hook called after user registration"""
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Hook called after forgot password request"""
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Hook called after verification request"""
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_db(session: AsyncSession = Depends(get_async_db)):
    """Get user database instance"""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Get user manager instance"""
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy for authentication"""
    return JWTStrategy(
        secret=settings.jwt_secret_key,
        lifetime_seconds=settings.jwt_expiration,
        algorithm=settings.jwt_algorithm,
    )


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
