import time

from loguru import logger

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.evidence_seeker_config_service import evidence_seeker_config_service
from app.core.evidence_seeker_pipeline import evidence_seeker_pipeline_manager
from app.models.evidence_seeker import EvidenceSeeker


async def warmup_pipelines(limit: int | None = None) -> None:
    """
    Preload EvidenceSeeker pipelines to avoid first-request cold starts.

    - Skips if disabled via EVSE_ENABLE_WARMUP.
    - Limits seekers warmed via EVSE_WARMUP_MAX or the passed limit.
    - Only warms seekers whose configuration status is ready.
    """
    if not settings.evse_enable_warmup:
        logger.info("Warmup skipped: EVSE_ENABLE_WARMUP is false")
        return

    if settings.disable_embeddings:
        logger.info("Warmup skipped: DISABLE_EMBEDDINGS is true")
        return

    started = time.perf_counter()
    db = SessionLocal()
    target_limit = limit if limit is not None else settings.evse_warmup_max

    try:
        query = db.query(EvidenceSeeker).order_by(
            EvidenceSeeker.updated_at.desc()
        )  # most recent first
        if target_limit:
            query = query.limit(int(target_limit))

        seekers: list[EvidenceSeeker] = query.all()

        ready_seekers: list[EvidenceSeeker] = []
        for seeker in seekers:
            try:
                status = evidence_seeker_config_service.get_configuration_status(
                    db, seeker
                )
            except Exception as exc:
                logger.warning(
                    "Warmup skipping seeker_id={seeker_id}: status check failed: {error}",
                    seeker_id=seeker.id,
                    error=str(exc),
                )
                continue

            if getattr(status, "is_ready", False):
                ready_seekers.append(seeker)

        if not ready_seekers:
            logger.info(
                "Warmup: no ready Evidence Seekers found (checked={count})",
                count=len(seekers),
            )
            return

        logger.info(
            "Warmup: warming {ready_count} ready seekers (limit={limit})",
            ready_count=len(ready_seekers),
            limit=target_limit or "none",
        )

        for seeker in ready_seekers:
            seeker_started = time.perf_counter()
            try:
                bundle = evidence_seeker_config_service.build_retrieval_bundle(
                    db, seeker
                )
                await evidence_seeker_pipeline_manager.warmup_pipeline(
                    db=db, seeker=seeker, bundle=bundle
                )
                elapsed = time.perf_counter() - seeker_started
                logger.info(
                    "Warmup: seeker_id={seeker_id} ready in {elapsed:.2f}s",
                    seeker_id=seeker.id,
                    elapsed=elapsed,
                )
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.warning(
                    "Warmup failed for seeker_id={seeker_id}: {error}",
                    seeker_id=seeker.id,
                    error=str(exc),
                )

        logger.info(
            "Warmup complete: warmed={count} in {elapsed:.2f}s",
            count=len(ready_seekers),
            elapsed=time.perf_counter() - started,
        )
    finally:
        db.close()


async def warmup_pipelines_async(limit: int | None = None) -> None:
    """Helper to schedule warmup from synchronous contexts via asyncio.run."""
    await warmup_pipelines(limit=limit)
