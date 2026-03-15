#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./load_canonicalized_postgres.sh [db_name]
#
# Optional environment variables:
#   PGHOST, PGPORT, PGUSER, PGPASSWORD

DB_NAME="${1:-university_conferences}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_SQL="${SCRIPT_DIR}/create_schema_for_canonicalized_data.sql"
DATA_SQL="${SCRIPT_DIR}/conference_data_canonicalized.sql"

if ! command -v psql >/dev/null 2>&1; then
  echo "Error: psql is not installed or not in PATH." >&2
  exit 1
fi

if ! command -v createdb >/dev/null 2>&1; then
  echo "Error: createdb is not installed or not in PATH." >&2
  exit 1
fi

if [[ ! -f "${SCHEMA_SQL}" ]]; then
  echo "Error: schema file not found: ${SCHEMA_SQL}" >&2
  exit 1
fi

if [[ ! -f "${DATA_SQL}" ]]; then
  echo "Error: data file not found: ${DATA_SQL}" >&2
  exit 1
fi

echo "Checking if database '${DB_NAME}' exists..."
if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  echo "Creating database '${DB_NAME}'..."
  createdb "${DB_NAME}"
else
  echo "Database '${DB_NAME}' already exists."
fi

echo "Applying schema..."
psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "${SCHEMA_SQL}"

echo "Loading canonicalized data (this may take a bit)..."
psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" -f "${DATA_SQL}"

echo "Done. Database '${DB_NAME}' is ready."
