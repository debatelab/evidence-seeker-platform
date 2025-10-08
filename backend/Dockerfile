########## Builder Stage ##########
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build dependencies (removed later by multi-stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (copy static binary)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy metadata & lock first for layer caching
COPY pyproject.toml uv.lock* ./
COPY README.md ./
COPY app ./app

# Use an in-project venv for portability to final stage
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install --upgrade pip && \
    uv pip install . && \
    find .venv -type d -name "__pycache__" -prune -exec rm -rf {} +

# Copy the rest of the source (migrations, scripts, templates, etc.)
COPY . .

########## Runtime Stage ##########
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy only the virtual environment and minimal application code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/init_db.py /app/init_db.py
COPY --from=builder /app/fix_document_data.py /app/fix_document_data.py
COPY --from=builder /app/uploads /app/uploads
COPY --from=builder /app/README.md /app/README.md

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server (no autoreload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
