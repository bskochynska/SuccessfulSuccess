#!/bin/sh
set -e

# Run database migrations if enabled
if [ "${RUN_MIGRATIONS_ON_START:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "Skipping database migrations..."
fi

# If no arguments provided, start uvicorn with PORT env var
if [ $# -eq 0 ]; then
    PORT=${PORT:-8080}
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
else
    # Execute the provided command (from CMD in Dockerfile or docker run)
    exec "$@"
fi
