from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .document import to_camel


class IndexJobRead(BaseModel):
    uuid: UUID
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
    submitted_by: int = Field(alias="submittedBy")
    job_type: str = Field(alias="jobType")
    status: str
    document_uuid: UUID | None = Field(alias="documentUuid", default=None)
    document_uuids: list[UUID] | None = Field(alias="documentUuids", default=None)
    payload: dict[str, Any] | None = None
    operation_id: str | None = Field(alias="operationId", default=None)
    error_message: str | None = Field(alias="errorMessage", default=None)
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime | None = Field(alias="startedAt", default=None)
    completed_at: datetime | None = Field(alias="completedAt", default=None)

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def _fill_document_uuids(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("document_uuids") is not None:
            return values
        payload = values.get("payload")
        if isinstance(payload, dict) and "document_uuids" in payload:
            values["document_uuids"] = payload.get("document_uuids")
        return values
