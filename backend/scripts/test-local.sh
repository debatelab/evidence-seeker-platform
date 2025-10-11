#!/usr/bin/env bash
set -euo pipefail

# Simple local test runner:
# - Starts Postgres test_db via docker-compose (if not already up)
# - Exports DATABASE_URL pointing at port 5433
# - Activates uv venv and runs pytest with coverage
# - Optionally stops DB on exit if it was started by this script

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pushd "$ROOT_DIR" >/dev/null

DB_URL="postgresql://evidence_user:evidence_password@localhost:5433/evidence_seeker_test"

was_running=false
if docker ps --format '{{.Names}}' | grep -q '^evidence-seeker-platform-test_db-1$'; then
  was_running=true
fi

echo "[test-local] Ensuring test_db is up..."
docker-compose -f docker-compose.dev.yml --profile testing up -d test_db

export DATABASE_URL="$DB_URL"

echo "[test-local] Running backend tests..."
cd backend

if [ ! -d .venv ]; then
  echo "[test-local] Creating Python venv with uv..."
  uv venv
fi

source .venv/bin/activate
pytest -v --cov=app --cov-report=term-missing "$@"

popd >/dev/null

if [ "$was_running" = false ]; then
  echo "[test-local] Leaving test_db running for reuse. Use 'docker-compose -f docker-compose.dev.yml --profile testing down -v' to stop."
fi

exit 0
