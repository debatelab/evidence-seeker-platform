from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.permission import Permission


class User(SQLAlchemyBaseUserTable[int], Base):
    """User SQLAlchemy model extending fastapi-users base"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    permissions: Mapped[list[Permission]] = relationship(
        "Permission", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


if TYPE_CHECKING:
    from fastapi_users import models

    FastAPIUser = models.UserProtocol[int]
else:
    FastAPIUser = User


def ensure_user_id(user: User | FastAPIUser) -> int:
    """Return the concrete user ID or raise if it has not been persisted."""
    user_id = user.id
    if user_id is None:
        raise ValueError("User is missing an ID")
    return int(user_id)


def build_user(
    *,
    email: str,
    username: str,
    hashed_password: str,
    is_active: bool = True,
    is_superuser: bool = False,
    is_verified: bool = False,
) -> User:
    """Construct a User instance with explicit, type-checked parameters."""
    user = User()
    user.email = email
    user.username = username
    user.hashed_password = hashed_password
    user.is_active = is_active
    user.is_superuser = is_superuser
    user.is_verified = is_verified
    return user
