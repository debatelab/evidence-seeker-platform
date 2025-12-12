from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class DocumentBase(BaseModel):
    """Base schema for Document"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    evidence_seeker_uuid: UUID  # External API uses UUID
    evidence_seeker_id: int | None = None  # Keep for internal use
    source_url: AnyHttpUrl | None = Field(
        None,
        alias="sourceUrl",
        description="Publicly accessible document URL",
        max_length=500,
    )

    class Config:
        from_attributes = True
        populate_by_name = True
        alias_generator = to_camel


class DocumentCreate(DocumentBase):
    """Schema for creating Document (without file_path, file_size, mime_type)"""

    pass


class DocumentUpdate(BaseModel):
    """Schema for updating Document"""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=500)
    source_url: AnyHttpUrl | None = Field(
        None,
        alias="sourceUrl",
        description="Publicly accessible document URL",
        max_length=500,
    )

    class Config:
        populate_by_name = True
        alias_generator = to_camel


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
        alias_generator = to_camel


class DocumentIngestionResponse(BaseModel):
    """Response schema returning document plus indexing job context."""

    document: DocumentRead
    job_uuid: UUID = Field(alias="jobUuid")
    operation_id: str | None = Field(alias="operationId")

    class Config:
        populate_by_name = True
        from_attributes = True
