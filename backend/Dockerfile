# Self-contained: build from THIS directory (backend/), e.g.:
#   docker build -f backend/Dockerfile -t fexo-backend backend/
# docker-compose.yml and render.yaml are already wired to do this for you.
#
# Backend-only image: the frontend (templates/static, FRONTEND_DIR) is a
# separate repo deployed independently (e.g. on Vercel) and is NOT baked
# into this image. Until the two are wired together at runtime, storefront
# pages that render frontend templates will error — the admin panel
# (/admin/) and /healthz/ don't depend on it and work fine on their own.
#
# App code lives at /app/backend (not /app) so FRONTEND_DIR's default
# ("sibling of backend/") lands at the conventional /app/frontend, same as
# every other doc in this repo — if/when you wire the frontend back in,
# COPY or bind-mount it to /app/frontend, or set FRONTEND_DIR explicitly.
FROM python:3.12-slim

# Fail fast on unhandled exceptions instead of buffering output, and don't
# write .pyc files into the image layer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# curl is only used by the HEALTHCHECK instruction below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x ./docker-entrypoint.sh \
    && mkdir -p staticfiles media

# Runs as a non-root user in production.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/healthz/" || exit 1

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
