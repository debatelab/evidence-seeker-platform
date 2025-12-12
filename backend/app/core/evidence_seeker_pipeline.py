"""
Asynchronous fact-check execution orchestrated through the EvidenceSeeker library.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.evidence_seeker_config_service import (
    RetrievalConfigBundle,
    evidence_seeker_config_service,
)
from app.core.progress_tracker import progress_tracker
from app.models import (
    ConfirmationLevel,
    EvidenceSeeker,
    EvidenceStance,
    FactCheckEvidence,
    FactCheckPublicationMode,
    FactCheckResult,
    FactCheckRun,
    FactCheckRunStatus,
    FactCheckRunVisibility,
    InterpretationType,
)

DocumentRetriever: type[Any] | None
EvidenceSeekerPipeline: type[Any] | None
RetrievalConfig: type[Any] | None
ClaimPreprocessingConfig: type[Any] | None
ConfirmationAnalyzerConfig: type[Any] | None

try:  # pragma: no cover - optional runtime dependency
    from evidence_seeker.retrieval.document_retriever import (
        DocumentRetriever as _DocumentRetriever,
    )
except ImportError:  # pragma: no cover
    DocumentRetriever = None
else:
    DocumentRetriever = cast(type[Any], _DocumentRetriever)

try:  # pragma: no cover - pipeline is optional during unit tests
    from evidence_seeker import (
        ClaimPreprocessingConfig as _ClaimPreprocessingConfig,
    )
    from evidence_seeker import (
        ConfirmationAnalyzerConfig as _ConfirmationAnalyzerConfig,
    )
    from evidence_seeker import EvidenceSeeker as _EvidenceSeekerPipeline
    from evidence_seeker import (
        RetrievalConfig as _RetrievalConfig,
    )
except ImportError:  # pragma: no cover
    EvidenceSeekerPipeline = None
    RetrievalConfig = None
    ClaimPreprocessingConfig = None
    ConfirmationAnalyzerConfig = None
else:
    EvidenceSeekerPipeline = cast(type[Any], _EvidenceSeekerPipeline)
    RetrievalConfig = cast(type[Any], _RetrievalConfig)
    ClaimPreprocessingConfig = cast(type[Any], _ClaimPreprocessingConfig)
    ConfirmationAnalyzerConfig = cast(type[Any], _ConfirmationAnalyzerConfig)


def _hash_config(bundle: RetrievalConfigBundle) -> str:
    payload = {
        "retrieval": getattr(bundle.config, "__dict__", str(bundle.config)),
        "overrides": bundle.overrides,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class CachedPipeline:
    """Memoised pipeline with the matching configuration hash."""

    config_hash: str
    pipeline: Any


class EvidenceSeekerPipelineManager:
    """Coordinates concurrent fact-check execution and persistence."""

    def __init__(self) -> None:
        self._pipelines: dict[int, CachedPipeline] = {}
        self._semaphore = asyncio.Semaphore(settings.evse_max_concurrent_runs)
        if (
            DocumentRetriever is None or EvidenceSeekerPipeline is None
        ):  # pragma: no cover
            logger.warning(
                "EvidenceSeeker library not fully available; fact-check runs will fail until dependencies are installed."
            )

    def invalidate(self, seeker_id: int) -> None:
        """Clear cached pipeline when settings or keys change."""
        self._pipelines.pop(seeker_id, None)

    def create_fact_check_run(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        statement: str,
        user_id: int | None,
        overrides: dict[str, Any] | None = None,
        *,
        public_run: bool = False,
    ) -> FactCheckRun:
        """
        Create a fact-check run record without executing the pipeline.

        This method prepares the database record and operation tracker,
        but does not execute the actual fact-checking. Use execute_fact_check_run()
        in a background task to perform the actual analysis.
        """
        overrides = overrides or {}
        bundle = evidence_seeker_config_service.build_retrieval_bundle(
            db, seeker, overrides
        )

        run_visibility = _initial_visibility(seeker, public_run)
        run = _build_fact_check_run(
            seeker=seeker,
            statement=statement,
            user_id=user_id,
            bundle=bundle,
            visibility=run_visibility,
        )
        _apply_publication_transition(run, run_visibility)
        db.add(run)
        db.commit()
        db.refresh(run)

        operation_id = progress_tracker.start_operation(
            "fact_check_run",
            user_id=user_id or 0,
            evidence_seeker_id=seeker.id,
            metadata={"run_uuid": str(run.uuid)},
        )
        run.operation_id = operation_id
        db.commit()
        db.refresh(run)

        return run

    async def execute_fact_check_run(
        self,
        run_id: int,
        seeker_id: int,
    ) -> None:
        """
        Execute a fact-check run in the background.

        This method loads the run from the database and executes the
        evidence-seeker pipeline, updating the run status and persisting
        results as it progresses.
        """
        from ..core.database import SessionLocal

        logger.info(
            f"=== STARTING BACKGROUND TASK: execute_fact_check_run for run_id={run_id}, seeker_id={seeker_id} ==="
        )

        db = SessionLocal()
        try:
            # Load the run and seeker
            logger.debug(f"Loading run {run_id} from database...")
            run = db.query(FactCheckRun).filter(FactCheckRun.id == run_id).first()
            if run is None:
                logger.error(f"Fact-check run {run_id} not found")
                return

            seeker = (
                db.query(EvidenceSeeker).filter(EvidenceSeeker.id == seeker_id).first()
            )
            if seeker is None:
                logger.error(f"Evidence seeker {seeker_id} not found")
                run.status = FactCheckRunStatus.FAILED
                run.error_message = "Evidence seeker not found"
                run.completed_at = datetime.utcnow()
                db.commit()
                return

            operation_id = run.operation_id
            if not operation_id:
                logger.error(f"No operation_id for run {run_id}")
                run.status = FactCheckRunStatus.FAILED
                run.error_message = "Missing operation ID"
                run.completed_at = datetime.utcnow()
                db.commit()
                return

            # Extract config from snapshot
            overrides = {}
            if run.config_snapshot:
                overrides = run.config_snapshot.get("overrides", {})

            async with self._semaphore:
                try:
                    # Step 1: Initialize
                    progress_tracker.update_progress(
                        operation_id,
                        progress=5.0,
                        message="Preparing EvidenceSeeker pipeline",
                        metadata={"stage": "initialization", "run_uuid": str(run.uuid)},
                    )

                    bundle = evidence_seeker_config_service.build_retrieval_bundle(
                        db, seeker, overrides
                    )

                    logger.info(
                        f"Building pipeline for run {run_id} (seeker {seeker_id})"
                    )
                    pipeline = await self._get_or_create_pipeline(
                        seeker.id, bundle, db, seeker
                    )

                    # Step 2: Mark as running
                    run.status = FactCheckRunStatus.RUNNING
                    run.began_at = datetime.utcnow()
                    db.commit()

                    progress_tracker.update_progress(
                        operation_id,
                        progress=10.0,
                        message="Running fact check",
                        metadata={"stage": "execution", "run_uuid": str(run.uuid)},
                    )

                    # Step 3: Execute pipeline - KEY FIX: proper awaiting and logging
                    logger.info(
                        f"Executing pipeline for run {run_id} with statement: {run.statement}"
                    )
                    result = await self._execute_pipeline(
                        pipeline, bundle, run.statement, operation_id, run
                    )
                    logger.info(f"Pipeline execution completed for run {run_id}")

                    # Step 4: Validate results
                    if result is None:
                        raise ValueError("Pipeline returned None result")

                    interpretations = _extract_interpretations(result)
                    logger.info(
                        f"Extracted {len(interpretations)} interpretations from pipeline result"
                    )

                    if not interpretations:
                        logger.warning(
                            f"No interpretations found in pipeline result for run {run_id}"
                        )

                    progress_tracker.update_progress(
                        operation_id,
                        progress=80.0,
                        message="Saving results",
                        metadata={"stage": "persistence", "run_uuid": str(run.uuid)},
                    )

                    # Step 5: Persist results
                    logger.info(
                        f"Persisting {len(interpretations)} interpretations for run {run_id}"
                    )
                    self._persist_results(db, run, result)
                    logger.info(f"Successfully persisted results for run {run_id}")

                    # Step 6: Mark as succeeded
                    run.status = FactCheckRunStatus.SUCCEEDED
                    run.completed_at = datetime.utcnow()
                    run.metrics = _extract_metrics(result)
                    db.commit()

                    progress_tracker.complete_operation(
                        operation_id,
                        message="Fact-check completed successfully",
                        metadata={
                            "run_uuid": str(run.uuid),
                            "interpretation_count": len(interpretations),
                        },
                    )

                    logger.info(
                        f"Fact check run {run_id} completed successfully with {len(interpretations)} interpretations"
                    )

                except Exception as exc:  # pragma: no cover - runtime failure path
                    logger.exception(
                        "Fact-check run failed for run_id=%s, seeker_id=%s: %s",
                        run_id,
                        seeker.id,
                        str(exc),
                    )
                    run.status = FactCheckRunStatus.FAILED
                    run.error_message = str(exc)
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    progress_tracker.fail_operation(
                        operation_id,
                        error_message=str(exc),
                        metadata={"run_uuid": str(run.uuid)},
                    )
        except Exception as outer_exc:  # pragma: no cover - unexpected error path
            logger.exception(
                "Unexpected error in execute_fact_check_run for run_id=%s: %s",
                run_id,
                str(outer_exc),
            )
            try:
                run = db.query(FactCheckRun).filter(FactCheckRun.id == run_id).first()
                if run:
                    run.status = FactCheckRunStatus.FAILED
                    run.error_message = f"Unexpected error: {str(outer_exc)}"
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    if run.operation_id:
                        progress_tracker.fail_operation(
                            run.operation_id,
                            error_message=f"Unexpected error: {str(outer_exc)}",
                            metadata={"run_uuid": str(run.uuid)},
                        )
            except Exception as nested_exc:  # pragma: no cover
                logger.exception(
                    f"Failed to update run status after error: {nested_exc}"
                )
        finally:
            db.close()

    async def run_fact_check(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        statement: str,
        user_id: int | None,
        overrides: dict[str, Any] | None = None,
        *,
        public_run: bool = False,
    ) -> FactCheckRun:
        """
        Execute a fact-check run synchronously (for backwards compatibility).

        DEPRECATED: Use create_fact_check_run() + execute_fact_check_run() instead
        for proper async execution. This method is kept for compatibility but
        blocks until completion.
        """
        overrides = overrides or {}
        bundle = evidence_seeker_config_service.build_retrieval_bundle(
            db, seeker, overrides
        )

        run_visibility = _initial_visibility(seeker, public_run)
        run = _build_fact_check_run(
            seeker=seeker,
            statement=statement,
            user_id=user_id,
            bundle=bundle,
            visibility=run_visibility,
        )
        _apply_publication_transition(run, run_visibility)
        db.add(run)
        db.commit()
        db.refresh(run)

        operation_id = progress_tracker.start_operation(
            "fact_check_run",
            user_id=user_id or 0,
            evidence_seeker_id=seeker.id,
            metadata={"run_uuid": str(run.uuid)},
        )
        run.operation_id = operation_id
        db.commit()
        db.refresh(run)

        async with self._semaphore:
            try:
                progress_tracker.update_progress(
                    operation_id,
                    progress=5.0,
                    message="Preparing EvidenceSeeker pipeline",
                    metadata={"run_uuid": str(run.uuid)},
                )
                pipeline = await self._get_or_create_pipeline(
                    seeker.id, bundle, db, seeker
                )
                run.status = FactCheckRunStatus.RUNNING
                run.began_at = datetime.utcnow()
                db.commit()

                result = await self._execute_pipeline(
                    pipeline, bundle, statement, operation_id, run
                )

                self._persist_results(db, run, result)
                run.status = FactCheckRunStatus.SUCCEEDED
                run.completed_at = datetime.utcnow()
                run.metrics = _extract_metrics(result)
                db.commit()

                progress_tracker.complete_operation(
                    operation_id,
                    message="Fact-check completed",
                    metadata={"run_uuid": str(run.uuid)},
                )
                return run
            except Exception as exc:  # pragma: no cover - runtime failure path
                logger.exception("Fact-check run failed for seeker_id=%s", seeker.id)
                run.status = FactCheckRunStatus.FAILED
                run.error_message = str(exc)
                run.completed_at = datetime.utcnow()
                db.commit()
                progress_tracker.fail_operation(
                    operation_id,
                    error_message=str(exc),
                    metadata={"run_uuid": str(run.uuid)},
                )
                raise

    async def _get_or_create_pipeline(
        self,
        seeker_id: int,
        bundle: RetrievalConfigBundle,
        db: Session,
        seeker: EvidenceSeeker,
    ) -> Any:
        """
        Retrieve cached pipeline or create a new one using the EvidenceSeeker library.
        Raises RuntimeError if evidence-seeker is not installed.
        """
        cache_key = _hash_config(bundle)
        cached = self._pipelines.get(seeker_id)
        if cached and cached.config_hash == cache_key:
            logger.debug(
                "Pipeline cache hit for seeker_id={seeker_id}", seeker_id=seeker_id
            )
            return cached.pipeline

        creation_start = time.perf_counter()

        if (
            EvidenceSeekerPipeline is None or DocumentRetriever is None
        ):  # pragma: no cover
            raise RuntimeError(
                "EvidenceSeeker package is not installed; cannot create pipeline."
            )

        # Extract configs from the bundle
        # bundle.config is already a RetrievalConfig from evidence-seeker
        retrieval_config = bundle.config

        # Build preprocessing and confirmation configs from overrides
        preprocessing_config = self._build_preprocessing_config(bundle, db, seeker)
        confirmation_config = self._build_confirmation_config(bundle, db, seeker)

        # Create a DocumentRetriever with the retrieval config
        # Note: We don't pass callback_manager here because we'll handle progress
        # tracking at the pipeline execution level
        retriever = DocumentRetriever(config=retrieval_config)

        # Create the EvidenceSeeker pipeline with config objects and custom retriever
        pipeline_instance = EvidenceSeekerPipeline(
            preprocessing_config=preprocessing_config,
            retrieval_config=retrieval_config,
            retriever=retriever,
            confirmation_analysis_config=confirmation_config,
        )

        self._pipelines[seeker_id] = CachedPipeline(
            config_hash=cache_key, pipeline=pipeline_instance
        )
        logger.info(
            "Created pipeline for seeker_id={seeker_id} (cache_key={cache_key}) in {elapsed:.2f}s",
            seeker_id=seeker_id,
            cache_key=cache_key,
            elapsed=time.perf_counter() - creation_start,
        )
        return pipeline_instance

    async def warmup_pipeline(
        self,
        db: Session,
        seeker: EvidenceSeeker,
        bundle: RetrievalConfigBundle,
    ) -> None:
        """
        Ensure a pipeline is built and cached for the given seeker.

        Uses the existing concurrency semaphore to avoid overwhelming the host.
        """
        start = time.perf_counter()
        cache_key = _hash_config(bundle)
        cached = self._pipelines.get(seeker.id)
        if cached and cached.config_hash == cache_key:
            logger.debug(
                "Warmup: pipeline already cached for seeker_id={seeker_id}",
                seeker_id=seeker.id,
            )
            return

        async with self._semaphore:
            await self._get_or_create_pipeline(
                seeker_id=seeker.id, bundle=bundle, db=db, seeker=seeker
            )

        logger.info(
            "Warmup: built pipeline for seeker_id={seeker_id} in {elapsed:.2f}s",
            seeker_id=seeker.id,
            elapsed=time.perf_counter() - start,
        )

    def _build_preprocessing_config(
        self, bundle: RetrievalConfigBundle, db: Session, seeker: EvidenceSeeker
    ) -> Any:
        """Build ClaimPreprocessingConfig from bundle overrides."""
        if ClaimPreprocessingConfig is None:  # pragma: no cover
            return None

        # Get the settings to determine the API key name
        settings_row = evidence_seeker_config_service.ensure_settings(db, seeker)
        api_key_name = f"EVSE_HF_API_KEY_{settings_row.id}"

        # Extract preprocessing-related overrides
        overrides = dict(bundle.overrides)
        preprocessing_kwargs = {}

        # Required field: used_model_key - specifies which LLM model to use
        # Use "default" as the model key which should be defined in the models dict
        preprocessing_kwargs["used_model_key"] = overrides.get(
            "used_model_key", "default"
        )

        # Optional language parameter
        if "language" in overrides:
            preprocessing_kwargs["language"] = overrides["language"]

        # Configure models dictionary with a default model using Llama 3.3 70B
        # via Hugging Face Inference Provider (together.ai)
        preprocessing_kwargs["models"] = {
            "default": {
                "name": "Llama-3.3-70B-Instruct",
                "description": "Llama-3.3-70B served by Together.ai over Hugging Face",
                "base_url": "https://router.huggingface.co/v1",
                "model": "meta-llama/Llama-3.3-70B-Instruct:together",
                "api_key_name": api_key_name,
                "backend_type": "openai",
                "default_headers": {"X-HF-Bill-To": "DebateLabKIT"},
                "max_tokens": overrides.get("max_tokens", 1024),
                "temperature": overrides.get("temperature", 0.2),
                "timeout": 260,
            }
        }

        return ClaimPreprocessingConfig(**preprocessing_kwargs)

    def _build_confirmation_config(
        self, bundle: RetrievalConfigBundle, db: Session, seeker: EvidenceSeeker
    ) -> Any:
        """Build ConfirmationAnalyzerConfig from bundle overrides."""
        if ConfirmationAnalyzerConfig is None:  # pragma: no cover
            return None

        # Get the settings to determine the API key name
        settings_row = evidence_seeker_config_service.ensure_settings(db, seeker)
        api_key_name = f"EVSE_HF_API_KEY_{settings_row.id}"

        overrides = dict(bundle.overrides)
        confirmation_kwargs = {}

        # Required field: used_model_key
        confirmation_kwargs["used_model_key"] = overrides.get(
            "used_model_key", "default"
        )

        # Optional language parameter
        if "language" in overrides:
            confirmation_kwargs["language"] = overrides["language"]

        # Configure models dictionary with a default model using Llama 3.3 70B
        # via Hugging Face Inference Provider (together.ai)
        confirmation_kwargs["models"] = {
            "default": {
                "name": "Llama-3.3-70B-Instruct",
                "description": "Llama-3.3-70B served by Together.ai over Hugging Face",
                "base_url": "https://router.huggingface.co/v1",
                "model": "meta-llama/Llama-3.3-70B-Instruct:together",
                "api_key_name": api_key_name,
                "backend_type": "openai",
                "default_headers": {"X-HF-Bill-To": "DebateLabKIT"},
                "max_tokens": overrides.get("max_tokens", 1024),
                "temperature": overrides.get("temperature", 0.2),
                "timeout": 260,
            }
        }

        return ConfirmationAnalyzerConfig(**confirmation_kwargs)

    async def _execute_pipeline(
        self,
        pipeline: Any,
        bundle: RetrievalConfigBundle,
        statement: str,
        operation_id: str,
        run: FactCheckRun,
    ) -> Any:
        """
        Execute the EvidenceSeeker pipeline.

        The EvidenceSeeker instance is directly callable and returns results.
        Metadata filters are already embedded in the RetrievalConfig that was
        passed when creating the retriever.

        Note: Progress tracking is handled at a coarser level via our progress_tracker
        since the pipeline's direct call doesn't support fine-grained callbacks.
        """
        # Update progress before execution
        progress_tracker.update_progress(
            operation_id,
            progress=10.0,
            message="Executing fact-check pipeline",
            metadata={"run_uuid": str(run.uuid)},
        )

        logger.info(f"Calling pipeline with statement: {statement}")

        # Call the pipeline (it's directly callable)
        # According to the evidence-seeker docs: results = asyncio.run(pipeline("statement"))
        try:
            result = await pipeline(statement)
            logger.info(f"Pipeline call completed. Result type: {type(result)}")
            logger.info(f"Result attributes: {dir(result) if result else 'None'}")

            # Log interpretations if available
            if result:
                interpretations = _extract_interpretations(result)
                logger.info(
                    f"Extracted {len(interpretations)} interpretations from result"
                )
                for i, interp in enumerate(interpretations):
                    logger.debug(
                        f"Interpretation {i}: type={interp.type}, "
                        f"confirmation={interp.confirmation}, "
                        f"evidence_count={len(interp.evidence)}"
                    )
            else:
                logger.warning("Pipeline returned None or empty result")

        except Exception as exc:
            logger.exception(f"Pipeline execution failed: {exc}")
            raise

        # Update progress after execution
        progress_tracker.update_progress(
            operation_id,
            progress=90.0,
            message="Processing results",
            metadata={"run_uuid": str(run.uuid)},
        )

        return result

    def _build_progress_callback(
        self,
        operation_id: str,
        run: FactCheckRun,
    ) -> Callable[..., None]:
        def callback(
            progress: float | None = None,
            stage: str | None = None,
            message: str | None = None,
            **kwargs: Any,
        ) -> None:
            pct = float(progress or 0.0)
            progress_tracker.update_progress(
                operation_id,
                progress=max(0.0, min(100.0, pct)),
                message=message or stage or "Processing",
                metadata={
                    **kwargs,
                    "stage": stage,
                    "run_uuid": str(run.uuid),
                },
            )

        return callback

    def _persist_results(
        self,
        db: Session,
        run: FactCheckRun,
        result: Any,
    ) -> None:
        interpretations = _extract_interpretations(result)
        for interpretation in interpretations:
            # Convert raw payload to JSON-serializable format
            json_serializable_raw = _make_json_serializable(interpretation.raw)

            result_row = FactCheckResult()
            result_row.run_id = int(run.id)
            result_row.interpretation_index = interpretation.index
            result_row.interpretation_text = interpretation.text
            result_row.interpretation_type = interpretation.type
            result_row.confirmation_level = interpretation.confirmation
            result_row.confidence_score = _to_python_float(interpretation.confidence)
            result_row.summary = interpretation.summary
            result_row.raw_payload = json_serializable_raw
            db.add(result_row)
            db.flush()

            for evidence in interpretation.evidence:
                evidence_row = FactCheckEvidence()
                evidence_row.result_id = int(result_row.id)
                evidence_row.library_node_id = evidence.node_id
                evidence_row.document_uuid = evidence.document_uuid
                evidence_row.document_id = evidence.document_id
                evidence_row.chunk_label = evidence.label
                evidence_row.evidence_text = evidence.text
                evidence_row.stance = evidence.stance
                evidence_row.score = _to_python_float(evidence.score)
                evidence_row.metadata_payload = evidence.metadata
                db.add(evidence_row)

        db.commit()


def _to_python_float(value: Any) -> float | None:
    """Convert a value to Python native float, handling numpy types and NaN."""
    if value is None:
        return None

    # Handle numpy types
    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float):
        import math

        if math.isnan(value) or math.isinf(value):
            return None
        return value

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert an object to a JSON-serializable format.
    Handles enums, dataclasses, NaN values, numpy types, and other common non-serializable types.
    """
    import math
    from enum import Enum
    from uuid import UUID

    if obj is None or isinstance(obj, str | int | bool):
        return obj

    # Handle numpy types
    if hasattr(obj, "item"):  # numpy scalar
        obj = obj.item()  # Convert to Python native type

    # Handle NaN and infinity values
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, dict):
        return {key: _make_json_serializable(value) for key, value in obj.items()}

    if isinstance(obj, list | tuple):
        return [_make_json_serializable(item) for item in obj]

    # Handle Pydantic models (v2 and v1)
    if hasattr(obj, "model_dump"):
        return _make_json_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return _make_json_serializable(obj.dict())

    # Handle dataclasses and objects with __dict__
    if hasattr(obj, "__dict__"):
        return _make_json_serializable(obj.__dict__)

    # Fallback: convert to string
    return str(obj)


def _pipeline_config_fields(config_cls: Any) -> Iterable[str]:
    annotations = getattr(config_cls, "__annotations__", None)
    if isinstance(annotations, dict):
        return annotations.keys()
    model_fields = getattr(config_cls, "model_fields", None)
    if isinstance(model_fields, dict):
        return model_fields.keys()
    schema_callable = getattr(config_cls, "schema", None)
    if callable(schema_callable):
        schema = schema_callable()
        if isinstance(schema, dict):
            properties = schema.get("properties", {})
            if isinstance(properties, dict):
                return properties.keys()
    return []


def _serialise_config(bundle: RetrievalConfigBundle) -> dict[str, Any]:
    return {
        "retrieval_config": getattr(bundle.config, "__dict__", str(bundle.config)),
        "overrides": bundle.overrides,
    }


def _build_fact_check_run(
    seeker: EvidenceSeeker,
    statement: str,
    user_id: int | None,
    bundle: RetrievalConfigBundle,
    visibility: FactCheckRunVisibility,
) -> FactCheckRun:
    """Create a FactCheckRun instance without relying on SQLAlchemy kwargs."""
    run = FactCheckRun()
    run.evidence_seeker_id = int(seeker.id)
    run.submitted_by = user_id
    run.statement = statement
    run.status = FactCheckRunStatus.PENDING
    run.config_snapshot = _serialise_config(bundle)
    run.visibility = visibility
    return run


def _apply_publication_transition(
    run: FactCheckRun, visibility: FactCheckRunVisibility
) -> None:
    """Synchronise visibility, is_public, and timestamps."""
    run.visibility = visibility
    if visibility == FactCheckRunVisibility.PUBLIC:
        run.is_public = True
        now = datetime.utcnow()
        run.published_at = run.published_at or now
        run.featured_at = run.featured_at or now
    elif visibility == FactCheckRunVisibility.UNLISTED:
        run.is_public = False
        run.published_at = None
        run.featured_at = None
        run.featured_by_id = None
    else:
        run.is_public = False
        run.published_at = None
        run.featured_at = None
        run.featured_by_id = None
    if visibility != FactCheckRunVisibility.PUBLIC:
        run.featured_by_id = None


def _initial_visibility(
    seeker: EvidenceSeeker, public_run: bool
) -> FactCheckRunVisibility:
    if not public_run:
        return FactCheckRunVisibility.PRIVATE
    if seeker.fact_check_publication_mode == FactCheckPublicationMode.MANUAL:
        return FactCheckRunVisibility.UNLISTED
    return FactCheckRunVisibility.PUBLIC


def _extract_metrics(result: Any) -> dict[str, Any]:
    for key in ("metrics", "run_metrics", "stats"):
        metrics = (
            result.get(key) if isinstance(result, dict) else getattr(result, key, None)
        )
        if isinstance(metrics, dict):
            return metrics
    return {}


@dataclass(slots=True)
class ParsedEvidence:
    text: str
    stance: EvidenceStance
    score: float | None
    label: str | None
    node_id: str | None
    document_uuid: UUID | None
    document_id: int | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class ParsedInterpretation:
    index: int
    text: str
    type: InterpretationType
    confirmation: ConfirmationLevel | None
    confidence: float | None
    summary: str | None
    raw: dict[str, Any]
    evidence: list[ParsedEvidence]


def _extract_interpretations(result: Any) -> list[ParsedInterpretation]:
    raw_list: list[Any]

    # Handle case where result is already a list of interpretations (CheckedClaim objects)
    if isinstance(result, list):
        logger.debug(f"Result is already a list with {len(result)} items")
        raw_list = result
    elif isinstance(result, dict):
        raw_list = result.get("interpretations", [])
    else:
        raw_list = getattr(result, "interpretations", []) or []

    parsed: list[ParsedInterpretation] = []
    for idx, item in enumerate(raw_list):
        logger.debug(f"Processing interpretation {idx}: type={type(item)}")

        # Handle Pydantic models (CheckedClaim)
        if hasattr(item, "model_dump"):
            # It's a Pydantic v2 model
            source = item.model_dump()
            logger.debug(f"Pydantic model fields: {list(source.keys())}")
        elif hasattr(item, "dict"):
            # It's a Pydantic v1 model
            source = item.dict()
            logger.debug(f"Pydantic model fields: {list(source.keys())}")
        elif isinstance(item, dict):
            source = item
        else:
            source = getattr(item, "__dict__", {})

        # Map CheckedClaim fields to our internal structure
        text = source.get("text", "")

        # statement_type maps to interpretation_type
        type_raw = (
            source.get("statement_type")
            or source.get("type")
            or source.get("interpretation_type")
        )

        # confirmation_level is the main field
        confirmation_raw = (
            source.get("confirmation_level")
            or source.get("confirmation")
            or source.get("aggregate_confirmation")
        )

        # average_confirmation could be used as confidence score
        confidence = (
            source.get("average_confirmation")
            or source.get("confidence_score")
            or source.get("confidence")
        )

        # Convert NaN to None for confidence score
        if confidence is not None:
            import math

            if isinstance(confidence, float) and (
                math.isnan(confidence) or math.isinf(confidence)
            ):
                confidence = None

        # verbalized_confirmation can be used as summary
        summary = source.get("verbalized_confirmation") or source.get("summary")

        # documents list maps to evidence
        documents = source.get("documents") or []
        evidence_parsed = []

        if documents:
            logger.debug(
                f"Processing {len(documents)} documents for interpretation {idx}"
            )
            for doc in documents:
                # Convert Document to ParsedEvidence
                if isinstance(doc, dict):
                    doc_text = doc.get("text", "")
                    doc_uid = doc.get("uid")
                    doc_metadata_raw = doc.get("metadata", {})
                elif hasattr(doc, "model_dump"):
                    doc_dict = doc.model_dump()
                    doc_text = doc_dict.get("text", "")
                    doc_uid = doc_dict.get("uid")
                    doc_metadata_raw = doc_dict.get("metadata", {})
                elif hasattr(doc, "dict"):
                    doc_dict = doc.dict()
                    doc_text = doc_dict.get("text", "")
                    doc_uid = doc_dict.get("uid")
                    doc_metadata_raw = doc_dict.get("metadata", {})
                else:
                    doc_text = getattr(doc, "text", "")
                    doc_uid = getattr(doc, "uid", None)
                    doc_metadata_raw = getattr(doc, "metadata", {})

                # Convert MetaData object to dict if needed
                if hasattr(doc_metadata_raw, "model_dump"):
                    doc_metadata = doc_metadata_raw.model_dump()
                elif hasattr(doc_metadata_raw, "dict"):
                    doc_metadata = doc_metadata_raw.dict()
                elif isinstance(doc_metadata_raw, dict):
                    doc_metadata = doc_metadata_raw
                else:
                    doc_metadata = {}

                # Get confirmation score for this document if available
                confirmation_by_doc = source.get("confirmation_by_document", {})
                doc_score = confirmation_by_doc.get(doc_uid) if doc_uid else None

                evidence_parsed.append(
                    ParsedEvidence(
                        text=doc_text,
                        stance=EvidenceStance.SUPPORTS,  # Default, could be refined based on confirmation
                        score=doc_score,
                        label=doc_uid,
                        node_id=doc_uid,
                        document_uuid=_parse_uuid(doc_uid),
                        document_id=None,  # Not available in CheckedClaim
                        metadata=doc_metadata,
                    )
                )

        parsed.append(
            ParsedInterpretation(
                index=idx,
                text=text,
                type=_coerce_interpretation_type(type_raw),
                confirmation=_coerce_confirmation(confirmation_raw),
                confidence=confidence,
                summary=summary,
                raw=source,
                evidence=evidence_parsed,
            )
        )

    logger.info(f"Successfully parsed {len(parsed)} interpretations")
    return parsed


def _coerce_interpretation_type(value: Any) -> InterpretationType:
    """Convert value to InterpretationType enum."""
    # StatementType and InterpretationType are the same now
    statement_cls = getattr(value, "__class__", None)
    if statement_cls is not None and statement_cls.__name__ == "StatementType":
        return InterpretationType(getattr(value, "value", value))

    # Handle string values
    if isinstance(value, str):
        # Try direct lookup first
        for member in InterpretationType:
            if member.value == value or member.name == value:
                return member

        # Try normalized lookup
        normalized = value.replace("-", "_").replace(" ", "_").lower()
        for member in InterpretationType:
            if member.value == normalized or member.name.lower() == normalized:
                return member

    return InterpretationType.DESCRIPTIVE


def _coerce_confirmation(value: Any) -> ConfirmationLevel | None:
    """Convert value to ConfirmationLevel enum."""
    if value is None:
        return None

    if isinstance(value, ConfirmationLevel):
        return value

    # Handle string values
    if isinstance(value, str):
        # Try direct lookup first
        for member in ConfirmationLevel:
            if member.value == value or member.name == value:
                return member

        # Try normalized lookup
        normalized = value.replace("-", "_").replace(" ", "_").lower()
        for member in ConfirmationLevel:
            if member.value == normalized or member.name.lower() == normalized:
                return member

    return None


def _parse_evidence(item: Any) -> ParsedEvidence:
    if isinstance(item, dict):
        source = item
        text = source.get("text") or source.get("content") or ""
        stance_raw = source.get("stance") or source.get("label") or "SUPPORTS"
        score = source.get("score") or source.get("similarity")
        label = source.get("label") or source.get("chunk_label")
        node_id = source.get("node_id") or source.get("library_node_id")
        document_uuid = source.get("document_uuid") or source.get("document_id")
        document_db_id = source.get("document_db_id")
        metadata = source.get("metadata") or {}
    else:
        source = getattr(item, "__dict__", {})
        text = getattr(item, "text", getattr(item, "content", ""))
        stance_raw = getattr(item, "stance", getattr(item, "label", "SUPPORTS"))
        score = getattr(item, "score", getattr(item, "similarity", None))
        label = getattr(item, "label", getattr(item, "chunk_label", None))
        node_id = getattr(item, "node_id", getattr(item, "library_node_id", None))
        document_uuid = getattr(
            item, "document_uuid", getattr(item, "document_id", None)
        )
        document_db_id = getattr(item, "document_db_id", None)
        metadata = getattr(item, "metadata", {})

    stance = _coerce_stance(stance_raw)
    if isinstance(metadata, dict):
        metadata_payload = metadata
    else:
        metadata_payload = {}

    document_uuid_value = _parse_uuid(document_uuid)

    document_db_id_int = None
    if isinstance(document_db_id, int):
        document_db_id_int = document_db_id
    elif isinstance(document_uuid, int):
        document_db_id_int = document_uuid

    return ParsedEvidence(
        text=text,
        stance=stance,
        score=float(score) if score is not None else None,
        label=label,
        node_id=node_id,
        document_uuid=document_uuid_value,
        document_id=document_db_id_int,
        metadata=metadata_payload,
    )


def _coerce_stance(value: Any) -> EvidenceStance:
    if isinstance(value, EvidenceStance):
        return value
    if isinstance(value, str):
        value_upper = value.upper()
        if value_upper in EvidenceStance.__members__:
            return EvidenceStance[value_upper]
        if value_upper in ("SUPPORT", "SUPPORTING"):
            return EvidenceStance.SUPPORTS
        if value_upper in ("REFUTE", "REFUTING"):
            return EvidenceStance.REFUTES
        if value_upper in ("NEUTRAL", "UNKNOWN"):
            return EvidenceStance.NEUTRAL
    return EvidenceStance.SUPPORTS


def _parse_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:  # pragma: no cover - defensive
            return None
    return None


evidence_seeker_pipeline_manager = EvidenceSeekerPipelineManager()
