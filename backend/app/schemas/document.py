from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base schema for Document"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    evidence_seeker_uuid: UUID  # External API uses UUID
    evidence_seeker_id: int | None = None  # Keep for internal use


class DocumentCreate(DocumentBase):
    """Schema for creating Document (without file_path, file_size, mime_type)"""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating Document"""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)


class DocumentRead(DocumentBase):
    """Schema for reading Document"""

    id: int
    uuid: UUID  # External API identifier
    file_path: str
    original_filename: str = Field(alias="originalFilename")
    file_size: int = Field(alias="fileSize")
    mime_type: str = Field(alias="mimeType")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True
