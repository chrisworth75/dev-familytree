#!/bin/bash
# status.sh - Show migration status
# Usage: ./status.sh [database_path]

DB="${1:-genealogy.db}"
MIGRATIONS_DIR="$(dirname "$0")/migrations"

echo "Database: $DB"
echo ""

if [ ! -f "$DB" ]; then
    echo "Database does not exist yet."
    echo "Run ./migrate.sh to create it."
    exit 0
fi

echo "Applied migrations:"
sqlite3 -header -column "$DB" "SELECT version, applied_at FROM schema_migrations ORDER BY version;"

echo ""
echo "Pending migrations:"
applied=$(sqlite3 "$DB" "SELECT version FROM schema_migrations;" 2>/dev/null || echo "")

pending=0
for f in "$MIGRATIONS_DIR"/*.sql; do
    version=$(basename "$f")
    if ! echo "$applied" | grep -q "^${version}$"; then
        echo "  $version"
        pending=$((pending + 1))
    fi
done

if [ $pending -eq 0 ]; then
    echo "  (none)"
fi

echo ""
echo "Record counts:"
sqlite3 "$DB" "SELECT 'person' as tbl, COUNT(*) as count FROM person UNION ALL SELECT 'census_record', COUNT(*) FROM census_record UNION ALL SELECT 'person_census_link', COUNT(*) FROM person_census_link;" 2>/dev/null || echo "  (tables not yet created)"
