from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .document import to_camel
from .fact_check import FactCheckResultRead, FactCheckRunDetail


class PublicEvidenceSeekerSummary(BaseModel):
    uuid: UUID
    title: str
    description: str | None = None
    language: str | None = None
    logo_url: str | None = Field(alias="logoUrl", default=None)
    published_at: datetime | None = Field(alias="publishedAt", default=None)
    document_count: int = Field(alias="documentCount", default=0)
    latest_fact_check_at: datetime | None = Field(
        alias="latestFactCheckAt", default=None
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PublicEvidenceSeekerDetail(PublicEvidenceSeekerSummary):
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    is_public: bool = Field(alias="isPublic")


class PublicDocumentRead(BaseModel):
    uuid: UUID
    title: str
    description: str | None = None
    original_filename: str = Field(alias="originalFilename")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PaginatedPublicEvidenceSeekers(BaseModel):
    items: list[PublicEvidenceSeekerSummary]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PublicEvidenceSeekerDetailResponse(BaseModel):
    seeker: PublicEvidenceSeekerDetail
    documents: list[PublicDocumentRead]
    recent_fact_checks: list[PublicFactCheckRunSummary] = Field(
        alias="recentFactChecks", default_factory=list
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PublicFactCheckRunSummary(BaseModel):
    uuid: UUID
    statement: str
    status: str
    completed_at: datetime | None = Field(alias="completedAt", default=None)
    published_at: datetime | None = Field(alias="publishedAt", default=None)
    evidence_seeker_uuid: UUID = Field(alias="evidenceSeekerUuid")
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
    evidence_seeker_title: str = Field(alias="evidenceSeekerTitle")

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PublicFactCheckRunsResponse(BaseModel):
    items: list[PublicFactCheckRunSummary]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class PublicFactCheckRunDetailResponse(BaseModel):
    run: FactCheckRunDetail
    seeker: PublicEvidenceSeekerSummary
    results: list[FactCheckResultRead]

    class Config:
        alias_generator = to_camel
        populate_by_name = True
