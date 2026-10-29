#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "Skipping database migrations for standalone service..."
fi

# Якщо передані аргументи командами (наприклад з Dockerfile CMD), виконуємо їх.
# Якщо аргументів немає — напряму запускаємо AWS Lambda RIC з вашим хендлером.
if [ $# -gt 0 ]; then
    exec "$@"
else
    exec /usr/local/bin/python -m awslambdaric app.ai.agenda_lambda.handler
fi
