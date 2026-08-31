# syntax=docker/dockerfile:1
# ──────────────────────────────────────────────────────────────────────────────
# Zion-HQ — API + agent-gateway runtime image.
#
# Installs both Python services from source (the gateway depends on the api
# package). The same image serves either entrypoint; docker-compose selects
# the command per service.
#
# Production notes (fail-closed):
#   - The container refuses to start unless ZIONHQ_ENV=production and the
#     required secrets/endpoints are supplied. See app/config.py.
#   - Build context = repo root.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps needed by some wheels (e.g. asyncpg, boto3 native bits).
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY api/ ./api/
COPY agent-gateway/ ./agent-gateway/
COPY alembic.ini ./
COPY migrations/ ./migrations/

RUN pip install --upgrade pip \
 && pip install -e ./api \
 && pip install -e ./agent-gateway

# Healthcheck: the API exposes /healthz when running.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Default: start the REST/WebSocket API.
# Override with --entrypoint python -m gateway.server for the gRPC gateway.
EXPOSE 8000 50051
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
