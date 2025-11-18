from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .document import to_camel


class IndexJobRead(BaseModel):
    uuid: UUID
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
    submitted_by: int = Field(alias="submittedBy")
    job_type: str = Field(alias="jobType")
    status: str
    operation_id: str | None = Field(alias="operationId", default=None)
    error_message: str | None = Field(alias="errorMessage", default=None)
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime | None = Field(alias="startedAt", default=None)
    completed_at: datetime | None = Field(alias="completedAt", default=None)

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True
