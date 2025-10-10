from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from fastapi_users.db import SQLAlchemyBaseUserTable
from app.core.database import Base


class User(SQLAlchemyBaseUserTable[int], Base):
    """User SQLAlchemy model extending fastapi-users base"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # type: ignore[assignment]
    email = Column(String, unique=True, index=True, nullable=False)  # type: ignore[assignment]
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # type: ignore[assignment]
    is_active = Column(Boolean, default=True)  # type: ignore[assignment]
    is_superuser = Column(Boolean, default=False)  # type: ignore[assignment]
    is_verified = Column(Boolean, default=False)  # type: ignore[assignment]

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    permissions = relationship(
        "Permission", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
