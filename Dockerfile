FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

FROM base AS model-cache

RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

COPY --from=base /app/.venv /app/.venv

FROM base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=model-cache /app/.venv /app/.venv
COPY --from=model-cache /root/.cache /root/.cache

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY pyproject.toml uv.lock ./

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD sh -c 'uv run uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-7860}'
