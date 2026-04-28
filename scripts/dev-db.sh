#!/usr/bin/env bash
# Start local Postgres container and run Alembic migrations.
# Usage: ./scripts/dev-db.sh
set -euo pipefail

CONTAINER="smarty-pg"
DB_USER="smarty"
DB_PASS="smarty"
DB_NAME="smarty_steps"
PORT="5432"

# Start or reuse existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "Restarting existing container ${CONTAINER}..."
    docker start "${CONTAINER}"
  else
    echo "Container ${CONTAINER} already running."
  fi
else
  echo "Starting fresh postgres:16 container..."
  docker run -d \
    --name "${CONTAINER}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASS}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p "${PORT}:5432" \
    postgres:16
fi

# Wait until postgres is ready
echo "Waiting for Postgres to be ready..."
until docker exec "${CONTAINER}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" -q; do
  sleep 1
done
echo "Postgres is ready."

# Run Alembic migrations
echo "Running migrations..."
uv run alembic upgrade head
echo "Done."
