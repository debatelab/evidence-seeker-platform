from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.evidence_seeker import FactCheckPublicationMode

from .evidence_seeker_settings import (
    ConfigurationStateLiteral,
    SetupModeLiteral,
)


class EvidenceSeekerBase(BaseModel):
    """Base schema for EvidenceSeeker"""

    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool = Field(default=False, alias="isPublic")
    fact_check_publication_mode: FactCheckPublicationMode = Field(
        default=FactCheckPublicationMode.AUTOPUBLISH,
        alias="factCheckPublicationMode",
    )
    language: str | None = Field(
        default=None,
        max_length=16,
        description="Language code used for preprocessing (e.g. EN, DE)",
    )

    class Config:
        populate_by_name = True


class InitialConfiguration(BaseModel):
    """Initial configuration payload for wizard onboarding."""

    api_key_name: str = Field(..., min_length=1, max_length=100, alias="apiKeyName")
    api_key_value: str = Field(..., min_length=10, alias="apiKeyValue")
    bill_to: str | None = Field(None, alias="billTo", max_length=100)
    setup_mode: SetupModeLiteral = Field(
        default="SIMPLE", alias="setupMode", description="Setup mode selection"
    )

    class Config:
        populate_by_name = True


class EvidenceSeekerCreate(EvidenceSeekerBase):
    """Schema for creating EvidenceSeeker"""

    initial_configuration: InitialConfiguration | None = Field(
        default=None, alias="initialConfiguration"
    )


class EvidenceSeekerUpdate(BaseModel):
    """Schema for updating EvidenceSeeker"""

    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_public: bool | None = Field(None, alias="isPublic")
    fact_check_publication_mode: FactCheckPublicationMode | None = Field(
        None, alias="factCheckPublicationMode"
    )
    language: str | None = Field(
        default=None,
        max_length=16,
        description="Language code used for preprocessing (e.g. EN, DE)",
    )

    class Config:
        populate_by_name = True


class EvidenceSeekerRead(EvidenceSeekerBase):
    """Schema for reading EvidenceSeeker"""

    id: int
    uuid: UUID  # External API identifier
    logo_url: str | None = Field(alias="logoUrl")
    created_by: int = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    published_at: datetime | None = Field(alias="publishedAt", default=None)
    is_public: bool = Field(alias="isPublic", default=False)
    fact_check_publication_mode: FactCheckPublicationMode = Field(
        alias="factCheckPublicationMode",
        default=FactCheckPublicationMode.AUTOPUBLISH,
    )
    configuration_state: ConfigurationStateLiteral | None = Field(
        alias="configurationState", default=None
    )
    missing_requirements: list[str] = Field(
        alias="missingRequirements", default_factory=list
    )
    language: str | None = Field(default=None)
    configured_at: datetime | None = Field(alias="configuredAt", default=None)
    setup_mode: SetupModeLiteral | None = Field(alias="setupMode", default=None)
    document_skip_acknowledged: bool = Field(
        alias="documentSkipAcknowledged", default=False
    )
    onboarding_token: str | None = Field(
        alias="onboardingToken", default=None, description="Short-lived wizard token"
    )

    class Config:
        populate_by_name = True
        from_attributes = True
        by_alias = True
