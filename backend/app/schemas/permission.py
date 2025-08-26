from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class PermissionRole(str, Enum):
    evse_admin = "evse_admin"
    evse_reader = "evse_reader"


class PermissionBase(BaseModel):
    """Base schema for Permission"""

    user_id: int = Field(alias="userId")
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
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
