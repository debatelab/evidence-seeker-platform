import enum
from typing import cast

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(enum.Enum):
    """Enum for user roles in evidence seekers"""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    EVSE_ADMIN = "EVSE_ADMIN"
    EVSE_READER = "EVSE_READER"


class Permission(Base):
    """Permission SQLAlchemy model for managing user access to evidence seekers"""

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evidence_seeker_id = Column(
        Integer, ForeignKey("evidence_seekers.id"), nullable=True
    )
    # Note: SQLAlchemy Column typing doesn't align with var annotations; define Column and add a typed property for mypy.
    role = Column(  # type: ignore[var-annotated]
        Enum(UserRole), nullable=False, default=UserRole.EVSE_READER
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="permissions")
    evidence_seeker = relationship(
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
