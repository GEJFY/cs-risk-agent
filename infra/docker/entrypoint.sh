#!/bin/bash
set -e

echo "=== CS Risk Agent Backend ==="
echo "Environment: ${APP_ENV:-development}"

# DB マイグレーション (PostgreSQL 接続待機)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Waiting for database..."
    for i in $(seq 1 30); do
        if python -c "
import psycopg2
conn = psycopg2.connect('${DATABASE_SYNC_URL:-postgresql://postgres:postgres@db:5432/cs_risk_agent}')
conn.close()
" 2>/dev/null; then
            echo "Database is ready."
            break
        fi
        echo "  Attempt $i/30 - waiting..."
        sleep 2
    done

    echo "Running Alembic migrations..."
    alembic upgrade head || echo "Warning: Migration failed (may already be up to date)"
fi

# デモデータシード (オプション)
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "Seeding demo data into database..."
    python -m cs_risk_agent.scripts.seed_db || echo "Warning: Seed failed (data may already exist)"
fi

echo "Starting uvicorn..."
exec uvicorn cs_risk_agent.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${UVICORN_WORKERS:-2}" \
    --log-level "${LOG_LEVEL:-info}"
