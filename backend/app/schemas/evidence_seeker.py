from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class EvidenceSeekerBase(BaseModel):
    """Base schema for EvidenceSeeker"""

    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: bool = Field(default=False)


class EvidenceSeekerCreate(EvidenceSeekerBase):
    """Schema for creating EvidenceSeeker"""

    pass


class EvidenceSeekerUpdate(BaseModel):
    """Schema for updating EvidenceSeeker"""

    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None


class EvidenceSeekerRead(EvidenceSeekerBase):
    """Schema for reading EvidenceSeeker"""

    id: int
    uuid: UUID  # External API identifier
    logo_url: Optional[str] = Field(alias="logoUrl")
    created_by: int = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    is_public: bool = Field(alias="isPublic", default=False)

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True
