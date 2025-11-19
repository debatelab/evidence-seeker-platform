# Security Improvements Spec

## Background
- The public Evidence Seeker page warns “Public runs are rate limited to prevent abuse” (`frontend/src/pages/public/PublicEvidenceSeekerPage.tsx:243-252`), but the backing route (`backend/app/api/public.py:260-305`) currently enqueues unlimited anonymous runs.
- Public endpoints sit behind a single Nginx reverse proxy (`nginx/prod.conf`) without any `limit_req`, connection caps, or request-size guards beyond the 10 MB default.
- The pipeline already enforces a concurrency semaphore (`backend/app/core/evidence_seeker_pipeline.py:72-189`), but that only slows execution; attackers can still create unbounded queued runs and overwhelm Postgres, disk, or API workers.

## Goals
1. Add lightweight protections suitable for a prototype (single host, low traffic) without needing new infrastructure such as Redis or an external WAF.
2. Ensure product copy reflects actual safeguards so users get accurate expectations.
3. Keep the solution simple to operate: everything should live inside the existing FastAPI + Nginx stack and reuse current config tooling (.env, docker-compose).

## Proposed Changes

1. **Backend request throttling for public fact-check creation**
   - Use a simple in-process token bucket keyed by client IP to cap `/api/public/evidence-seekers/{uuid}/fact-checks` runs, e.g., 3 requests per minute with a short burst allowance.
   - Implementation sketch:
     - Create a new utility (e.g., `backend/app/core/rate_limiter.py`) that stores counters in an `asyncio` friendly LRU with timestamps (Python `collections.deque` or `cachetools.TTLCache`).
     - Add dependency to `create_public_fact_check` that extracts `request.client.host`, checks allowance, and returns `429 Too Many Requests` when exceeded.
     - Expose knobs (`PUBLIC_RUN_RATE_LIMIT_WINDOW`, `PUBLIC_RUN_RATE_LIMIT_REQUESTS`) via `Settings` in `backend/app/core/config.py` so operators can tune limits without code changes.
     - Log rejections with IP and seeker UUID to aid later tuning; hook into existing logging config.
   - This keeps scope minimal (no DB schema changes) but enforces the promise made in the UI.

2. **Align UI copy with actual limits**
   - Once backend throttling is in place, tweak the helper text in `frontend/src/pages/public/PublicEvidenceSeekerPage.tsx` to describe the new behavior (e.g., “Limited to 3 public runs per minute to prevent abuse.”).
   - Surface API errors from 429 responses so the user sees an inline warning instead of the generic “try again later.”

3. **Add burst protection at the edge**
   - Update `nginx/prod.conf` to define a `limit_req_zone` keyed by `$binary_remote_addr` (e.g., 10 req/s with burst=5) and apply it to `/api/` locations. This guards other public endpoints (search/listing) with almost no code.
   - Optionally add `limit_conn_zone` for HTTPS connections to keep any single client from hoarding sockets.
   - Document new directives in `deployment.md` so ops knows why they exist and how to tune them.

4. **Queue depth guardrail**
   - Before inserting a new public run, count pending runs (status PENDING/RUNNING) for that seeker. If over a small threshold (e.g., 10), reject with `409` and a friendly message so one noisy client cannot block everyone.
   - Implement check directly in `create_public_fact_check`. Reuse SQLAlchemy query; no migration needed.
   - Include the threshold in settings (`public_run_queue_limit_per_seeker`) for easy adjustment.

## Rollout / Testing
- Unit-test the limiter helper to ensure it blocks after the configured number of hits and resets after the window.
- Add FastAPI route tests for the 429/409 paths using `TestClient` with a mocked IP.
- Exercise the Nginx config locally via `docker-compose` (`curl` in a loop) to confirm 503/429 are returned when the limit is exceeded.
- After deployment, monitor backend logs for `rate_limit_exceeded` entries and adjust env vars if legitimate users are hitting the ceiling.
