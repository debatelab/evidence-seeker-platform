from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, IntegerIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.core.database import get_async_db, get_db
from app.models.user import User
from app.core.config import settings


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """Custom user manager for fastapi-users"""

    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

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


# Dependency to get current user
def get_current_user(
    db: Session = Depends(get_db),
    user_manager=Depends(get_user_manager),
) -> User:
    """Get the current authenticated user"""
    # This is a simplified version - in production you'd want to get the user from the JWT token
    # For now, we'll return the first user (test user)
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user
