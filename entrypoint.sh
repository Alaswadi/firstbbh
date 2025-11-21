#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."

# Wait for PostgreSQL
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

>&2 echo "PostgreSQL is up - continuing"

# Initialize database schema
echo "Initializing database schema..."
python -c "from database import init_db; init_db()"

# Run migration from SQLite if needed
echo "Checking for SQLite migration..."
python -c "from database import migrate_from_sqlite; migrate_from_sqlite()" || echo "No migration needed"

echo "Setup complete - starting application"

# Execute the main command
exec "$@"
