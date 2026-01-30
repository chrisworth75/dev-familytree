#!/usr/bin/env python3
"""
Recover Ancestry GUIDs from SQLite and add them to PostgreSQL.

The SQLite dna_match table has ancestry_id (GUID) that was not migrated
to PostgreSQL. This script:
1. Adds ancestry_guid column to PostgreSQL person table
2. Matches SQLite records to PostgreSQL person records by name + shared_cm
3. Updates PostgreSQL with the recovered GUIDs

Usage:
    python recover_ancestry_guids.py --dry-run   # Preview changes
    python recover_ancestry_guids.py             # Apply changes
"""

import sqlite3
import psycopg2
import sys
from pathlib import Path

# Configuration
SQLITE_PATH = Path(__file__).parent.parent / "genealogy.db"
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "familytree",
    "user": "familytree",
    "password": "familytree",
}


def get_sqlite_matches(sqlite_conn):
    """Get all DNA matches with ancestry_id from SQLite."""
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT ancestry_id, name, shared_cm
        FROM dna_match
        WHERE ancestry_id IS NOT NULL AND ancestry_id != ''
    """)
    return cursor.fetchall()


def get_pg_match_persons(pg_conn):
    """
    Get all person records that are DNA matches in PostgreSQL.
    DNA match persons are referenced in dna_match.person_2_id (the match)
    where person_1_id is typically the test taker (id=1000).
    """
    cursor = pg_conn.cursor()

    # Get all unique person_2_ids from dna_match (these are the DNA matches)
    # Along with their shared_cm for matching
    # PostgreSQL splits names into first_name + surname, so we need to combine them
    cursor.execute("""
        SELECT DISTINCT
            p.id,
            p.first_name,
            p.surname,
            dm.shared_cm
        FROM person p
        JOIN dna_match dm ON dm.person_2_id = p.id
        WHERE p.first_name IS NOT NULL
    """)

    results = cursor.fetchall()

    # Build lookup dict: (name, shared_cm) -> person_id
    # Handle potential duplicates by storing as list
    lookup = {}
    for person_id, first_name, surname, shared_cm in results:
        # Combine first_name and surname to match SQLite format
        if surname:
            full_name = f"{first_name} {surname}"
        else:
            full_name = first_name

        cm_value = float(shared_cm) if shared_cm else None
        key = (full_name, cm_value)
        if key not in lookup:
            lookup[key] = []
        lookup[key].append(person_id)

        # Also index by first_name only for fallback matching
        key_first_only = (first_name, cm_value)
        if key_first_only not in lookup:
            lookup[key_first_only] = []
        if person_id not in lookup[key_first_only]:
            lookup[key_first_only].append(person_id)

    return lookup


def add_ancestry_guid_column(pg_conn, dry_run=False):
    """Add ancestry_guid column to person table if it doesn't exist."""
    cursor = pg_conn.cursor()

    # Check if column exists
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'person' AND column_name = 'ancestry_guid'
    """)

    if cursor.fetchone():
        print("Column ancestry_guid already exists on person table")
        return True

    if dry_run:
        print("Would add ancestry_guid column to person table")
        return True

    print("Adding ancestry_guid column to person table...")
    cursor.execute("""
        ALTER TABLE person
        ADD COLUMN ancestry_guid VARCHAR(36)
    """)

    # Add index for faster lookups
    cursor.execute("""
        CREATE INDEX idx_person_ancestry_guid
        ON person(ancestry_guid)
        WHERE ancestry_guid IS NOT NULL
    """)

    pg_conn.commit()
    print("Added ancestry_guid column and index")
    return True


def recover_guids(sqlite_conn, pg_conn, dry_run=False):
    """Match SQLite records to PostgreSQL and recover GUIDs."""

    print("\n" + "=" * 60)
    print("RECOVERING ANCESTRY GUIDs")
    print("=" * 60)

    # Get SQLite data
    print("\nReading SQLite dna_match records...")
    sqlite_matches = get_sqlite_matches(sqlite_conn)
    print(f"  Found {len(sqlite_matches)} records with ancestry_id")

    # Get PostgreSQL lookup
    print("\nBuilding PostgreSQL person lookup...")
    pg_lookup = get_pg_match_persons(pg_conn)
    print(f"  Found {len(pg_lookup)} unique (name, shared_cm) combinations")

    # Match and prepare updates
    matched = []
    unmatched = []
    ambiguous = []

    for ancestry_id, name, shared_cm in sqlite_matches:
        # Try exact match on name + shared_cm
        key = (name, float(shared_cm) if shared_cm else None)

        if key in pg_lookup:
            person_ids = list(set(pg_lookup[key]))  # Deduplicate
            if len(person_ids) == 1:
                matched.append((ancestry_id, person_ids[0], name, shared_cm))
            else:
                ambiguous.append((ancestry_id, name, shared_cm, person_ids))
        else:
            # Try matching by name only (in case shared_cm differs slightly)
            name_matches = [
                (k, v) for k, v in pg_lookup.items()
                if k[0] == name
            ]
            if len(name_matches) == 1:
                _, person_ids = name_matches[0]
                person_ids = list(set(person_ids))  # Deduplicate
                if len(person_ids) == 1:
                    matched.append((ancestry_id, person_ids[0], name, shared_cm))
                else:
                    ambiguous.append((ancestry_id, name, shared_cm, person_ids))
            elif len(name_matches) > 1:
                # Multiple matches with same name but different cM - deduplicate person_ids
                all_person_ids = list(set(pid for _, pids in name_matches for pid in pids))
                if len(all_person_ids) == 1:
                    matched.append((ancestry_id, all_person_ids[0], name, shared_cm))
                else:
                    ambiguous.append((ancestry_id, name, shared_cm, all_person_ids))
            else:
                unmatched.append((ancestry_id, name, shared_cm))

    # Report results
    print(f"\nMatching results:")
    print(f"  Matched:   {len(matched)}")
    print(f"  Ambiguous: {len(ambiguous)}")
    print(f"  Unmatched: {len(unmatched)}")

    if ambiguous:
        print(f"\nFirst 5 ambiguous matches:")
        for ancestry_id, name, shared_cm, person_ids in ambiguous[:5]:
            print(f"  {name} ({shared_cm} cM) -> {len(person_ids)} possible persons: {person_ids[:3]}...")

    if unmatched:
        print(f"\nFirst 10 unmatched records:")
        for ancestry_id, name, shared_cm in unmatched[:10]:
            print(f"  {ancestry_id[:8]}... {name} ({shared_cm} cM)")

    # Apply updates
    if dry_run:
        print(f"\n[DRY RUN] Would update {len(matched)} person records with ancestry_guid")
        return len(matched), len(ambiguous), len(unmatched)

    print(f"\nUpdating {len(matched)} person records...")
    cursor = pg_conn.cursor()

    updated = 0
    for ancestry_id, person_id, name, shared_cm in matched:
        cursor.execute("""
            UPDATE person
            SET ancestry_guid = %s
            WHERE id = %s AND ancestry_guid IS NULL
        """, (ancestry_id, person_id))
        if cursor.rowcount > 0:
            updated += 1

    pg_conn.commit()
    print(f"  Updated {updated} records")

    # Verify
    cursor.execute("""
        SELECT COUNT(*) FROM person WHERE ancestry_guid IS NOT NULL
    """)
    total_with_guid = cursor.fetchone()[0]
    print(f"  Total persons with ancestry_guid: {total_with_guid}")

    return len(matched), len(ambiguous), len(unmatched)


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 60)

    # Connect to databases
    print(f"\nConnecting to SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)

    print(f"Connecting to PostgreSQL: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    pg_conn = psycopg2.connect(**PG_CONFIG)

    try:
        # Add column if needed
        add_ancestry_guid_column(pg_conn, dry_run)

        # Recover GUIDs
        matched, ambiguous, unmatched = recover_guids(sqlite_conn, pg_conn, dry_run)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Matched and updated: {matched}")
        print(f"Ambiguous (skipped): {ambiguous}")
        print(f"Unmatched (skipped): {unmatched}")

        if ambiguous > 0 or unmatched > 0:
            print("\nNote: Ambiguous/unmatched records may need manual review.")
            print("These could be due to:")
            print("  - Name changes or corrections in PostgreSQL")
            print("  - Shared cM rounding differences")
            print("  - Records that weren't migrated")

        if dry_run:
            print("\nRun without --dry-run to apply changes.")

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
