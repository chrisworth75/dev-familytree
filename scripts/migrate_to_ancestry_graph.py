#!/usr/bin/env python3
"""
Migrate DNA data to new ancestry_person/ancestry_match graph schema.

Migrates from:
- PostgreSQL dna_match → ancestry_person (nodes) + ancestry_match (you↔match edges)
- SQLite shared_match → ancestry_match (match↔match edges)
"""

import sqlite3
import psycopg2
import uuid
from datetime import datetime

# Database connections
PG_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'familytree',
    'user': 'familytree',
    'password': 'familytree'
}

SQLITE_PATH = '/Users/chris/dev-familytree/genealogy.db'

# Chris's ancestry_id (the test-taker)
CHRIS_ANCESTRY_ID = 'E756DE6C-0C8D-443B-8793-ADDB6F35FD6A'
CHRIS_PERSON_ID = 1000


def generate_synthetic_id(name):
    """Generate a deterministic synthetic ancestry_id for people without one."""
    # Use UUID5 with a namespace to get deterministic IDs from names
    namespace = uuid.UUID('12345678-1234-5678-1234-567812345678')
    return str(uuid.uuid5(namespace, name.lower())).upper()


def migrate_dna_match_to_ancestry_person(pg_cursor):
    """Migrate existing dna_match records to ancestry_person nodes."""
    print("\n" + "=" * 60)
    print("STEP 1: Migrate dna_match → ancestry_person")
    print("=" * 60)

    # First, insert Chris as a node (the test-taker)
    pg_cursor.execute("""
        INSERT INTO ancestry_person (ancestry_id, name, person_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (ancestry_id) DO NOTHING
    """, (CHRIS_ANCESTRY_ID, 'Chris Worthington', CHRIS_PERSON_ID))

    # Get all matches from dna_match
    pg_cursor.execute("""
        SELECT ancestry_id, name, admin_level, has_tree, tree_size, person_id
        FROM dna_match
        WHERE ancestry_id IS NOT NULL
    """)
    matches = pg_cursor.fetchall()
    print(f"Found {len(matches)} matches in dna_match")

    # Insert into ancestry_person
    inserted = 0
    for ancestry_id, name, admin_level, has_tree, tree_size, person_id in matches:
        try:
            pg_cursor.execute("""
                INSERT INTO ancestry_person (ancestry_id, name, admin_level, has_tree, tree_size, person_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ancestry_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    admin_level = COALESCE(EXCLUDED.admin_level, ancestry_person.admin_level),
                    has_tree = COALESCE(EXCLUDED.has_tree, ancestry_person.has_tree),
                    tree_size = COALESCE(EXCLUDED.tree_size, ancestry_person.tree_size),
                    person_id = COALESCE(EXCLUDED.person_id, ancestry_person.person_id),
                    updated_at = NOW()
            """, (ancestry_id, name, admin_level, has_tree, tree_size, person_id))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {name}: {e}")

    print(f"Inserted/updated {inserted} ancestry_person records")
    return inserted


def create_you_to_match_edges(pg_cursor):
    """Create edges from Chris to each of his DNA matches."""
    print("\n" + "=" * 60)
    print("STEP 2: Create you↔match edges in ancestry_match")
    print("=" * 60)

    # Get all matches with their shared_cm
    pg_cursor.execute("""
        SELECT ancestry_id, shared_cm, shared_segments
        FROM dna_match
        WHERE ancestry_id IS NOT NULL
        AND matched_to_person_id = %s
    """, (CHRIS_PERSON_ID,))
    matches = pg_cursor.fetchall()
    print(f"Found {len(matches)} matches to create edges for")

    inserted = 0
    for ancestry_id, shared_cm, shared_segments in matches:
        # Ensure consistent ordering (smaller ID first)
        p1, p2 = sorted([CHRIS_ANCESTRY_ID, ancestry_id])

        try:
            pg_cursor.execute("""
                INSERT INTO ancestry_match (person1_id, person2_id, shared_cm, shared_segments)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (person1_id, person2_id) DO UPDATE SET
                    shared_cm = COALESCE(EXCLUDED.shared_cm, ancestry_match.shared_cm),
                    shared_segments = COALESCE(EXCLUDED.shared_segments, ancestry_match.shared_segments)
            """, (p1, p2, shared_cm, shared_segments))
            inserted += 1
        except Exception as e:
            print(f"  Error creating edge for {ancestry_id}: {e}")

    print(f"Inserted/updated {inserted} you↔match edges")
    return inserted


def build_sqlite_id_map(sqlite_cursor):
    """Build a mapping from SQLite dna_match.id to ancestry_id."""
    print("\n" + "=" * 60)
    print("STEP 3: Build SQLite ID mapping")
    print("=" * 60)

    sqlite_cursor.execute("""
        SELECT id, ancestry_id, name FROM dna_match WHERE ancestry_id IS NOT NULL
    """)
    rows = sqlite_cursor.fetchall()

    id_to_ancestry = {row[0]: row[1] for row in rows}
    name_to_ancestry = {row[2]: row[1] for row in rows}

    print(f"Built mapping for {len(id_to_ancestry)} SQLite dna_match records")
    print(f"Built name mapping for {len(name_to_ancestry)} unique names")

    return id_to_ancestry, name_to_ancestry


def migrate_shared_matches(sqlite_cursor, pg_cursor, id_to_ancestry, name_to_ancestry):
    """Migrate shared_match edges from SQLite to PostgreSQL."""
    print("\n" + "=" * 60)
    print("STEP 4: Migrate shared_match → ancestry_match edges")
    print("=" * 60)

    # Get all shared_match records
    sqlite_cursor.execute("""
        SELECT match1_id, match2_id, match2_name, match1_to_match2_cm
        FROM shared_match
    """)
    shared_matches = sqlite_cursor.fetchall()
    print(f"Found {len(shared_matches)} shared_match records")

    # Track people we need to create nodes for
    missing_people = {}  # name -> synthetic_id
    edges_created = 0
    edges_skipped = 0

    for match1_id, match2_id, match2_name, shared_cm in shared_matches:
        # Look up ancestry_id for match1
        ancestry1 = id_to_ancestry.get(match1_id)
        if not ancestry1:
            edges_skipped += 1
            continue

        # Look up ancestry_id for match2
        ancestry2 = None
        if match2_id and match2_id in id_to_ancestry:
            ancestry2 = id_to_ancestry[match2_id]
        elif match2_name in name_to_ancestry:
            ancestry2 = name_to_ancestry[match2_name]

        # If still no ancestry_id, create synthetic one
        if not ancestry2:
            if match2_name not in missing_people:
                synthetic_id = generate_synthetic_id(match2_name)
                missing_people[match2_name] = synthetic_id
            ancestry2 = missing_people[match2_name]

        # Ensure consistent ordering
        p1, p2 = sorted([ancestry1, ancestry2])

        try:
            pg_cursor.execute("""
                INSERT INTO ancestry_match (person1_id, person2_id, shared_cm)
                VALUES (%s, %s, %s)
                ON CONFLICT (person1_id, person2_id) DO UPDATE SET
                    shared_cm = GREATEST(ancestry_match.shared_cm, EXCLUDED.shared_cm)
            """, (p1, p2, shared_cm))
            edges_created += 1
        except psycopg2.errors.ForeignKeyViolation:
            # Person doesn't exist yet - we'll create them next
            pg_cursor.connection.rollback()
            if ancestry2 not in [v for v in missing_people.values()]:
                # Add to missing people for later creation
                missing_people[match2_name] = ancestry2
            edges_skipped += 1
        except Exception as e:
            print(f"  Error creating edge {ancestry1} ↔ {ancestry2}: {e}")
            pg_cursor.connection.rollback()
            edges_skipped += 1

    print(f"Created {edges_created} edges, skipped {edges_skipped}")
    print(f"Found {len(missing_people)} people needing node creation")

    return missing_people, edges_created


def create_missing_person_nodes(pg_cursor, missing_people):
    """Create ancestry_person nodes for people only found in shared_match."""
    print("\n" + "=" * 60)
    print("STEP 5: Create missing ancestry_person nodes")
    print("=" * 60)

    if not missing_people:
        print("No missing people to create")
        return 0

    created = 0
    for name, ancestry_id in missing_people.items():
        try:
            pg_cursor.execute("""
                INSERT INTO ancestry_person (ancestry_id, name)
                VALUES (%s, %s)
                ON CONFLICT (ancestry_id) DO NOTHING
            """, (ancestry_id, name))
            created += 1
        except Exception as e:
            print(f"  Error creating node for {name}: {e}")

    print(f"Created {created} missing person nodes")
    return created


def retry_failed_edges(sqlite_cursor, pg_cursor, id_to_ancestry, name_to_ancestry, missing_people):
    """Retry creating edges after missing person nodes are created."""
    print("\n" + "=" * 60)
    print("STEP 6: Retry failed edges")
    print("=" * 60)

    # Get all shared_match records again
    sqlite_cursor.execute("""
        SELECT match1_id, match2_id, match2_name, match1_to_match2_cm
        FROM shared_match
    """)
    shared_matches = sqlite_cursor.fetchall()

    edges_created = 0

    for match1_id, match2_id, match2_name, shared_cm in shared_matches:
        ancestry1 = id_to_ancestry.get(match1_id)
        if not ancestry1:
            continue

        ancestry2 = None
        if match2_id and match2_id in id_to_ancestry:
            ancestry2 = id_to_ancestry[match2_id]
        elif match2_name in name_to_ancestry:
            ancestry2 = name_to_ancestry[match2_name]
        elif match2_name in missing_people:
            ancestry2 = missing_people[match2_name]

        if not ancestry2:
            continue

        p1, p2 = sorted([ancestry1, ancestry2])

        try:
            pg_cursor.execute("""
                INSERT INTO ancestry_match (person1_id, person2_id, shared_cm)
                VALUES (%s, %s, %s)
                ON CONFLICT (person1_id, person2_id) DO UPDATE SET
                    shared_cm = GREATEST(ancestry_match.shared_cm, EXCLUDED.shared_cm)
            """, (p1, p2, shared_cm))
            edges_created += 1
        except Exception as e:
            pass  # Already exists or still has issues

    print(f"Created {edges_created} additional edges on retry")
    return edges_created


def fix_chris_edge_weights(sqlite_cursor, pg_cursor):
    """Fix Chris's edge weights using correct cM values from SQLite.

    The shared_match import can overwrite Chris↔match edges with incorrect
    match1↔match2 cM values. This function restores the correct values.
    """
    print("\n" + "=" * 60)
    print("STEP 7: Fix Chris edge weights")
    print("=" * 60)

    # Get correct cM values from SQLite dna_match
    sqlite_cursor.execute("SELECT ancestry_id, shared_cm FROM dna_match WHERE ancestry_id IS NOT NULL")
    correct_cm = {row[0]: row[1] for row in sqlite_cursor.fetchall()}
    print(f"Loaded {len(correct_cm)} correct cM values from SQLite")

    updated = 0
    for ancestry_id, cm in correct_cm.items():
        if cm is None:
            continue

        # Ensure consistent ordering (smaller ID first)
        p1, p2 = sorted([CHRIS_ANCESTRY_ID, ancestry_id])

        pg_cursor.execute("""
            UPDATE ancestry_match
            SET shared_cm = %s
            WHERE person1_id = %s AND person2_id = %s
        """, (cm, p1, p2))
        if pg_cursor.rowcount > 0:
            updated += 1

    print(f"Updated {updated} Chris edges with correct cM values")
    return updated


def verify_migration(pg_cursor):
    """Verify the migration results."""
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    pg_cursor.execute("SELECT COUNT(*) FROM ancestry_person")
    person_count = pg_cursor.fetchone()[0]

    pg_cursor.execute("SELECT COUNT(*) FROM ancestry_match")
    match_count = pg_cursor.fetchone()[0]

    pg_cursor.execute("SELECT COUNT(*) FROM dna_match")
    old_match_count = pg_cursor.fetchone()[0]

    print(f"ancestry_person nodes: {person_count}")
    print(f"ancestry_match edges:  {match_count}")
    print(f"Original dna_match:    {old_match_count}")

    # Show sample edges
    print("\nSample edges (top 10 by shared_cm):")
    pg_cursor.execute("""
        SELECT ap1.name, ap2.name, am.shared_cm
        FROM ancestry_match am
        JOIN ancestry_person ap1 ON ap1.ancestry_id = am.person1_id
        JOIN ancestry_person ap2 ON ap2.ancestry_id = am.person2_id
        ORDER BY am.shared_cm DESC
        LIMIT 10
    """)
    for name1, name2, cm in pg_cursor.fetchall():
        print(f"  {name1[:25]:<25} ↔ {name2[:25]:<25} : {cm:.1f} cM")

    return person_count, match_count


def main():
    print("=" * 60)
    print("DNA GRAPH MIGRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")

    # Connect to databases
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cursor = pg_conn.cursor()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    try:
        # Step 1: Migrate dna_match → ancestry_person
        migrate_dna_match_to_ancestry_person(pg_cursor)
        pg_conn.commit()

        # Step 2: Create you↔match edges
        create_you_to_match_edges(pg_cursor)
        pg_conn.commit()

        # Step 3: Build SQLite ID mapping
        id_to_ancestry, name_to_ancestry = build_sqlite_id_map(sqlite_cursor)

        # Step 4: Migrate shared_match edges (first pass)
        missing_people, _ = migrate_shared_matches(sqlite_cursor, pg_cursor, id_to_ancestry, name_to_ancestry)
        pg_conn.commit()

        # Step 5: Create missing person nodes
        create_missing_person_nodes(pg_cursor, missing_people)
        pg_conn.commit()

        # Step 6: Retry failed edges
        retry_failed_edges(sqlite_cursor, pg_cursor, id_to_ancestry, name_to_ancestry, missing_people)
        pg_conn.commit()

        # Step 7: Fix Chris edge weights (shared_match import can overwrite with wrong values)
        fix_chris_edge_weights(sqlite_cursor, pg_cursor)
        pg_conn.commit()

        # Verify
        verify_migration(pg_cursor)

        print(f"\nCompleted at: {datetime.now()}")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        pg_conn.rollback()
        raise
    finally:
        pg_cursor.close()
        pg_conn.close()
        sqlite_cursor.close()
        sqlite_conn.close()


if __name__ == '__main__':
    main()
