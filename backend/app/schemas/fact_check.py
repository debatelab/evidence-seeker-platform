from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .document import to_camel


class FactCheckRunCreate(BaseModel):
    statement: str
    overrides: dict[str, Any] | None = None


class FactCheckRerunRequest(BaseModel):
    overrides: dict[str, Any] | None = None


class FactCheckRunRead(BaseModel):
    uuid: UUID
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
    statement: str
    status: str
    is_public: bool = Field(alias="isPublic", default=False)
    created_at: datetime = Field(alias="createdAt")
    began_at: datetime | None = Field(alias="beganAt", default=None)
    completed_at: datetime | None = Field(alias="completedAt", default=None)
    published_at: datetime | None = Field(alias="publishedAt", default=None)
    error_message: str | None = Field(alias="errorMessage", default=None)
    operation_id: str | None = Field(alias="operationId", default=None)

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class FactCheckEvidenceRead(BaseModel):
    id: int
    library_node_id: str | None = Field(alias="libraryNodeId", default=None)
    document_uuid: UUID | None = Field(alias="documentUuid", default=None)
    document_id: int | None = Field(alias="documentId", default=None)
    chunk_label: str | None = Field(alias="chunkLabel", default=None)
    evidence_text: str = Field(alias="evidenceText")
    stance: str
    score: float | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        serialization_alias="metadata",
        validation_alias="metadata_payload",
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class FactCheckResultRead(BaseModel):
    id: int
    interpretation_index: int = Field(alias="interpretationIndex")
    interpretation_text: str = Field(alias="interpretationText")
    interpretation_type: str = Field(alias="interpretationType")
    confirmation_level: str | None = Field(alias="confirmationLevel", default=None)
    confidence_score: float | None = Field(alias="confidenceScore", default=None)
    summary: str | None = None
    evidence: list[FactCheckEvidenceRead]

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class FactCheckRunDetail(FactCheckRunRead):
    metrics: dict[str, Any] | None = None
    config_snapshot: dict[str, Any] | None = Field(alias="configSnapshot", default=None)
