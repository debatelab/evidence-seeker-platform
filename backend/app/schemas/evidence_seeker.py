from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceSeekerBase(BaseModel):
    """Base schema for EvidenceSeeker"""

    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool = Field(default=False)


class EvidenceSeekerCreate(EvidenceSeekerBase):
    """Schema for creating EvidenceSeeker"""

    pass


class EvidenceSeekerUpdate(BaseModel):
    """Schema for updating EvidenceSeeker"""

    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = None


class EvidenceSeekerRead(EvidenceSeekerBase):
    """Schema for reading EvidenceSeeker"""

    id: int
    uuid: UUID  # External API identifier
    logo_url: str | None = Field(alias="logoUrl")
    created_by: int = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    is_public: bool = Field(alias="isPublic", default=False)

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True
