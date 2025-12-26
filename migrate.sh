#!/bin/bash
# migrate.sh - Apply pending migrations
# Usage: ./migrate.sh [database_path]

set -e

DB="${1:-genealogy.db}"
MIGRATIONS_DIR="$(dirname "$0")/migrations"

echo "Database: $DB"
echo "Migrations: $MIGRATIONS_DIR"
echo ""

# Create db if it doesn't exist
touch "$DB"

# Ensure schema_migrations table exists (bootstrap)
sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"

# Get list of applied migrations
applied=$(sqlite3 "$DB" "SELECT version FROM schema_migrations;" 2>/dev/null || echo "")

# Apply each migration in order
for f in "$MIGRATIONS_DIR"/*.sql; do
    if [ ! -f "$f" ]; then
        continue
    fi
    
    version=$(basename "$f")
    
    if echo "$applied" | grep -q "^${version}$"; then
        echo "SKIP: $version (already applied)"
    else
        echo "APPLY: $version"
        sqlite3 "$DB" < "$f"
        sqlite3 "$DB" "INSERT INTO schema_migrations (version) VALUES ('$version');"
    fi
done

echo ""
echo "Done. Current schema version:"
sqlite3 "$DB" "SELECT version, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 1;"
