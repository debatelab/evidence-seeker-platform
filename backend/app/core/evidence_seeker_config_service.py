"""
Configuration service bridging platform settings with the EvidenceSeeker library.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TYPE_CHECKING, TypedDict

from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.config_service import config_service
from app.core.progress_tracker import progress_tracker
from app.models import (
    EvidenceSeeker,
    EvidenceSeekerSettings,
)
from app.models.document import Document
from app.models.evidence_seeker_settings import (
    ConfigurationState,
    SetupMode,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency during tests
    from evidence_seeker import RetrievalConfig as _RuntimeRetrievalConfig
except ImportError:  # pragma: no cover
    _RuntimeRetrievalConfig = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from evidence_seeker import RetrievalConfig as RetrievalConfigType
else:
    RetrievalConfigType = Any

try:  # pragma: no cover - optional dependency during tests
    from evidence_seeker.retrieval.config import (
        EmbedBackendType as _RuntimeEmbedBackendType,
    )
except ImportError:  # pragma: no cover
    _RuntimeEmbedBackendType = None  # type: ignore[assignment]

if _RuntimeEmbedBackendType is not None:
    _VALID_BACKEND_TYPES = {member.value for member in _RuntimeEmbedBackendType}
else:  # Fallback when evidence_seeker is unavailable at import time
    _VALID_BACKEND_TYPES = {
        "huggingface",
        "huggingface_inference_api",
        "tei",
        "ollama",
        "huggingface_instruct_prefix",
    }


class PipelineOverrides(TypedDict, total=False):
    """Runtime overrides forwarded to the EvidenceSeeker pipeline."""

    temperature: float
    top_k: int
    rerank_k: int
    max_tokens: int
    language: str
    metadata_filters: dict[str, Any]


@dataclass(slots=True)
class RetrievalConfigBundle:
    """Aggregated retrieval configuration plus metadata filters."""

    config: RetrievalConfigType
    metadata_filters: dict[str, Any]
    overrides: PipelineOverrides


@dataclass(slots=True)
class ConfigurationStatus:
    """Represents persisted configuration health."""

    state: ConfigurationState
    missing_requirements: list[str]
    setup_mode: SetupMode
    configured_at: datetime | None
    document_skip_acknowledged: bool

    @property
    def is_ready(self) -> bool:
        return self.state == ConfigurationState.READY


class ConfigurationNotReadyError(RuntimeError):
    """Raised when guarded operations encounter an unconfigured seeker."""

    def __init__(self, status: ConfigurationStatus) -> None:
        super().__init__("Evidence Seeker configuration incomplete")
        self.status = status


class EvidenceSeekerConfigService:
    """Builds EvidenceSeeker configs from database settings."""

    def _coerce_setup_mode(self, raw_value: object | None) -> SetupMode:
        """Normalize setup mode input to enum."""
        if not raw_value:
            return SetupMode.SIMPLE
        try:
            return SetupMode(str(raw_value).strip().upper())
        except ValueError:
            return SetupMode.SIMPLE

    def _evaluate_configuration_status(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        settings_row: EvidenceSeekerSettings,
    ) -> ConfigurationStatus:
        """Determine the current state and outstanding requirements."""
        setup_mode = self._coerce_setup_mode(getattr(settings_row, "setup_mode", None))
        backend_type_raw = getattr(settings_row, "embed_backend_type", None)
        backend_type = (
            (backend_type_raw or settings.evse_default_backend or "huggingface")
            .strip()
            .lower()
        )

        missing: list[str] = []
        require_hf_key = False
        if setup_mode == SetupMode.SIMPLE:
            require_hf_key = True
        elif backend_type in {"huggingface_inference_api", "huggingface_instruct_prefix"}:
            require_hf_key = True

        if require_hf_key and not settings_row.huggingface_api_key_id:
            missing.append("CREDENTIALS")

        if settings.evse_require_bill_to:
            bill_to = (settings_row.embed_bill_to or "").strip()
            if not bill_to:
                if "CREDENTIALS" not in missing:
                    missing.append("CREDENTIALS")

        document_count = (
            db.query(Document)
            .filter(Document.evidence_seeker_id == settings_row.evidence_seeker_id)
            .count()
        )
        documents_missing = document_count == 0
        if documents_missing:
            if "DOCUMENTS" not in missing:
                missing.append("DOCUMENTS")

        configured_at = getattr(settings_row, "configured_at", None)
        if "CREDENTIALS" in missing:
            state = (
                ConfigurationState.UNCONFIGURED
                if configured_at is None
                else ConfigurationState.MISSING_CREDENTIALS
            )
        elif "DOCUMENTS" in missing:
            state = ConfigurationState.MISSING_DOCUMENTS
        else:
            state = ConfigurationState.READY

        return ConfigurationStatus(
            state=state,
            missing_requirements=missing,
            setup_mode=setup_mode,
            configured_at=configured_at,
            document_skip_acknowledged=bool(settings_row.document_skip_acknowledged),
        )

    def _sync_configuration_status(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        settings_row: EvidenceSeekerSettings,
    ) -> ConfigurationStatus:
        """Persist evaluated status if fields changed."""
        previous_state = settings_row.configuration_state
        status = self._evaluate_configuration_status(db, seeker, settings_row)
        changed = False

        if settings_row.configuration_state != status.state.value:
            settings_row.configuration_state = status.state.value
            changed = True

        stored_missing = settings_row.missing_requirements or []
        if stored_missing != status.missing_requirements:
            settings_row.missing_requirements = status.missing_requirements
            changed = True

        if status.is_ready and settings_row.configured_at is None:
            settings_row.configured_at = datetime.utcnow()
            status.configured_at = settings_row.configured_at
            changed = True

        if changed:
            db.commit()
            db.refresh(settings_row)

        if (
            previous_state != ConfigurationState.READY.value
            and status.state == ConfigurationState.READY
        ):
            progress_tracker.record_event(
                "evse_onboarding_ready",
                user_id=settings_row.onboarding_token_owner_id,
                evidence_seeker_id=settings_row.evidence_seeker_id,
                metadata={"previous_state": previous_state},
            )

        return status

    def serialise_status(self, status: ConfigurationStatus) -> dict[str, object]:
        """Convert status to API payload."""
        return {
            "state": status.state.value,
            "missingRequirements": status.missing_requirements,
            "setupMode": status.setup_mode.value,
            "configuredAt": status.configured_at.isoformat()
            if status.configured_at
            else None,
            "isReady": status.is_ready,
            "documentSkipAcknowledged": status.document_skip_acknowledged,
        }

    def _ensure_metadata_filter_injection(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        settings_row: EvidenceSeekerSettings,
    ) -> None:
        """Persist mandatory metadata filter if missing."""
        metadata = settings_row.metadata_filters
        try:
            normalised = self._normalise_metadata_filters(
                seeker, metadata, strict=False
            )
        except ValueError:
            normalised = {"evidence_seeker_id": str(seeker.uuid)}

        if metadata != normalised:
            settings_row.metadata_filters = normalised
            db.commit()
            db.refresh(settings_row)

    def _ensure_embedding_defaults(
        self,
        db: Session,
        settings_row: EvidenceSeekerSettings,
    ) -> None:
        """Populate embedding defaults from application settings if unset."""
        changed = False
        if not getattr(settings_row, "embed_backend_type", None):
            settings_row.embed_backend_type = settings.evse_default_backend
            changed = True
        if (
            settings_row.embed_base_url is None
            and settings.evse_default_embed_base_url is not None
        ):
            settings_row.embed_base_url = settings.evse_default_embed_base_url
            changed = True
        if changed:
            db.commit()
            db.refresh(settings_row)

    def _normalise_metadata_filters(
        self,
        seeker: EvidenceSeeker,
        metadata: Any,
        *,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Coerce metadata filters to a dict and ensure seeker injection."""
        if metadata is None:
            metadata_dict: dict[str, Any] = {}
        elif isinstance(metadata, Mapping):
            metadata_dict = {
                str(key): value
                for key, value in metadata.items()
                if value is not None
            }
        else:
            if strict:
                raise ValueError("metadata_filters must be an object")
            metadata_dict = {}

        metadata_dict.setdefault("evidence_seeker_id", str(seeker.uuid))
        return metadata_dict

    def _coerce_pipeline_overrides(
        self,
        overrides: Any,
        *,
        strict: bool = True,
    ) -> dict[str, Any] | None:
        """Validate and coerce pipeline overrides."""
        if overrides is None:
            return None
        if isinstance(overrides, Mapping):
            return {str(key): value for key, value in overrides.items()}
        if strict:
            raise ValueError("pipeline_overrides must be an object")
        return None

    def _prepare_payload(
        self,
        seeker: EvidenceSeeker,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate incoming payload and return sanitized values."""
        clean: dict[str, Any] = {}

        if "embed_backend_type" in payload:
            value = payload.get("embed_backend_type")
            if value is None:
                clean["embed_backend_type"] = settings.evse_default_backend
            else:
                backend_value = str(value).strip().lower()
                if backend_value not in _VALID_BACKEND_TYPES:
                    raise ValueError(
                        "embed_backend_type must be one of: "
                        + ", ".join(sorted(_VALID_BACKEND_TYPES))
                    )
                clean["embed_backend_type"] = backend_value

        if "embed_base_url" in payload:
            value = payload.get("embed_base_url")
            if value is None:
                clean["embed_base_url"] = None
            else:
                if not isinstance(value, str):
                    raise ValueError("embed_base_url must be a string")
                clean["embed_base_url"] = value.strip() or None

        if "embed_bill_to" in payload:
            value = payload.get("embed_bill_to")
            if value is None:
                clean["embed_bill_to"] = None
            else:
                if not isinstance(value, str):
                    raise ValueError("embed_bill_to must be a string")
                clean["embed_bill_to"] = value.strip() or None

        if "trust_remote_code" in payload:
            value = payload.get("trust_remote_code")
            if value is None:
                clean["trust_remote_code"] = None
            elif isinstance(value, bool):
                clean["trust_remote_code"] = value
            else:
                raise ValueError("trust_remote_code must be a boolean")

        if "default_model" in payload:
            value = payload.get("default_model")
            clean["default_model"] = str(value) if value else None

        if "temperature" in payload:
            value = payload.get("temperature")
            if value is None:
                clean["temperature"] = None
            else:
                try:
                    temp = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("temperature must be a number") from exc
                if not 0 <= temp <= 2:
                    raise ValueError("temperature must be between 0 and 2")
                clean["temperature"] = temp

        def _positive_int(field: str) -> None:
            if field not in payload:
                return
            value = payload.get(field)
            if value is None:
                clean[field] = None
                return
            try:
                int_value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field} must be an integer") from exc
            if int_value <= 0:
                raise ValueError(f"{field} must be greater than 0")
            clean[field] = int_value

        for field in ("top_k", "rerank_k", "max_tokens"):
            _positive_int(field)

        if "language" in payload:
            value = payload.get("language")
            if value is None:
                clean["language"] = None
            else:
                if not isinstance(value, str):
                    raise ValueError("language must be a string")
                clean["language"] = value.strip() or None

        if "metadata_filters" in payload:
            clean["metadata_filters"] = self._normalise_metadata_filters(
                seeker,
                payload.get("metadata_filters"),
                strict=True,
            )

        if "pipeline_overrides" in payload:
            clean["pipeline_overrides"] = self._coerce_pipeline_overrides(
                payload.get("pipeline_overrides"), strict=True
            )

        if "huggingface_api_key_id" in payload:
            value = payload.get("huggingface_api_key_id")
            if value is None:
                clean["huggingface_api_key_id"] = None
            else:
                try:
                    clean["huggingface_api_key_id"] = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("huggingface_api_key_id must be an integer") from exc

        if "setup_mode" in payload:
            value = payload.get("setup_mode")
            mode = self._coerce_setup_mode(value)
            clean["setup_mode"] = mode.value

        return clean

    def ensure_settings(
        self,
        db: Session,
        seeker: EvidenceSeeker,
    ) -> EvidenceSeekerSettings:
        """Fetch or create default settings for the provided EvidenceSeeker."""
        settings_row = (
            db.query(EvidenceSeekerSettings)
            .filter(EvidenceSeekerSettings.evidence_seeker_id == seeker.id)
            .one_or_none()
        )

        if settings_row is not None:
            self._ensure_metadata_filter_injection(db, seeker, settings_row)
            self._ensure_embedding_defaults(db, settings_row)
            return settings_row

        default_metadata = self._normalise_metadata_filters(
            seeker, {"evidence_seeker_id": str(seeker.uuid)}, strict=False
        )

        settings_row = EvidenceSeekerSettings(
            evidence_seeker_id=seeker.id,
            default_model=settings.evse_default_model,
            embed_backend_type=settings.evse_default_backend,
            embed_base_url=settings.evse_default_embed_base_url,
            metadata_filters=default_metadata,
            setup_mode=SetupMode.SIMPLE.value,
            configuration_state=ConfigurationState.UNCONFIGURED.value,
            missing_requirements=["CREDENTIALS"],
        )
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
        logger.info(
            "Created default EvidenceSeeker settings for seeker_id=%s",
            seeker.id,
        )
        return settings_row

    def acknowledge_document_skip(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        *,
        acknowledged: bool,
    ) -> EvidenceSeekerSettings:
        """Persist the user's choice to temporarily skip document uploads."""
        settings_row = self.ensure_settings(db, seeker)
        settings_row.document_skip_acknowledged = acknowledged
        db.commit()
        db.refresh(settings_row)
        return settings_row

    def get_settings(
        self,
        db: Session,
        seeker_id: int,
    ) -> EvidenceSeekerSettings | None:
        """Return existing settings row."""
        return (
            db.query(EvidenceSeekerSettings)
            .filter(EvidenceSeekerSettings.evidence_seeker_id == seeker_id)
            .one_or_none()
        )

    def upsert_settings(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        payload: dict[str, Any],
        updated_by: int,
    ) -> EvidenceSeekerSettings:
        """Persist configuration changes coming from the API."""
        settings_row = self.ensure_settings(db, seeker)

        validated_payload = self._prepare_payload(seeker, payload)

        for key, value in validated_payload.items():
            setattr(settings_row, key, value)

        settings_row.updated_by = updated_by
        db.commit()
        db.refresh(settings_row)
        self._sync_configuration_status(db, seeker, settings_row)
        return settings_row

    def apply_initial_configuration(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        *,
        api_key_id: int,
        bill_to: str | None,
        setup_mode: SetupMode | None = None,
    ) -> EvidenceSeekerSettings:
        """Attach stored Hugging Face key and update status."""
        settings_row = self.ensure_settings(db, seeker)
        settings_row.huggingface_api_key_id = api_key_id
        settings_row.embed_bill_to = (bill_to or "").strip() or None
        settings_row.setup_mode = (setup_mode or SetupMode.SIMPLE).value
        db.commit()
        db.refresh(settings_row)
        self._sync_configuration_status(db, seeker, settings_row)
        return settings_row

    def get_configuration_status(
        self,
        db: Session,
        seeker: EvidenceSeeker,
    ) -> ConfigurationStatus:
        """Return configuration status for API consumers."""
        settings_row = self.ensure_settings(db, seeker)
        return self._sync_configuration_status(db, seeker, settings_row)

    def require_ready(
        self,
        db: Session,
        seeker: EvidenceSeeker,
    ) -> ConfigurationStatus:
        """Ensure seeker is ready before running heavy operations."""
        settings_row = self.ensure_settings(db, seeker)
        status = self._sync_configuration_status(db, seeker, settings_row)
        if not settings.enable_simple_config:
            return status
        if not status.is_ready:
            raise ConfigurationNotReadyError(status)
        return status

    def _build_postgres_kwargs(self) -> dict[str, Any]:
        """Translate platform database URL into EvidenceSeeker postgres kwargs."""
        url = make_url(settings.database_url)

        schema = settings.evse_postgres_schema or "public"
        table_prefix = settings.evse_postgres_table_prefix or "evse_"
        table_name = f"{table_prefix}documents"

        return {
            "use_postgres": True,
            "postgres_host": url.host or "localhost",
            "postgres_port": str(url.port or 5432),
            "postgres_database": url.database,
            "postgres_user": url.username,
            "postgres_password": url.password,
            "postgres_table_name": table_name,
            "postgres_schema_name": schema,
            # Allow EvidenceSeeker to discover the actual llama-index table name
            "postgres_llamaindex_table_name_prefix": None,
        }

    def _resolve_huggingface_key(
        self,
        db: Session,
        settings_row: EvidenceSeekerSettings,
    ) -> str | None:
        """Fetch and decrypt the stored Hugging Face key, if configured."""
        if settings_row.huggingface_api_key_id is None:
            return None
        return config_service.get_decrypted_api_key(
            api_key_id=settings_row.huggingface_api_key_id,
            evidence_seeker_id=settings_row.evidence_seeker_id,
            db=db,
        )

    def build_retrieval_bundle(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        overrides: dict[str, Any] | None = None,
    ) -> RetrievalConfigBundle:
        """Construct RetrievalConfig together with metadata filters and overrides."""
        overrides = overrides or {}
        settings_row = self.ensure_settings(db, seeker)
        hf_key = self._resolve_huggingface_key(db, settings_row)

        backend_type_raw = getattr(settings_row, "embed_backend_type", None)
        backend_type = (
            (backend_type_raw or settings.evse_default_backend or "huggingface")
            .strip()
            .lower()
        )
        if backend_type not in _VALID_BACKEND_TYPES:
            raise ValueError(
                f"Unsupported embed_backend_type '{backend_type}'. "
                f"Valid options: {', '.join(sorted(_VALID_BACKEND_TYPES))}"
            )

        base_kwargs: dict[str, Any] = {
            "embed_backend_type": backend_type,
            "embed_model_name": settings_row.default_model
            or settings.evse_default_model,
        }

        if settings_row.embed_base_url:
            base_kwargs["embed_base_url"] = settings_row.embed_base_url

        if settings_row.trust_remote_code is not None:
            base_kwargs["trust_remote_code"] = settings_row.trust_remote_code

        if settings_row.embed_bill_to:
            base_kwargs["bill_to"] = settings_row.embed_bill_to

        base_kwargs.update(self._build_postgres_kwargs())

        if backend_type in {"huggingface_inference_api", "tei"}:
            api_key_name = f"EVSE_HF_API_KEY_{settings_row.id}"
            if hf_key:
                os.environ[api_key_name] = hf_key
            base_kwargs["api_key_name"] = api_key_name
            if backend_type == "huggingface_inference_api" and not hf_key:
                raise ValueError(
                    "A Hugging Face API key is required when using the "
                    "huggingface_inference_api backend."
                )
        elif hf_key:
            # Ensure Hugging Face Hub aware clients can access private models.
            os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", hf_key)

        top_k_value = overrides.get("top_k", settings_row.top_k)
        if top_k_value is not None:
            base_kwargs["top_k"] = int(top_k_value)

        bundle_overrides: PipelineOverrides = PipelineOverrides()
        if isinstance(settings_row.pipeline_overrides, dict):
            for key, value in settings_row.pipeline_overrides.items():
                if value is not None:
                    bundle_overrides[key] = value  # type: ignore[index]

        for key in ("temperature", "rerank_k", "max_tokens", "language"):
            value = overrides.get(key, getattr(settings_row, key))
            if value is not None:
                bundle_overrides[key] = value  # type: ignore[index]

        metadata_filters = self._normalise_metadata_filters(
            seeker, settings_row.metadata_filters, strict=False
        )

        # Allow caller overrides to extend metadata filters
        override_filters = overrides.get("metadata_filters")
        if isinstance(override_filters, dict):
            metadata_filters.update(
                {str(k): v for k, v in override_filters.items() if v is not None}
            )

        bundle_overrides["metadata_filters"] = metadata_filters

        if _RuntimeRetrievalConfig is None:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "EvidenceSeeker package is not installed; install `evidence-seeker` to run index operations."
            )

        retrieval_config = _RuntimeRetrievalConfig(**base_kwargs)

        return RetrievalConfigBundle(
            config=retrieval_config,
            metadata_filters=metadata_filters,
            overrides=bundle_overrides,
        )


# Global singleton
evidence_seeker_config_service = EvidenceSeekerConfigService()
