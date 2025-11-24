# Fix Fact-Check First-Run Timeout

## Problem
- The first fact-check request after a deploy/boot routinely exceeds the 10s frontend axios timeout.
- Subsequent runs are fast and complete; results exist when the page is reloaded, so this is a cold-start/initialization delay, not a pipeline failure.

## Findings
- `POST /evidence-seekers/{id}/runs` should be quick—it only builds the retrieval bundle, creates the DB row, and enqueues a background task—yet the first request stalls.
- The likely culprit is cold-start work inside `_get_or_create_pipeline` (HF/Together model routing, embedding backend init, etc.) that happens when the first run is executed.
- We currently do no proactive warm-up after deploy/restart.

## Goals
1. Eliminate first-run latency so the create-run call returns well under 10s.
2. Keep UI timeout at 10s (do not relax client timeout).

## Proposed Changes

### 1) Backend warm-up on startup
- Add a FastAPI startup hook to warm pipelines for all “ready” Evidence Seekers:
  - For each seeker with `settings.status.is_ready`, call `evidence_seeker_config_service.build_retrieval_bundle` and `evidence_seeker_pipeline_manager._get_or_create_pipeline(...)`.
  - Run this in a background task so app startup is not blocked; cap concurrency (reuse the existing semaphore) to avoid stampedes.
- Make warm-up controllable:
  - Env flag `EVSE_ENABLE_WARMUP` (default `true`) to allow disabling if needed.
  - Optional `EVSE_WARMUP_MAX` to limit how many seekers to warm (e.g., first N by updated_at) on large fleets.
- Log durations per seeker and total; emit a clear “warmup complete” line.

### 2) Explicit warm-up endpoint/command for ops
- Provide a management script/CLI command to trigger warm-up manually (e.g., `python -m app.scripts.warmup_pipelines`) that reuses the same warm-up routine.
- Document running this post-deploy (or via CI/CD hook) to preheat models before traffic arrives.

### 3) Better instrumentation around first-run path
- Add structured timing logs around:
  - `create_fact_check_run` endpoint (db bundle creation, enqueue).
  - `_get_or_create_pipeline` and the first `_execute_pipeline` call.
- This will validate that post-warmup the endpoint returns quickly and help catch future regressions.

### 4) Optional tuning (evaluate after warm-up)
- If startup warm-up is still insufficient, consider:
  - Increasing uvicorn workers to ≥2 so a single blocking init cannot starve the event loop.
  - Offloading pipeline execution to a worker process (Celery/RQ) to isolate heavy LLM calls from API responsiveness.

## Non-Goals
- Do not raise the axios timeout.
- No functional changes to fact-check logic or result schema.

## Rollout Plan
1. Implement warm-up routine and startup hook with logging/guards.
2. Add management script for manual warm-up; wire into deploy docs/pipeline.
3. Deploy; verify logs show warm-up completion before first user traffic.
4. Observe first-run latency; only if needed, apply uvicorn worker bump or worker offload.
