from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.evidence_seeker import EvidenceSeeker
    from app.models.user import User


class UserRole(enum.Enum):
    """Enum for user roles in evidence seekers"""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    EVSE_ADMIN = "EVSE_ADMIN"
    EVSE_READER = "EVSE_READER"


class Permission(Base):
    """Permission SQLAlchemy model for managing user access to evidence seekers"""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    evidence_seeker_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=True
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.EVSE_READER
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="permissions")
    evidence_seeker: Mapped[EvidenceSeeker | None] = relationship(
        "EvidenceSeeker", back_populates="permissions", lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<Permission(user_id={self.user_id}, evidence_seeker_id={self.evidence_seeker_id}, role={self.role.value})>"

    @property
    def role_value(self) -> UserRole:
        """Return the role as a concrete UserRole enum for type checkers.

        SQLAlchemy's Column typing can confuse static analysis; this accessor normalizes
        the stored value into a UserRole enum for use in typed code and tests.
        """
        rv = self.role
        if isinstance(rv, UserRole):
            return rv
        # Attempt common shapes: a string value or enum-like with `.value`
        try:
            return UserRole(rv)
        except Exception:
            try:
                return UserRole(rv.value)
            except Exception:
                return cast(UserRole, rv)


def build_permission(
    *,
    user_id: int,
    role: UserRole,
    evidence_seeker_id: int | None = None,
) -> Permission:
    """Construct a Permission instance with type-checked arguments."""
    permission = Permission()
    permission.user_id = user_id
    permission.role = role
    permission.evidence_seeker_id = evidence_seeker_id
    return permission
