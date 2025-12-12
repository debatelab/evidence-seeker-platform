"""
Index management utilities wrapping the EvidenceSeeker IndexBuilder.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.evidence_seeker_config_service import (
    RetrievalConfigBundle,
    evidence_seeker_config_service,
)
from app.core.progress_tracker import progress_tracker
from app.models import Document, EvidenceSeeker, IndexJob, IndexJobStatus

logger = logging.getLogger(__name__)

# Ensure NLTK resources are available for llama-index sentence parsing.
_NLTK_READY = False

try:  # pragma: no cover - optional dependency during tests
    from evidence_seeker.retrieval.index_builder import IndexBuilder as _IndexBuilder
except ImportError:  # pragma: no cover
    IndexBuilder = None
else:
    IndexBuilder = cast(type[Any], _IndexBuilder)
    # Add retries for HF Inference embeddings to survive transient 5xx/504 responses.
    try:
        import evidence_seeker.retrieval.base as es_base
        import tenacity

        hf_inference_base = getattr(es_base, "HFTextEmbeddingsInference", None)
        HFInferenceBase: type[Any] | None
        if isinstance(hf_inference_base, type):
            HFInferenceBase = cast(type[Any], hf_inference_base)
        else:
            HFInferenceBase = None

        if HFInferenceBase is not None and not getattr(
            HFInferenceBase, "__evse_retry_wrapped__", False
        ):
            assert isinstance(HFInferenceBase, type)

            class _RetryingHFTextEmbeddingsInference(HFInferenceBase):  # type: ignore[misc,valid-type]
                """Wrap HF inference calls with exponential backoff."""

                @tenacity.retry(
                    reraise=True,
                    stop=tenacity.stop_after_attempt(6),
                    wait=tenacity.wait_exponential(multiplier=1, max=20),
                )
                def _call_api(self, texts: list[str]) -> list[list[float]]:
                    result = super()._call_api(texts)
                    return cast(list[list[float]], result)

                @tenacity.retry(
                    reraise=True,
                    stop=tenacity.stop_after_attempt(6),
                    wait=tenacity.wait_exponential(multiplier=1, max=20),
                )
                async def _acall_api(self, texts: list[str]) -> list[list[float]]:
                    result = await super()._acall_api(texts)
                    return cast(list[list[float]], result)

            _RetryingHFTextEmbeddingsInference.__evse_retry_wrapped__ = True
            es_base.HFTextEmbeddingsInference = _RetryingHFTextEmbeddingsInference
            logger.info("Patched HFTextEmbeddingsInference with retry/backoff")
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to patch HFTextEmbeddingsInference for retries")


class EvidenceSeekerIndexService:
    """Synchronises platform documents with the EvidenceSeeker vector store."""

    def __init__(self) -> None:
        if IndexBuilder is None:  # pragma: no cover
            logger.warning(
                "EvidenceSeeker library not available; index operations will fail at runtime."
            )
        self._max_index_concurrency = max(1, int(settings.evse_index_max_concurrency))
        # Semaphore must be created per event loop to avoid cross-loop binding issues.
        self._index_semaphores: weakref.WeakKeyDictionary[
            asyncio.AbstractEventLoop, asyncio.Semaphore
        ] = weakref.WeakKeyDictionary()

    def _get_index_semaphore(self) -> asyncio.Semaphore:
        """Return a semaphore bound to the current event loop."""
        loop = asyncio.get_event_loop()
        sem = self._index_semaphores.get(loop)
        if sem is None:
            sem = asyncio.Semaphore(self._max_index_concurrency)
            self._index_semaphores[loop] = sem
        return sem

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

    def _ensure_nltk_resources(self) -> None:
        """Download required NLTK data if missing (punkt + stopwords)."""
        global _NLTK_READY
        if _NLTK_READY:
            return
        try:
            import nltk  # type: ignore[import-untyped]
            from nltk.corpus import stopwords  # type: ignore[import-untyped]
            from nltk.tokenize import (  # type: ignore[import-untyped]
                PunktSentenceTokenizer,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("NLTK not available; sentence parsing may fail: %s", exc)
            return

        required = [
            ("tokenizers/punkt", "punkt"),
            ("corpora/stopwords", "stopwords"),
        ]
        for path, name in required:
            try:
                nltk.data.find(path)
            except LookupError:
                try:
                    nltk.download(name, quiet=True)
                except Exception as dl_exc:  # pragma: no cover
                    logger.warning(
                        "Failed to download NLTK resource '%s': %s", name, dl_exc
                    )

        # Preload heavy resources to avoid LazyCorpusLoader race conditions when
        # llama-index triggers sentence/stopword parsing from multiple threads.
        try:
            stopwords.words("english")
            PunktSentenceTokenizer()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "Failed to pre-initialize NLTK tokenizers/stopwords: %s", exc
            )
        _NLTK_READY = True

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

        # Ensure sentence tokenizer + stopwords are available for llama-index parsers.
        self._ensure_nltk_resources()

        index_builder = IndexBuilder(
            config=bundle.config,
            progress_callback=self._progress_callback(job),
        )
        self._patch_builder_for_serial_async(index_builder)

        maybe_coro = action(index_builder)
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro

    def _patch_builder_for_serial_async(self, builder: Any) -> None:
        """Force async updates to insert nodes sequentially to avoid HF router overload."""
        if not hasattr(builder, "_aupdate_files_in_index"):
            return

        async def _serial_aupdate_files_in_index(
            self: Any,
            index: Any,
            document_input_dir: str | None = None,
            document_input_files: list[str] | None = None,
            metadata_func: Callable[[str], dict[str, Any]] | None = None,
            track_progress: bool = True,
        ) -> bool:
            if document_input_dir and document_input_files:
                logger.warning(
                    "Both 'document_input_dir' and 'document_input_files' provided. Using 'document_input_files'."
                )
                document_input_dir = None

            if document_input_dir is not None:
                document_input_files = [
                    str(p) for p in Path(document_input_dir).glob("*") if p.is_file()
                ]

            if document_input_files is not None:
                file_names = [Path(f).name for f in document_input_files]
                await self._adelete_files_in_index(index, file_names)

                docs = self._load_documents(
                    document_input_files=document_input_files,
                    metadata_func=metadata_func,
                )
                nodes = self._nodes_from_documents(docs)
                self._reset_callback_manager(total_nodes=len(nodes))

                logger.debug(
                    "Adding %s nodes to index (serial async insert)...", len(nodes)
                )
                await index.ainsert_nodes(
                    nodes, use_async=False, show_progress=track_progress
                )
                return True

            logger.warning(
                "Neither 'document_input_dir' nor 'document_input_files' provided. No files to update."
            )
            return False

        # Bind the patched coroutine to the builder instance
        builder._aupdate_files_in_index = _serial_aupdate_files_in_index.__get__(
            builder, builder.__class__
        )

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
        async with self._get_index_semaphore():
            self._update_job_status(
                db, job, IndexJobStatus.RUNNING, "Ingesting documents"
            )
            try:
                bundle = evidence_seeker_config_service.build_retrieval_bundle(
                    db, seeker
                )
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
                            "No metadata found for %s; defaulting to file name only",
                            key,
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
        async with self._get_index_semaphore():
            self._update_job_status(
                db, job, IndexJobStatus.RUNNING, "Removing documents"
            )
            try:
                bundle = evidence_seeker_config_service.build_retrieval_bundle(
                    db, seeker
                )
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
