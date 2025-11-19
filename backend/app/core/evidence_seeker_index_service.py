"""
Index management utilities wrapping the EvidenceSeeker IndexBuilder.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.evidence_seeker_config_service import (
    RetrievalConfigBundle,
    evidence_seeker_config_service,
)
from app.core.progress_tracker import progress_tracker
from app.models import Document, EvidenceSeeker, IndexJob, IndexJobStatus

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency during tests
    from evidence_seeker.retrieval.index_builder import IndexBuilder as _IndexBuilder
except ImportError:  # pragma: no cover
    IndexBuilder = None
else:
    IndexBuilder = cast(type[Any], _IndexBuilder)


class EvidenceSeekerIndexService:
    """Synchronises platform documents with the EvidenceSeeker vector store."""

    def __init__(self) -> None:
        if IndexBuilder is None:  # pragma: no cover
            logger.warning(
                "EvidenceSeeker library not available; index operations will fail at runtime."
            )

    def _create_job(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        user_id: int,
        job_type: str,
        payload: dict[str, Any] | None = None,
    ) -> IndexJob:
        job = IndexJob()
        job.evidence_seeker_id = int(seeker.id)
        job.submitted_by = user_id
        job.job_type = job_type
        job.payload = payload or {}
        job.status = IndexJobStatus.QUEUED
        db.add(job)
        db.commit()
        db.refresh(job)

        operation_id = progress_tracker.start_operation(
            operation_type=f"index_{job_type}",
            user_id=user_id,
            evidence_seeker_id=seeker.id,
            metadata={"job_uuid": str(job.uuid)},
        )
        job.operation_id = operation_id
        db.commit()
        db.refresh(job)

        logger.info(
            "Created index job %s (type=%s) for seeker_id=%s",
            job.uuid,
            job_type,
            seeker.id,
        )
        return job

    def _update_job_status(
        self,
        db: Session,
        job: IndexJob,
        status: IndexJobStatus,
        message: str,
        *,
        error: str | None = None,
    ) -> None:
        job.status = status
        job.updated_at = datetime.utcnow()
        if status == IndexJobStatus.RUNNING:
            job.started_at = datetime.utcnow()
        if status in (IndexJobStatus.SUCCEEDED, IndexJobStatus.FAILED):
            job.completed_at = datetime.utcnow()
        if error:
            job.error_message = error
        db.commit()
        db.refresh(job)

        if not job.operation_id:
            return

        operation_id = job.operation_id

        if status == IndexJobStatus.SUCCEEDED:
            progress_tracker.complete_operation(
                operation_id,
                message=message,
                metadata={"job_uuid": str(job.uuid)},
            )
        elif status == IndexJobStatus.FAILED:
            progress_tracker.fail_operation(
                operation_id,
                error_message=error or message,
                metadata={"job_uuid": str(job.uuid)},
            )
        elif status == IndexJobStatus.RUNNING:
            progress_tracker.update_progress(
                operation_id,
                progress=5.0,
                message=message,
                metadata={"job_uuid": str(job.uuid)},
            )

    def _progress_callback(
        self,
        job: IndexJob,
    ) -> Callable[..., None]:
        def callback(
            progress: float | None = None,
            message: str | None = None,
            stage: str | None = None,
            **kwargs: Any,
        ) -> None:
            operation_id = job.operation_id
            if not operation_id:
                return

            extra_metadata: dict[str, Any] = {}

            if isinstance(progress, dict):
                extra_metadata.update(progress)
                progress_value = progress.get("percentage") or progress.get("progress")
                try:
                    pct = float(progress_value) if progress_value is not None else 0.0
                except (TypeError, ValueError):
                    pct = 0.0
                message = message or stage or progress.get("stage")
                stage = stage or progress.get("stage")
            else:
                try:
                    pct = float(progress or 0.0)
                except (TypeError, ValueError):
                    pct = 0.0

            pct = max(0.0, min(100.0, pct))

            metadata: dict[str, Any] = {
                **kwargs,
                **extra_metadata,
                "job_uuid": str(job.uuid),
                "stage": stage,
            }

            progress_tracker.update_progress(
                operation_id,
                progress=pct,
                message=message or stage or "Processing",
                metadata=metadata,
            )

        return callback

    def _materialise_paths(self, files: Iterable[str | Path]) -> list[Path]:
        paths = [Path(f) for f in files]
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Document path not found: {path}")
        return paths

    async def _execute_index_builder(
        self,
        bundle: RetrievalConfigBundle,
        job: IndexJob,
        action: Callable[[Any], Any],
    ) -> None:
        if IndexBuilder is None:  # pragma: no cover
            raise RuntimeError(
                "EvidenceSeeker package is not installed; cannot perform index operations."
            )

        index_builder = IndexBuilder(
            config=bundle.config,
            progress_callback=self._progress_callback(job),
        )

        maybe_coro = action(index_builder)
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro

    def queue_update(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        user_id: int,
        documents: Sequence[Document],
    ) -> IndexJob:
        """Persist an update job for the provided documents."""
        payload = {"document_uuids": [str(doc.uuid) for doc in documents]}
        job = self._create_job(
            db=db,
            seeker=seeker,
            user_id=user_id,
            job_type="update",
            payload=payload,
        )
        if job.operation_id:
            progress_tracker.update_progress(
                job.operation_id,
                progress=1.0,
                message="Queued document ingestion",
                metadata={"job_uuid": str(job.uuid)},
            )
        return job

    def queue_delete(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        user_id: int,
        documents: Sequence[Document],
    ) -> IndexJob:
        payload = {"document_uuids": [str(doc.uuid) for doc in documents]}
        job = self._create_job(
            db=db,
            seeker=seeker,
            user_id=user_id,
            job_type="delete",
            payload=payload,
        )
        if job.operation_id:
            progress_tracker.update_progress(
                job.operation_id,
                progress=1.0,
                message="Queued document removal",
                metadata={"job_uuid": str(job.uuid)},
            )
        return job

    async def run_update(
        self,
        db: Session,
        job: IndexJob,
        seeker: EvidenceSeeker,
        documents: Sequence[Document],
    ) -> None:
        """Execute an update job."""
        self._update_job_status(db, job, IndexJobStatus.RUNNING, "Ingesting documents")
        try:
            bundle = evidence_seeker_config_service.build_retrieval_bundle(db, seeker)
            file_paths = self._materialise_paths(doc.file_path for doc in documents)
            metadata_payload: list[dict[str, Any]] = []
            metadata_by_name: dict[str, dict[str, Any]] = {}
            for doc in documents:
                file_name = Path(doc.file_path).name
                payload = {
                    "evidence_seeker_id": str(seeker.uuid),
                    "document_uuid": str(doc.uuid),
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "file_name": file_name,
                }
                metadata_payload.append(payload)
                metadata_by_name[file_name] = payload

            def metadata_func(file_name: str) -> dict[str, Any] | None:
                """Return metadata for the requested file name."""
                key = Path(file_name).name
                metadata = metadata_by_name.get(key)
                if metadata is None:
                    logger.warning(
                        "No metadata found for %s; defaulting to file name only", key
                    )
                    return None
                return metadata

            async def _update(builder: Any) -> Any:
                return await builder.aupdate_files(
                    document_input_files=[str(path) for path in file_paths],
                    metadata_func=metadata_func,
                )

            await self._execute_index_builder(bundle, job, _update)
            for doc, metadata in zip(documents, metadata_payload, strict=False):
                doc.index_file_key = str(metadata["file_name"])
            db.commit()
        except Exception as exc:  # pragma: no cover - runtime failure path
            logger.exception("Failed to update index for job %s", job.uuid)
            self._update_job_status(
                db,
                job,
                IndexJobStatus.FAILED,
                message="Index update failed",
                error=str(exc),
            )
            raise
        else:
            self._update_job_status(
                db,
                job,
                IndexJobStatus.SUCCEEDED,
                message="Indexed documents successfully",
            )

    async def run_delete(
        self,
        db: Session,
        job: IndexJob,
        seeker: EvidenceSeeker,
        documents: Sequence[Document],
    ) -> None:
        """Execute a delete job removing files from the index."""
        self._update_job_status(db, job, IndexJobStatus.RUNNING, "Removing documents")
        try:
            bundle = evidence_seeker_config_service.build_retrieval_bundle(db, seeker)
            file_keys = [
                doc.index_file_key or Path(doc.file_path).name for doc in documents
            ]

            async def _delete(builder: Any) -> Any:
                return await builder.adelete_files(file_keys)

            await self._execute_index_builder(bundle, job, _delete)
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to delete documents for job %s", job.uuid)
            self._update_job_status(
                db,
                job,
                IndexJobStatus.FAILED,
                message="Index delete failed",
                error=str(exc),
            )
            raise
        else:
            for doc in documents:
                doc.index_file_key = None
            db.commit()
            self._update_job_status(
                db,
                job,
                IndexJobStatus.SUCCEEDED,
                message="Removed documents from index",
            )


evidence_seeker_index_service = EvidenceSeekerIndexService()
