from __future__ import annotations

import os
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.evidence_seeker_config_service import (
    ConfigurationNotReadyError,
    EvidenceSeekerConfigService,
)
from app.models import EvidenceSeekerSettings


@pytest.fixture(autouse=True)
def _auto_clean_db() -> None:  # type: ignore[override]
    """Disable integration DB cleanup for fast unit tests."""
    yield


@pytest.fixture()
def service() -> EvidenceSeekerConfigService:
    return EvidenceSeekerConfigService()


@pytest.fixture()
def seeker() -> SimpleNamespace:
    return SimpleNamespace(id=1, uuid=uuid.uuid4())


def _build_settings(seeker: SimpleNamespace) -> EvidenceSeekerSettings:
    return EvidenceSeekerSettings(
        evidence_seeker_id=seeker.id,
        default_model="test-model",
        metadata_filters={},
        embed_backend_type="huggingface",
        setup_mode="SIMPLE",
        configuration_state="UNCONFIGURED",
        missing_requirements=["CREDENTIALS"],
    )


def test_upsert_settings_normalises_payload(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)

    service.upsert_settings(
        db=db,
        seeker=seeker,
        payload={
            "metadata_filters": {"custom": "value"},
            "top_k": 5,
            "temperature": 0.5,
        },
        updated_by=42,
    )

    assert settings_row.metadata_filters["evidence_seeker_id"] == str(seeker.uuid)
    assert settings_row.metadata_filters["custom"] == "value"
    assert settings_row.top_k == 5
    assert settings_row.temperature == pytest.approx(0.5, rel=1e-6)
    assert settings_row.updated_by == 42
    db.commit.assert_called()
    db.refresh.assert_called_with(settings_row)


def test_upsert_settings_rejects_invalid_values(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)

    with pytest.raises(ValueError):
        service.upsert_settings(
            db=db,
            seeker=seeker,
            payload={"temperature": -0.1},
            updated_by=1,
        )


def test_build_retrieval_bundle_injects_metadata(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    settings_row.top_k = 7
    settings_row.id = 12
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)

    class DummyRetrievalConfig:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.core.evidence_seeker_config_service._RuntimeRetrievalConfig",
        DummyRetrievalConfig,
    )

    bundle = service.build_retrieval_bundle(db=db, seeker=seeker)

    assert bundle.metadata_filters["evidence_seeker_id"] == str(seeker.uuid)
    assert bundle.config.kwargs["top_k"] == 7
    assert bundle.overrides["metadata_filters"]["evidence_seeker_id"] == str(
        seeker.uuid
    )
    assert bundle.config.kwargs["embed_backend_type"] == "huggingface"


def test_build_retrieval_bundle_hf_inference_sets_env_var(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    settings_row.id = 77
    settings_row.embed_backend_type = "huggingface_inference_api"
    settings_row.embed_base_url = (
        "https://api-inference.huggingface.co/models/test-model"
    )
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)
    monkeypatch.setattr(
        service,
        "_resolve_huggingface_key",
        lambda *_: "hf-secret-token",
    )

    class DummyRetrievalConfig:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.core.evidence_seeker_config_service._RuntimeRetrievalConfig",
        DummyRetrievalConfig,
    )

    env_name = f"EVSE_HF_API_KEY_{settings_row.id}"
    os.environ.pop(env_name, None)

    bundle = service.build_retrieval_bundle(db=db, seeker=seeker)

    assert os.environ[env_name] == "hf-secret-token"
    assert bundle.config.kwargs["api_key_name"] == env_name
    assert bundle.config.kwargs["embed_backend_type"] == "huggingface_inference_api"
    assert bundle.config.kwargs["embed_base_url"] == settings_row.embed_base_url
    os.environ.pop(env_name, None)


def test_build_retrieval_bundle_sets_env_var_for_preprocessing_models(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preprocessing/confirmation configs expect the key env var regardless of backend."""
    settings_row = _build_settings(seeker)
    settings_row.id = 5
    settings_row.embed_backend_type = "huggingface"  # uses default embedding backend
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)
    monkeypatch.setattr(
        service,
        "_resolve_huggingface_key",
        lambda *_: "hf-internal-" + str(settings_row.id),
    )

    class DummyRetrievalConfig:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.core.evidence_seeker_config_service._RuntimeRetrievalConfig",
        DummyRetrievalConfig,
    )

    env_name = f"EVSE_HF_API_KEY_{settings_row.id}"
    os.environ.pop(env_name, None)

    service.build_retrieval_bundle(db=db, seeker=seeker)

    assert os.environ[env_name] == f"hf-internal-{settings_row.id}"
    os.environ.pop(env_name, None)


def test_build_retrieval_bundle_hf_inference_requires_key(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    settings_row.id = 23
    settings_row.embed_backend_type = "huggingface_inference_api"
    settings_row.embed_base_url = (
        "https://api-inference.huggingface.co/models/test-model"
    )
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)
    monkeypatch.setattr(
        service,
        "_resolve_huggingface_key",
        lambda *_: None,
    )

    monkeypatch.setattr(
        "app.core.evidence_seeker_config_service._RuntimeRetrievalConfig",
        lambda **_: None,
    )

    with pytest.raises(ValueError):
        service.build_retrieval_bundle(db=db, seeker=seeker)


def test_require_ready_detects_missing_key(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)

    with pytest.raises(ConfigurationNotReadyError):
        service.require_ready(db, seeker)


def test_require_ready_passes_when_key_attached(
    service: EvidenceSeekerConfigService,
    seeker: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_row = _build_settings(seeker)
    settings_row.huggingface_api_key_id = 99
    settings_row.configuration_state = "READY"
    settings_row.missing_requirements = []
    db = MagicMock()
    monkeypatch.setattr(service, "ensure_settings", lambda *_: settings_row)

    status = service.require_ready(db, seeker)

    assert status.is_ready
