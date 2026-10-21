# Repo-root build of backend/ for hosts that default to ./Dockerfile with the
# repo root as context (e.g. a Render service created without render.yaml).
# Same image as backend/Dockerfile — keep the two in sync.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
RUN chmod +x ./docker-entrypoint.sh \
    && mkdir -p staticfiles media

RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz/" || exit 1

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
