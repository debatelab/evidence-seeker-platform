from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .document import to_camel

SetupModeLiteral = Literal["SIMPLE", "EXPERT"]
ConfigurationStateLiteral = Literal[
    "UNCONFIGURED",
    "MISSING_CREDENTIALS",
    "MISSING_DOCUMENTS",
    "READY",
    "ERROR",
]


class EvidenceSeekerSettingsBase(BaseModel):
    default_model: str | None = Field(default=None, alias="defaultModel")
    temperature: float | None = None
    top_k: int | None = Field(default=None, alias="topK")
    rerank_k: int | None = Field(default=None, alias="rerankK")
    max_tokens: int | None = Field(default=None, alias="maxTokens")
    language: str | None = None
    embed_backend_type: str = Field(default="huggingface", alias="embedBackendType")
    embed_base_url: str | None = Field(default=None, alias="embedBaseUrl")
    embed_bill_to: str | None = Field(default=None, alias="embedBillTo")
    trust_remote_code: bool | None = Field(default=None, alias="trustRemoteCode")
    metadata_filters: dict[str, Any] = Field(
        default_factory=dict, alias="metadataFilters"
    )
    pipeline_overrides: dict[str, Any] | None = Field(
        default=None, alias="pipelineOverrides"
    )
    huggingface_api_key_id: int | None = Field(
        default=None, alias="huggingfaceApiKeyId"
    )
    setup_mode: SetupModeLiteral = Field(default="SIMPLE", alias="setupMode")
    document_skip_acknowledged: bool = Field(
        default=False, alias="documentSkipAcknowledged"
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class EvidenceSeekerSettingsRead(EvidenceSeekerSettingsBase):
    evidence_seeker_id: int = Field(alias="evidenceSeekerId")
    last_validated_at: datetime | None = Field(alias="lastValidatedAt", default=None)
    updated_at: datetime | None = Field(alias="updatedAt", default=None)
    configuration_state: ConfigurationStateLiteral = Field(
        alias="configurationState", default="UNCONFIGURED"
    )
    configured_at: datetime | None = Field(alias="configuredAt", default=None)
    missing_requirements: list[str] = Field(
        alias="missingRequirements", default_factory=list
    )
    document_skip_acknowledged: bool = Field(
        alias="documentSkipAcknowledged", default=False
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        from_attributes = True


class EvidenceSeekerSettingsUpdate(EvidenceSeekerSettingsBase):
    pass


class TestSettingsRequest(BaseModel):
    metadata_filters: dict[str, Any] | None = Field(
        default=None, alias="metadataFilters"
    )
    statement: str | None = None

    class Config:
        alias_generator = to_camel
        populate_by_name = True


class ConfigurationStatusRead(BaseModel):
    state: ConfigurationStateLiteral = Field(alias="state")
    setup_mode: SetupModeLiteral = Field(alias="setupMode")
    configured_at: datetime | None = Field(alias="configuredAt", default=None)
    missing_requirements: list[str] = Field(
        alias="missingRequirements", default_factory=list
    )
    is_ready: bool = Field(alias="isReady", default=False)
    document_skip_acknowledged: bool = Field(
        alias="documentSkipAcknowledged", default=False
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True
