#!/bin/bash
set -e

echo "Starting PostgreSQL initialization script..."

# Wait for PostgreSQL to start
until pg_isready -h 127.0.0.1 -p 5432; do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

echo "PostgreSQL started. Creating roles..."

# Create roles
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE boss WITH SUPERUSER LOGIN PASSWORD 'boss';
    CREATE ROLE frontend_user WITH SUPERUSER LOGIN PASSWORD 'hockey-blast';
EOSQL

echo "Roles created. Restoring the sample database..."

# Restore the sample database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" < /docker-entrypoint-initdb.d/sample_db_backup.sql

echo "Sample database restored."
