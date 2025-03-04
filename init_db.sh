#!/bin/sh
set -e

DB_NAME=${DB_NAME:-"hockey_blast_sample"}
SUPERUSER_NAME="boss"
SUPERUSER_PASSWORD="boss"

echo "PostgreSQL - Creating roles and restoring database $DB_NAME"

psql --username=postgres --command="CREATE ROLE $SUPERUSER_NAME WITH SUPERUSER LOGIN PASSWORD '$SUPERUSER_PASSWORD'"
psql --username=postgres --command="CREATE ROLE frontend_user WITH SUPERUSER LOGIN PASSWORD 'hockey-blast'"
psql --username=postgres --command="SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();"
psql --username=postgres --command="DROP DATABASE IF EXISTS $DB_NAME"
psql --username=postgres --command="CREATE DATABASE $DB_NAME OWNER $SUPERUSER_NAME"

cd /sample_db_restore/hockey_blast_common_lib
COMPRESSED_DUMP_FILE="hockey_blast_sample_backup.sql.gz"

# Set environment variables for pg_restore
export PGUSER=$SUPERUSER_NAME
export PGPASSWORD=$SUPERUSER_PASSWORD

# Restore the database from the dump file with --no-acl and --no-owner options
gunzip -c $COMPRESSED_DUMP_FILE | pg_restore --dbname=$DB_NAME --format=custom --no-acl --no-owner

# Unset environment variables
unset PGUSER
unset PGPASSWORD

# Create the frontend_user if it does not exist
psql --username=postgres --dbname=$DB_NAME --command="DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'frontend_user') THEN CREATE ROLE frontend_user LOGIN PASSWORD 'hockey-blast'; END IF; END \$\$;"

# Grant necessary permissions to the frontend_user
psql --username=postgres --dbname=$DB_NAME --command="GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO frontend_user"

echo "Database restore completed: $DB_NAME"


