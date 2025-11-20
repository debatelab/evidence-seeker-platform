# Backend Resilience Improvements (Spec)

This document specifies how to implement resiliency improvements #1 and #2 that were identified after reviewing `README.md:510-534` and `docker-compose.yml:25-87`. These changes focus on making the containerized backend restart automatically when it becomes unhealthy and ensuring it runs with a production-ready application server.

## Goals
- Detect backend failures (crash loops or hung processes) and let Docker restart the container without manual intervention.
- Ensure other services (`frontend`, `nginx`) only start when the backend is responsive.
- Remove development-only reload behavior from production deployments and run FastAPI with a single, well-behaved process tree.

## Non-Goals
- High-availability or multi-host orchestration (tracked separately as idea #3).
- Scaling beyond one backend replica.

---

## Feature 1 – Backend Health Check + Auto-Restart

### Current State
- A `/health` endpoint already exists (`backend/app/main.py:117-120`), returning JSON when the app is healthy.
- The runtime `Dockerfile` defines a `HEALTHCHECK` that curls `http://localhost:8000/health`, but `docker-compose.yml:25-46` overrides the container command and lacks an explicit `healthcheck`, so service dependencies cannot react to the status.

### Requirements
1. **Docker healthcheck**  
   - Add a `healthcheck` section under the `backend` service in `docker-compose.yml` that mirrors the Dockerfile directive:  
     ```yaml
     healthcheck:
       test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
       interval: 30s
       timeout: 10s
       retries: 3
       start_period: 30s
     ```
   - Rationale: Compose-level health checks integrate with `depends_on` and ensure status is visible via `docker-compose ps`.

2. **Service dependencies respect health**  
   - Update `frontend` and `nginx` services in `docker-compose.yml` so `depends_on` waits for `backend` to be healthy before starting. Example:  
     ```yaml
     depends_on:
       backend:
         condition: service_healthy
     ```
   - Result: UI and proxy won’t start (and spam errors) until API is reachable.

3. **Recovery behavior**  
   - Confirm `restart: unless-stopped` remains on the backend service. Combined with the health check, Docker will automatically restart the container if the command exits or the health probe fails repeatedly.

### Acceptance Criteria
- `docker-compose ps` shows the `backend` service with a `healthy` status after startup.
- Killing the backend process inside the container causes Docker to restart it without manual commands.
- If `/health` returns non-200, the container is marked unhealthy and Docker retries based on the restart policy.
- `frontend` and `nginx` services wait until the backend is `healthy` before reporting `Up`.

### Open Questions
- None identified. `/health` already exists and requires no functional changes.

---

## Feature 2 – Production-Grade Server Command

### Current State
- `docker-compose.yml:25-46` runs the backend with `uvicorn ... --reload`. `--reload` spawns a parent watcher process and child worker, which is intended for local development and can interfere with Docker’s signal handling.
- The runtime `Dockerfile` already specifies `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`, so Compose is the only place still forcing reload mode.

### Requirements
1. **Remove `--reload` from production Compose**  
   - Update the `backend` service `command` in `docker-compose.yml` to either:
     - Omit `command` entirely so Docker uses the runtime `CMD`, **or**
     - Explicitly set `uvicorn app.main:app --host 0.0.0.0 --port 8000` without `--reload`.
   - Ensure documentation (`README.md` deployment section) states that `--reload` is for development only.

2. **Optional Gunicorn wrapper (future-friendly)**  
   - Consider switching to `gunicorn` with `uvicorn.workers.UvicornWorker` in production Dockerfiles later. For this iteration, simply running plain `uvicorn` without reload meets stability requirements and keeps resource usage predictable.

3. **Development workflow unaffected**  
   - If local developers depend on auto-reload, add an explicit note in `docker-compose.dev.yml` (if used) or the README instructing them to use `uvicorn --reload` only in dev environments. No changes required for this spec beyond documenting the distinction.

### Acceptance Criteria
- Running `docker-compose up` starts the backend with a single `uvicorn` worker (verify via `docker-compose logs backend` or `ps` inside the container).
- Manual file changes on the host no longer trigger automatic reloads in the production stack (expected).
- README clearly differentiates between development (reload allowed) and production (no reload) commands.

### Open Questions
- Do we want multiple workers (e.g., `--workers 2`)? For now we keep one to minimize memory consumption; scaling decisions can be revisited if CPU-bound workloads appear.

---

## Rollout & Testing
1. Implement docker-compose changes plus README updates.
2. `docker-compose up -d backend` to build and start the service, verify health with `docker-compose ps`.
3. Simulate crashes (`docker-compose exec backend pkill uvicorn`) and confirm restart occurs automatically.
4. Smoke test API endpoints to ensure there is no behavior change beyond removal of live reload.
5. Once validated, rebuild production images and redeploy via `docker-compose up -d --build`.

This spec covers only improvements #1 and #2. Any move toward orchestration beyond a single host remains out-of-scope for now.
