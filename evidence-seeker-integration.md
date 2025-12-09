# EvidenceSeeker Library Integration Spec (Prototype Mode)

We are free to break backward compatibility and drop existing data. The goal is the fastest path to fully relying on the `evidence-seeker` library while keeping the platform code thin.

## 1. Objectives
- Replace all custom embedding, retrieval, and fact-check logic with the upstream `evidence-seeker` package.
- Let each Evidence Seeker store Hugging Face API keys and pipeline settings directly in our DB (no YAML files).
- Use the library’s document ingestion (IndexBuilder), metadata filtering, PostgreSQL vector store, and pipeline execution end to end.
- Provide minimal yet functional UI + API surfaces to configure seekers, upload documents, trigger fact checks, and inspect results.

## 1.a Current Status (2025-03-15)
- ✅ Backend dependencies + configuration updated (`evidence-seeker`, modern `psycopg`, EVSE settings in `app/core/config.py`).
- ✅ Legacy embedding/vector stack removed; new SQLAlchemy models + Alembic migration for settings, runs, evidence, index jobs in place.
- ✅ Core services implemented (`EvidenceSeekerConfigService`, `EvidenceSeekerIndexService`, `EvidenceSeekerPipelineManager`) with async job orchestration + progress tracking.
- ✅ API surface refactored: document upload/delete push into EVSE index jobs; new settings/runs/search endpoints under `/evidence-seekers/{uuid}`; `/search` + `/embeddings` legacy routes removed.
- ✅ Frontend UI wired to EVSE APIs: documents tab surfaces index jobs + reindex action, fact-check console executes runs with live progress, configuration tab edits/tests pipeline settings alongside API keys.
- ⏳ Frontend polish & validation: Search tab still needs UX cleanup, and we must add automated coverage for the new hooks/components.
- ⏳ Testing: backend needs unit coverage for services + endpoint smoke; frontend needs updated mocks/tests after API shift.
- ⚠️ Follow-up: harden UI error states, add frontend/backend test coverage, validate migrations on a fresh DB, and run end-to-end smoke with real EVSE responses.

## 2. Backend Plan

### 2.1 Dependencies & Environment
- Add to `backend/requirements.txt`:
  - `evidence-seeker>=latest`
  - `llama-index>=latest`
  - `llama-index-vector-stores-postgres`
  - Any additional runtime deps identified in the notebook (e.g., `psycopg[binary]`).
- Remove our LlamaIndex + sentence-transformer direct usage once the integration lands.
- Environment settings exposed via `app/core/config.py`:
  - `EVSE_RUN_TIMEOUT_SECONDS` (default 900)
  - `EVSE_MAX_CONCURRENT_RUNS` (default 5)
  - `EVSE_DEFAULT_MODEL`
  - `EVSE_POSTGRES_SCHEMA` + `EVSE_POSTGRES_TABLE_PREFIX` if we want to isolate library tables.

### 2.2 Database Schema (brand new tables only)
Because data can be dropped, we can recreate schema from scratch:

1. **Drop obsolete structures immediately**
   - Remove `embeddings` table and related SQLAlchemy models/services.
   - Delete `EmbeddingService`, `VectorSearchService`, `/search` endpoints, and any background tasks that call them.

2. **Create new tables**
   - `evidence_seeker_settings`
     - `id` PK, `evidence_seeker_id` FK, `huggingface_api_key_id` FK.
     - Columns: `default_model`, `temperature`, `top_k`, `rerank_k`, `max_tokens`, `language`, `metadata_filters` JSONB (default enforces `evidence_seeker_id`), `pipeline_overrides` JSONB, `last_validated_at`, `updated_by`.
   - `fact_check_runs`
     - `id` PK, `uuid` unique, `evidence_seeker_id` FK, `submitted_by` FK, timestamps (`created_at`, `began_at`, `completed_at`), `statement`, `status` ENUM (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`), `error_message`, `config_snapshot` JSONB, `metrics` JSONB (processing time, token usage, cost).
   - `fact_check_results`
     - FK `run_id`, `interpretation_index`, `interpretation_text`, `interpretation_type` ENUM, `confirmation_level` ENUM, `confidence_score`, `summary`, `raw_payload` JSONB.
   - `fact_check_evidence`
     - FK `result_id`, `library_node_id`, `document_uuid`, optional `document_id`, `chunk_label`, `evidence_text`, `stance` ENUM (`SUPPORTS`, `REFUTES`, `NEUTRAL`), `score`, `metadata` JSONB (includes file name, page, etc.).
   - Optional `index_jobs` table storing ingestion attempts (`id`, `evidence_seeker_id`, `job_type`, `status`, `payload`, timestamps, `error`).

### 2.3 Services

- **Settings Service (`EvidenceSeekerConfigService`)**
  - CRUD for `evidence_seeker_settings`.
  - Resolve decrypted HF key via existing `config_service`.
  - Produce library `RetrievalConfig` (Postgres backend) + pipeline kwargs, injecting mandatory metadata filter `{"evidence_seeker_id": seeker.uuid}`.
  - `test_configuration` endpoint that instantiates a retriever and executes a lightweight retrieval to validate the key/config.

- **Index Service (`EvidenceSeekerIndexService`)**
  - On document upload/update, build a metadata map keyed by file name and pass it via `metadata_func`:
    ```python
    metadata_map = {
        Path(doc.file_path).name: {
            "evidence_seeker_id": str(seeker.uuid),
            "document_uuid": str(doc.uuid),
            "document_title": doc.title,
            "uploaded_by": current_user.id,
            "uploaded_at": doc.created_at.isoformat(),
        }
        for doc in documents
    }

    async def update(builder: IndexBuilder) -> None:
        await builder.aupdate_files(
            document_input_files=[str(Path(doc.file_path)) for doc in documents],
            metadata_func=lambda filename: metadata_map.get(Path(filename).name),
        )
    ```
  - For deletes, call `IndexBuilder.delete_files`/`adelete_files` with the stored `file_name` from metadata.
  - Use async variants where helpful (`aupdate_files`, `adelete_files`).
  - Track job status in `index_jobs` and broadcast progress via `progress_tracker`.
  - Job tracking pattern (start/complete) for uploads:
    ```python
    def start_index_job(seeker_id: int, user_id: int, job_type: str, payload: dict) -> IndexJob:
        job = index_jobs_repo.create(seeker_id=seeker_id, job_type=job_type, payload=payload, user_id=user_id)
        operation_id = progress_tracker.start_operation(
            operation_type=f"index_{job_type}",
            user_id=user_id,
            evidence_seeker_id=seeker_id,
            metadata={"job_id": job.id},
        )
        index_jobs_repo.attach_operation(job.id, operation_id)
        progress_tracker.update_progress(operation_id, 1, "Queued")
        return job
    ```
    Pass `operation_id` into the async worker so each stage can call `progress_tracker.update_progress(operation_id, pct, "message", metadata={...})` just like the notebook’s progress callback.
  - Recommended upload flow (FastAPI route) illustrates single-document ingestion:
    ```python
    @router.post("/documents/upload", response_model=DocumentRead)
    async def upload_document(
        file: UploadFile,
        title: str = Form(...),
        description: str | None = Form(None),
        seeker_uuid: UUID = Form(...),
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        seeker = db.scalar(select(EvidenceSeeker).where(EvidenceSeeker.uuid == seeker_uuid))
        if not seeker:
            raise HTTPException(status_code=404, detail="Evidence Seeker not found")

        db_doc = Document.create_from_upload(...)  # legacy helper to store file row
        db.commit()

        job = index_jobs_repo.start_job(
            evidence_seeker_id=seeker.id,
            job_type="upload",
            document_uuid=db_doc.uuid,
            user_id=user.id,
        )

        metadata_map = {
            Path(db_doc.file_path).name: {
                "evidence_seeker_id": str(seeker.uuid),
                "document_uuid": str(db_doc.uuid),
                "document_title": db_doc.title,
                "uploaded_by": user.id,
            }
        }
        background_tasks.add_task(
            evidence_seeker_index_service.update_files,
            seeker=seeker,
            files=[Path(db_doc.file_path)],
            metadata_map=metadata_map,
            job_id=job.id,
        )
        progress_tracker.update_progress(job.operation_id, 5, "Queued upload")
        return DocumentRead.model_validate(db_doc)
    ```
  - For updates and deletes:
    ```python
    async def update_document(seeker: EvidenceSeeker, doc: Document, job_id: int) -> None:
        index_builder = IndexBuilder(config=config_service.build_retrieval_config(seeker))
        progress_tracker.update_progress(job_id, 10, "Reindexing document")
        metadata_map = {
            Path(doc.file_path).name: {
                "evidence_seeker_id": str(seeker.uuid),
                "document_uuid": str(doc.uuid),
            }
        }
        await index_builder.aupdate_files(
            document_input_files=[str(Path(doc.file_path))],
            metadata_func=lambda filename: metadata_map.get(Path(filename).name),
        )
        progress_tracker.complete_operation(job_id, "Document reindexed")

    async def delete_document(seeker: EvidenceSeeker, doc: Document, job_id: int) -> None:
        index_builder = IndexBuilder(config=config_service.build_retrieval_config(seeker))
        progress_tracker.update_progress(job_id, 10, "Removing document from index")
        await index_builder.adelete_files([doc.original_filename])
        progress_tracker.complete_operation(job_id, "Document deleted from index")
    ```
    The above mirrors notebook examples (`IndexBuilder.update_files/delete_files`) and keeps metadata filtering intact. For deletes, pass the exact file names stored in metadata (`metadata["file_name"]` in the notebook); we can persist that value alongside document rows to guarantee a match.

  - Because data is disposable, no need for partial migrations—simply rebuild the index when code changes.

- **Pipeline Manager (`EvidenceSeekerPipelineManager`)**
  - Per seeker: caches the EvidenceSeeker pipeline (retriever + confirmation pipeline) keyed by config hash.
  - `run_fact_check(statement, overrides)`:
    1. Acquire semaphore (`EVSE_MAX_CONCURRENT_RUNS`).
    2. Create metadata filters combining seeker filter + explicit overrides (e.g., subset of document UUIDs).
    3. Start `fact_check_runs` row with `RUNNING`.
    4. Execute pipeline asynchronously, streaming stage updates to `progress_tracker`.
    5. Persist interpretations/evidence by iterating library output.
    6. Update metrics (duration, token usage if provided).
    7. Handle cancellation requests by consulting `progress_tracker` (if not supported natively, finish current step then mark as cancelled).
    8. On error, capture sanitized message, set status `FAILED`.
  - Suggested implementation sketch referencing the notebook’s retriever usage:
    ```python
    class EvidenceSeekerPipelineManager:
        def __init__(self, settings_service: EvidenceSeekerConfigService) -> None:
            self._settings = settings_service
            self._pipelines: dict[int, CachedPipeline] = {}
            self._semaphore = asyncio.Semaphore(settings.EVSE_MAX_CONCURRENT_RUNS)

        async def run_fact_check(
            self,
            seeker: EvidenceSeeker,
            statement: str,
            user_id: int,
            overrides: dict | None = None,
        ) -> FactCheckRun:
            async with self._semaphore:
                config = self._settings.build_pipeline_config(seeker, overrides)
                pipeline = await self._get_or_create_pipeline(seeker.id, config)

                metadata_filter = pipeline.retriever.create_metadata_filters({
                    "evidence_seeker_id": str(seeker.uuid),
                    **(overrides.get("metadata_filters", {}) if overrides else {})
                })

                run = runs_repo.create_run(seeker.id, user_id, statement, config_snapshot=config.asdict())
                operation_id = progress_tracker.start_operation(
                    "fact_check_run", user_id=user_id, evidence_seeker_id=seeker.id, metadata={"run_uuid": str(run.uuid)}
                )

                try:
                    progress_tracker.update_progress(operation_id, 5, "Initialising pipeline")
                    result = await pipeline.run_fact_check(statement, metadata_filters=metadata_filter)
                    persistence.save_run_output(run, result)
                    progress_tracker.complete_operation(operation_id, "Fact-check completed", metadata={"run_uuid": str(run.uuid)})
                    return runs_repo.mark_succeeded(run.id, result.metrics)
                except Exception as exc:
                    progress_tracker.fail_operation(operation_id, f"Failed: {exc}")
                    return runs_repo.mark_failed(run.id, str(exc))

        async def _get_or_create_pipeline(self, seeker_id: int, config: PipelineConfig) -> EvidenceSeekerPipeline:
            cache = self._pipelines.get(seeker_id)
            if cache and cache.config_hash == config.hash():
                return cache.pipeline
            retriever_config = self._settings.build_retrieval_config(config)
            retriever = DocumentRetriever(config=retriever_config)
            pipeline = EvidenceSeekerPipeline(config=pipeline_builder.build(config), retriever=retriever)
            self._pipelines[seeker_id] = CachedPipeline(config_hash=config.hash(), pipeline=pipeline)
            return pipeline
    ```
    The caching wrapper can be invalidated whenever settings or API keys change (`pipeline_manager.invalidate(seeker_id)`). Metadata filters follow the notebook’s `create_metadata_filters` usage.

### 2.4 API Surface (all under `/api/v1/evidence-seekers/{uuid}` unless noted)
- `GET /settings` – Fetch settings + HF key status.
- `PUT /settings` – Upsert settings (EVSE admin).
- `POST /settings/test` – Validate config by running a quick retriever test.
- `POST /documents/reindex` – Rebuild entire index (admin).
- `POST /runs` – Submit statement, optional overrides: `documents` (list of document UUIDs), `metadata_filters` map, `top_k`, etc. Returns `run_uuid` + `operation_id`.
- `GET /runs` – Paginated list with filters (`status`, `submittedBy`, `dateRange`).
- `GET /runs/{run_uuid}` – Run summary.
- `GET /runs/{run_uuid}/results` – Interpretations + evidence.
- `DELETE /runs/{run_uuid}` – Cancel.
- `POST /runs/{run_uuid}/rerun` – Rerun with stored config snapshot.

Document endpoints (`/documents/upload`, `/documents/{uuid}` delete) call the new index service instead of any platform-built embedding code.

### 2.5 Progress & Logging
- Reuse `progress_tracker` for indexing and fact-check runs with stage metadata (`statement_analysis`, `retrieval`, `confirmation`).
- Log structured events: seeker UUID, run UUID, stage, duration, error.
- Because we can reset environments at will, no need for long-term metrics storage yet.

## 3. Frontend Plan

### 3.1 API Client & Types
- Extend `frontend/src/utils/api.ts` with `evidenceSeekerAPI`:
  - `getSettings`, `updateSettings`, `testSettings`
  - `triggerReindex`
  - `createRun`, `listRuns`, `getRun`, `getRunResults`, `cancelRun`, `rerun`
- Types: `EvidenceSeekerSettings`, `FactCheckRun`, `FactCheckResult`, `FactCheckEvidence`, `IndexJob`, `MetadataFilter`.

**Status (2025-03-15):**
- ✅ `frontend/src/utils/api.ts` now exports `documentsAPI` helpers bound to the new backend contract and an `evidenceSeekerAPI` covering settings, index jobs, fact-check runs, and search (`frontend/src/utils/api.ts`).
- ✅ Added/extended TS models for settings, fact checks, search hits, and index jobs so UI code can lean on typed responses (`frontend/src/types/evidenceSeeker.ts`, `frontend/src/types/factCheck.ts`, `frontend/src/types/search.ts`, `frontend/src/types/indexJob.ts`).

### 3.2 UI Updates
- Add **Fact Checks** tab (routes `/manage/runs`):
  - Statement input + advanced options (optional metadata filters, doc selection).
  - Active run card with `ProgressIndicator`.
  - Run history table (status chips, confirmation summary).
  - Run detail view with interpretations grouped by confirmation level; each evidence card links to document view/download.
- Update **Documents** tab:
  - Show ingestion status from `index_jobs`.
  - Offer “Rebuild Index” button (EVSE admin).
- Update **Config** tab:
  - Pipeline settings form bound to new endpoints.
  - “Test Configuration” action that displays success/failure message.
  - When showing configuration, include metadata filter preview (e.g., `{"evidence_seeker_id": "...", ...}`) so admins understand applied filters.
- Update **AI Search** tab to call backend route that proxies EvidenceSeeker metadata-filtered retrieval; include UI for custom metadata filters (basic key/value advanced drawer).

**Status:** ✅ Documents, fact-check, and configuration tabs are live with EVSE-backed flows; search tab already calls the new retrieval endpoint. Remaining work is polish + validation states.

### 3.3 Hooks
- `useEvidenceSeekerSettings`
- `useEvidenceSeekerRuns` (list + create + cancel + rerun + polling)
- `useEvidenceSeekerRunDetails` (folded into `useEvidenceSeekerRuns.getRunDetail`)
- `useIndexJobs`
- Replace `useSearch` implementation with library-backed endpoint.

**Status:**
- ✅ `useEvidenceSearch` replaces legacy `/search` hook and targets `/evidence-seekers/{uuid}/search`. Also added shared `useSystemStatistics`.
- ✅ Document hook now calls the new upload/delete endpoints and returns ingestion metadata.
- ✅ Hooks for settings, runs (including detail/results helpers), and index jobs implemented; progress polling helper reused for run console updates.

### 3.4 Permissions & UX
- Gate settings, reindex, and run submission with `PermissionGuard` requiring `EVSE_ADMIN` (easy to relax later).
- Show warnings if HF key missing or configuration invalid.
- Use lightweight toasts/alerts for reindex + run actions; we don’t worry about long-term audit trails.

## 4. DevOps Notes
- We can drop and recreate DB tables at will; no migration choreography needed. Alembic scripts simply drop legacy tables and create new ones.
- Ensure Postgres has `pgvector` extension enabled. If not, create it during migration (`CREATE EXTENSION IF NOT EXISTS vector;`).
- Docker images must install new dependencies; no need to preserve legacy artifacts.
- Because the system is disposable, we can rely on manual reindex after deployments rather than incremental migrations.

## 5. Testing Strategy (pragmatic)
- Backend unit tests for:
  - Settings serialization
  - Index service calling library (mock EvidenceSeeker objects)
  - Pipeline manager run happy path + error path
  - API permission checks
- Integration smoke test: spin up Postgres (pgvector), run ingestion + fact-check with mocked HF client to assert metadata filters.
- Frontend: component test for run console and settings form, plus Cypress/Playwright happy path (upload → reindex → run → view results).
Because we can discard data, tests only need to prove functionality, not migration safety.

## 6. Rollout (fast path)
1. Merge backend changes, drop legacy tables, deploy.
2. Manually reupload sample docs and run `IndexBuilder` via API.
3. Verify fact-check run in staging with real/mocked HF key.
4. Wire up frontend tabs to new endpoints.
5. Iterate quickly; if issues arise, wipe DB/index and repeat.

This simplified plan embraces the prototype nature: no backward compatibility, no data migration, immediate replacement of old services with the EvidenceSeeker library.

## 7. Execution Checklists

### 7.1 Backend
- ✅ Dependencies landed (`backend/requirements.txt`, environment variables in `config.py`).
- ✅ New SQLAlchemy models + Alembic migrations scaffolded for settings, runs, results, evidence, index jobs.
- ✅ **Implement settings service wiring** – `EvidenceSeekerConfigService` now validates inputs, enforces metadata filter injection, and exposes overrides (`backend/app/core/evidence_seeker_config_service.py`).
- 🛠️ **Index service background tasks** – adapt upload/delete routes to enqueue `IndexBuilder` jobs and record them in `index_jobs` (`backend/app/api/documents.py`, `backend/app/services/evidence_seeker_index_service.py`).
- 🛠️ **Pipeline manager orchestration** – complete async pipeline execution path, progress hooks, and persistence of run/evidence payloads (`backend/app/services/evidence_seeker_pipeline_manager.py`, `backend/app/repositories/fact_check_runs.py`).
- 🛠️ **API endpoints** – finalize FastAPI routers for settings, runs, results, and reindex operations (`backend/app/api/evidence_seekers.py`, `backend/app/api/search.py` legacy cleanup).
- 🔍 **Testing** – author unit tests covering services + routers; wire integration smoke test with mocked EvidenceSeeker client (`backend/tests/test_evidence_seeker_*.py`). *Config service unit coverage added (`backend/tests/test_evidence_seeker_config_service.py`).*

### 7.2 Frontend
- ✅ Type definitions drafted for documents, runs, search (`frontend/src/types/*.ts`).
- ✅ **API client module** – `evidenceSeekerAPI` + enhanced `documentsAPI` implemented with typed responses (`frontend/src/utils/api.ts`).
- ✅ **Hooks** – `useEvidenceSeekerSettings`, `useEvidenceSeekerRuns`, `useIndexJobs`, and refreshed document/search hooks now consume the new API surface.
- ✅ **Fact Checks tab UI** – run submission, live progress, history, rerun/cancel, and evidence detail view shipped (`frontend/src/components/EvidenceSeeker/*`).
- ✅ **Documents tab refresh** – ingestion job list, metadata filter preview, and manual reindex action exposed.
- ✅ **Config tab adjustments** – pipeline settings form saved/tested via EVSE endpoints alongside API key management.
- 🔍 **Frontend tests** – update Vitest mocks + component tests; add happy-path e2e scenario (Cypress/Playwright).

### 7.3 DevOps & Data
- ✅ Docker + runtime images include new dependencies.
- 🛠️ Ensure `pgvector` extension automatically created in dev/staging migrations.
- 🛠️ Document manual reindex procedure in `deployment.md`.
- 🛠️ Provide rollback switches (feature flag or environment) in case we need to disable new endpoints temporarily.

### 7.4 Documentation & Enablement
- 🛠️ Update README + internal runbooks to point to EvidenceSeeker-powered flows.
- 🛠️ Record demo script: upload document → observe indexing job → run fact check → inspect results.

## 8. API Contract Details

### 8.1 Settings
- **GET** `/api/v1/evidence-seekers/{seeker_uuid}/settings`
  ```json
  {
    "default_model": "BAAI/bge-m3",
    "temperature": 0.2,
    "top_k": 8,
    "rerank_k": 25,
    "max_tokens": 1200,
    "language": "en",
    "metadata_filters": {
      "evidence_seeker_id": "4f1c7a05-…",
      "custom": {"topic": "climate"}
    },
    "pipeline_overrides": {},
    "huggingface_key_status": "linked",
    "last_validated_at": "2025-03-10T18:42:00Z",
    "updated_by": 42
  }
  ```
- **PUT** – accepts the above schema (minus status fields) and returns updated settings.
- **POST** `/settings/test`
  ```json
  {
    "ok": true,
    "latency_ms": 820,
    "documents_checked": 2,
    "message": "Retriever validated successfully."
  }
  ```

### 8.2 Documents
- **POST** `/documents/upload` – multipart form (`file`, `title`, `description`, `seeker_uuid`). Returns `DocumentRead` plus queued job metadata.
- **DELETE** `/documents/{document_uuid}` – removes doc, enqueues delete job, responds with `202 Accepted`.
- **POST** `/documents/reindex`
  ```json
  {
    "operation_id": "op_123",
    "job_id": 87,
    "status": "QUEUED"
  }
  ```
- **GET** `/documents/index-jobs`
  ```json
  [
    {
      "id": 87,
      "job_type": "upload",
      "status": "RUNNING",
      "progress": 45,
      "started_at": "2025-03-11T14:13:00Z",
      "updated_at": "2025-03-11T14:13:45Z",
      "payload": {
        "document_uuid": "2dfe-…",
        "file_name": "policy.pdf"
      }
    }
  ]
  ```

### 8.3 Fact Check Runs
- **POST** `/runs`
  ```json
  {
    "statement": "Germany will achieve carbon neutrality by 2030.",
    "metadata_filters": {
      "document_uuid": ["2dfe-…", "fa77-…"]
    },
    "overrides": {
      "top_k": 6,
      "temperature": 0.1
    }
  }
  ```
  Response:
  ```json
  {
    "run_uuid": "0f95f6f0-…",
    "operation_id": "op_456",
    "status": "PENDING"
  }
  ```
- **GET** `/runs`
  ```json
  {
    "items": [
      {
        "run_uuid": "0f95f6f0-…",
        "status": "RUNNING",
        "statement": "Germany will achieve carbon neutrality by 2030.",
        "submitted_by": {"id": 7, "name": "Ada Lovelace"},
        "created_at": "2025-03-11T14:15:00Z",
        "began_at": "2025-03-11T14:15:05Z",
        "completed_at": null,
        "metrics": {"latency_seconds": null},
        "last_progress": {"stage": "retrieval", "percent": 60}
      }
    ],
    "next_cursor": "eyJpZCI6…"
  }
  ```
- **GET** `/runs/{run_uuid}`
  ```json
  {
    "run_uuid": "0f95f6f0-…",
    "status": "SUCCEEDED",
    "statement": "Germany will achieve carbon neutrality by 2030.",
    "config_snapshot": {...},
    "metrics": {"latency_seconds": 132, "tokens": 14800},
    "submitted_by": {"id": 7, "name": "Ada Lovelace"},
    "created_at": "2025-03-11T14:15:00Z",
    "began_at": "2025-03-11T14:15:05Z",
    "completed_at": "2025-03-11T14:17:12Z"
  }
  ```
- **GET** `/runs/{run_uuid}/results`
  ```json
  {
    "interpretations": [
      {
        "index": 0,
        "text": "Germany will become carbon neutral by 2030.",
        "type": "DESCRIPTIVE",
        "confirmation_level": "weakly_confirmed",
        "confidence_score": 0.62,
        "summary": "Two policy documents outline plans but lack binding commitments.",
        "evidence": [
          {
            "document_uuid": "2dfe-…",
            "document_title": "Climate Roadmap 2030",
            "chunk_label": "page_12",
            "stance": "SUPPORTS",
            "score": 0.81,
            "excerpt": "The government aims for neutrality by 2045, with interim 2030 milestones.",
            "metadata": {"page": 12, "section": "Targets"}
          }
        ]
      }
    ]
  }
  ```
- **DELETE** `/runs/{run_uuid}` – cancels if run still pending; returns 204.
- **POST** `/runs/{run_uuid}/rerun` – triggers rerun using stored config snapshot.

## 9. EvidenceSeeker Library Mapping

- **IndexBuilder**
  - Use `IndexBuilder(config)` from the README to ingest files.
  - Provide per-file metadata containing `evidence_seeker_id`, `document_uuid`, file name, and provenance.
  - In deletion flows, reference the `file_name` recorded during ingestion to guarantee removal.

- **DocumentRetriever**
  - Configure via `llama_index-vector-stores-postgres` integration.
  - Instantiate with metadata filters using `create_metadata_filters` helper described in `retriever_new_features.ipynb`.
  - Respect overrides (`top_k`, `rerank_k`) by updating retriever kwargs before execution.

- **EvidenceSeekerPipeline**
  - Build pipeline with `EvidenceSeekerPipeline.from_settings(...)` (or equivalent builder from README).
  - Stream progress by subscribing to pipeline callbacks (statement analysis → retrieval → confirmation).
  - Persist `ConfirmationResult` objects to `fact_check_results`/`fact_check_evidence`.

- **Configuration**
  - Settings map to README defaults: `default_model`, `temperature`, `max_tokens`.
  - Hugging Face API key stored in DB, injected into pipeline config when building LLM/embedding clients.
  - Optional YAML overrides from README should be transcribed into JSON stored in `pipeline_overrides`.

- **CLI/Manual Tools**
  - For debugging, developers can still run `evse run` locally against the same Postgres schema by pointing environment variables to the shared DB.
  - Document this workflow for operations engineers needing to backfill or diagnose issues.

## 10. Open Questions & Follow-Ups
- Do we need audit logging for changes to EvidenceSeeker settings beyond existing `updated_by`? (If yes, extend to track previous values.)
- Clarify Hugging Face quota limits to decide on rate limiting or queuing policies.
- Determine whether we expose confirmation metrics in analytics dashboards (optional future work).
- Confirm if fact-check cancellation should terminate in-flight LLM calls or simply mark run as cancelled post-step.
- Validate whether to retain legacy `/search` UI under a feature flag during transition or fully replace it.
