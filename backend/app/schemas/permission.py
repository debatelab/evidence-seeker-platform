from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PermissionRole(str, Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    EVSE_ADMIN = "EVSE_ADMIN"
    EVSE_READER = "EVSE_READER"


class PermissionBase(BaseModel):
    """Base schema for Permission"""

    user_id: int = Field(alias="userId")
    evidence_seeker_id: int | None = Field(alias="evidenceSeekerId", default=None)
    role: PermissionRole


class PermissionCreate(PermissionBase):
    """Schema for creating Permission"""

    pass


class PermissionRead(PermissionBase):
    """Schema for reading Permission"""

    id: int
    created_at: datetime = Field(alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True


class PermissionUpdate(BaseModel):
    """Schema for updating existing permissions"""

    role: PermissionRole | None = None


class UserPermissions(BaseModel):
    """Schema aggregating all permissions for a user across evidence seekers"""

    user_id: int = Field(alias="userId")
    permissions: list[PermissionRead] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True
