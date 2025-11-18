from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .document import to_camel


class EvidenceSearchRequest(BaseModel):
    query: str
    top_k: int | None = Field(default=5, alias="topK")
    metadata_filters: dict[str, Any] | None = Field(
        default=None, alias="metadataFilters"
    )
    document_uuids: list[UUID] | None = Field(
        default=None, alias="documentUuids"
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class EvidenceSearchHit(BaseModel):
    score: float
    text: str
    document_uuid: UUID | None = Field(alias="documentUuid", default=None)
    document_id: int | None = Field(alias="documentId", default=None)
    metadata: dict[str, Any] | None = None

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class EvidenceSearchResponse(BaseModel):
    query: str
    results: list[EvidenceSearchHit]

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class SystemStatistics(BaseModel):
    total_documents: int = Field(alias="totalDocuments")
    indexed_documents: int = Field(alias="indexedDocuments")
    evidence_seeker_settings: int = Field(alias="evidenceSeekerSettings")
    fact_check_runs: int = Field(alias="factCheckRuns")
    active_index_jobs: int = Field(alias="activeIndexJobs")
    total_api_keys: int = Field(alias="totalApiKeys")

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True
