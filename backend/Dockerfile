########## Builder Stage ##########
FROM python:3.12-slim AS builder

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

# Install uv (static binary)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy metadata first for better caching
COPY pyproject.toml uv.lock* README.md ./
COPY app ./app

# ---------- Install dependencies (CPU-only PyTorch) ----------
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install --upgrade pip wheel setuptools && \
    # Force CPU-only wheels for torch/torchvision
    uv pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.4.0 torchvision==0.19.0 && \
    # Install all other dependencies (includes sentence-transformers etc.)
    uv pip install --no-cache-dir . && \
    # Sanity check (should print "CUDA available: False")
    python -c "import torch; print('CUDA available:', torch.cuda.is_available())" && \
    # Clean up build dependencies and caches
    find .venv -type d -name "__pycache__" -prune -exec rm -rf {} + && \
    rm -rf /root/.cache /tmp/*

# Copy remaining project files (migrations, scripts, etc.)
COPY . .
RUN mkdir -p /app/uploads

# ---------- Strip binaries and reduce size ----------
# Remove static libs and strip compiled extensions to shrink image
RUN find .venv -type f -name '*.a' -delete && \
    find .venv -type f -name '*.so' -exec strip --strip-unneeded {} + 2>/dev/null || true && \
    du -sh .venv || true

########## Runtime Stage ##########
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies required by psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy only the runtime essentials
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

# Launch the FastAPI app (production)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
