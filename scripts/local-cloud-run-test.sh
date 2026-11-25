#!/bin/bash
# Lab 9 (no-GCP-account route): run the backend image the way Cloud Run runs it
# (PORT=8080, no Lambda adapter) next to a local PostgreSQL, and call the API.
#
# Usage, from anywhere:  bash scripts/local-cloud-run-test.sh

set -euo pipefail

# This script lives in scripts/, the project root is one level up.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"

NETWORK=spry-local
DB_URL="postgresql+asyncpg://appuser:apppass@spry-db:5432/meetings"

echo "=========================================="
echo "Lab 9 — local Cloud Run readiness test"
echo "=========================================="

# Start clean so the script can be run twice.
docker rm -f spry-api spry-db >/dev/null 2>&1 || true
docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null

echo "[1] Building the backend image (the same Dockerfile Cloud Run would use)..."
docker build -t spry-backend:latest "$BACKEND_DIR"

echo "[2] Starting PostgreSQL..."
docker run -d --name spry-db --network "$NETWORK" \
  -e POSTGRES_USER=appuser -e POSTGRES_PASSWORD=apppass -e POSTGRES_DB=meetings \
  -p 5432:5432 postgres:17-alpine >/dev/null

for i in $(seq 1 30); do
  if docker exec spry-db pg_isready -U appuser -d meetings >/dev/null 2>&1; then
    echo "    PostgreSQL is ready"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "    PostgreSQL did not start"
    exit 1
  fi
  sleep 1
done

echo "[3] Starting the API as Cloud Run does: PORT=8080, migrations on start..."
docker run -d --name spry-api --network "$NETWORK" \
  -p 8080:8080 \
  -e PORT=8080 \
  -e DATABASE_URL="$DB_URL" \
  -e APP_TIMEZONE="Europe/Kyiv" \
  -e CORS_ORIGINS="http://localhost:3000" \
  -e LOG_LEVEL=INFO \
  -e RUN_MIGRATIONS_ON_START=true \
  spry-backend:latest >/dev/null

echo "[4] GET /health (runs SELECT 1 against PostgreSQL)..."
for i in $(seq 1 30); do
  if curl -fsS http://localhost:8080/health 2>/dev/null | grep -q '"database":"ok"'; then
    echo "    OK: $(curl -fsS http://localhost:8080/health)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "    health check failed; container log:"
    docker logs spry-api
    exit 1
  fi
  sleep 1
done

echo "[5] GET /api/v1/meetings without a token (the API must refuse it)..."
code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/api/v1/meetings)
echo "    HTTP $code (401 means the API checks tokens itself)"

cat <<'EOF'

Backend is running on http://localhost:8080.
To see the frontend read from the database, start it against this API:

  cd frontend
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8080 npm run dev

then open http://localhost:3000 and take the screenshot.

Stop everything:  docker rm -f spry-api spry-db
EOF
