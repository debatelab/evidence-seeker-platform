import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.evidence_seeker_config_service import evidence_seeker_config_service
from app.core.evidence_seeker_pipeline import EvidenceSeekerPipelineManager
from app.core.rate_limiter import reset_public_run_rate_limiter
from app.models.evidence_seeker import EvidenceSeeker, build_evidence_seeker
from app.models.fact_check import (
    FactCheckRun,
    FactCheckRunStatus,
    FactCheckRunVisibility,
    build_fact_check_run,
)
from app.models.user import User


def _make_public_seeker(db: Session, owner: User) -> EvidenceSeeker:
    seeker = build_evidence_seeker(
        title="Public Seeker", created_by=owner.id, is_public=True
    )
    db.add(seeker)
    db.commit()
    db.refresh(seeker)
    return seeker


def _stub_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_create_run(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        statement: str,
        user_id: int | None,
        overrides=None,
        *,
        public_run: bool = False,
    ) -> FactCheckRun:
        run = build_fact_check_run(
            evidence_seeker_id=seeker.id,
            statement=statement,
            status=FactCheckRunStatus.PENDING,
            is_public=public_run,
            visibility=(
                FactCheckRunVisibility.PUBLIC
                if public_run
                else FactCheckRunVisibility.PRIVATE
            ),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    async def fake_execute_run(
        self, run_id: int, seeker_id: int
    ) -> None:  # pragma: no cover - minimal stub
        return None

    monkeypatch.setattr(
        EvidenceSeekerPipelineManager,
        "create_fact_check_run",
        fake_create_run,
        raising=False,
    )
    monkeypatch.setattr(
        EvidenceSeekerPipelineManager,
        "execute_fact_check_run",
        fake_execute_run,
        raising=False,
    )


def _disable_config_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        evidence_seeker_config_service,
        "require_ready",
        lambda db, seeker: None,
        raising=False,
    )


def test_public_fact_check_rate_limit_returns_429(
    db: Session,
    test_user: User,
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_pipeline(monkeypatch)
    _disable_config_guard(monkeypatch)
    monkeypatch.setattr(settings, "public_run_rate_limit_requests", 2, raising=False)
    reset_public_run_rate_limiter()

    seeker = _make_public_seeker(db, test_user)
    url = f"/api/v1/public/evidence-seekers/{seeker.uuid}/fact-checks"

    headers = {"X-Forwarded-For": "203.0.113.42"}
    payload = {"statement": "Test rate limit"}

    first = test_client.post(url, json=payload, headers=headers)
    second = test_client.post(url, json=payload, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 202

    third = test_client.post(url, json=payload, headers=headers)
    assert third.status_code == 429
    assert "Please wait" in third.json()["detail"]
    assert third.headers.get("Retry-After") is not None


def test_public_fact_check_queue_limit_blocks_when_pending_runs_exist(
    db: Session,
    test_user: User,
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_pipeline(monkeypatch)
    _disable_config_guard(monkeypatch)
    monkeypatch.setattr(settings, "public_run_queue_limit_per_seeker", 1, raising=False)
    reset_public_run_rate_limiter()

    seeker = _make_public_seeker(db, test_user)

    existing_run = build_fact_check_run(
        evidence_seeker_id=seeker.id,
        statement="Already running",
        status=FactCheckRunStatus.PENDING,
        is_public=True,
    )
    db.add(existing_run)
    db.commit()

    url = f"/api/v1/public/evidence-seekers/{seeker.uuid}/fact-checks"
    response = test_client.post(url, json={"statement": "Queue test"})

    assert response.status_code == 409
    assert "public runs in progress" in response.json()["detail"]
