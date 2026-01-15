#!/usr/bin/env python3
"""
Migrate relationships from the relationship table:
1. Parent-child -> mother_id/father_id columns on person table
2. Spouse -> new marriage table
3. Drop relationship table when done
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

FEMALE_NAMES = {
    'mary', 'alice', 'constance', 'blanche', 'evelyn', 'ethel', 'jane',
    'margaret', 'angela', 'janet', 'betty', 'susan', 'ann', 'elizabeth',
    'doris', 'marjorie', 'patricia', 'nina', 'rachel', 'verity', 'kathleen',
    'muriel', 'agnes', 'sarah', 'emma', 'lily', 'rose', 'irene', 'annie',
    'loreen', 'betsy', 'theodora', 'maria', 'ellen', 'elsie', 'grace',
    'rebecca', 'jennifer', 'norah', 'florence', 'miriam', 'harriet',
    'hannah', 'ruth', 'dorothy', 'edith', 'gladys', 'mabel', 'agnes',
    'clara', 'charlotte', 'caroline', 'catherine', 'kate', 'lucy', 'amy',
    'julia', 'laura', 'helen', 'eleanor', 'frances', 'virginia', 'beatrice',
    'lillian', 'hazel', 'mildred', 'gertrude', 'josephine', 'esther',
    'matilda', 'emily'
}

MALE_NAMES = {
    'henry', 'leon', 'donald', 'reginald', 'leslie', 'arthur', 'william',
    'james', 'john', 'thomas', 'george', 'richard', 'david', 'peter', 'stephen',
    'kenneth', 'mervyn', 'albert', 'samuel', 'edmund', 'louis', 'lupton',
    'sydney', 'oliver', 'andrew', 'timothy', 'harry', 'frank', 'francis',
    'robert', 'edward', 'charles', 'joseph', 'michael', 'christopher', 'chris',
    'daniel', 'matthew', 'mark', 'paul', 'jonathan', 'jonathon', 'bryan', 'brian',
    'gordon', 'hugo', 'zachary', 'joe', 'jack', 'fred', 'frederick', 'walter',
    'alfred', 'ernest', 'herbert', 'harold', 'stanley', 'leonard', 'raymond',
    'norman', 'roy', 'cecil', 'ralph', 'howard', 'douglas', 'roger', 'gerald',
    'lewis', 'levi', 'adam', 'nicholas', 'patrick', 'simon'
}


def guess_sex(forename: str) -> str | None:
    """Guess sex from first name. Returns 'M', 'F', or None if unknown."""
    if not forename:
        return None
    first_name = forename.lower().split()[0]
    if first_name in FEMALE_NAMES:
        return "F"
    if first_name in MALE_NAMES:
        return "M"
    return None


def create_marriage_table(cursor):
    """Create the marriage table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS marriage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id_1 INTEGER NOT NULL REFERENCES person(id),
            person_id_2 INTEGER NOT NULL REFERENCES person(id),
            marriage_date TEXT,
            marriage_place TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(person_id_1, person_id_2)
        )
    """)
    print("Created marriage table")


def migrate_spouses(cursor):
    """Migrate spouse relationships to marriage table."""
    cursor.execute("""
        SELECT person_id_1, person_id_2, source
        FROM relationship
        WHERE relationship_type = 'spouse'
    """)
    spouses = cursor.fetchall()
    print(f"Found {len(spouses)} spouse relationships to migrate")

    migrated = 0
    for person_id_1, person_id_2, source in spouses:
        try:
            cursor.execute("""
                INSERT INTO marriage (person_id_1, person_id_2, source)
                VALUES (?, ?, ?)
            """, (person_id_1, person_id_2, source))
            migrated += 1
        except sqlite3.IntegrityError:
            # Already exists (or reverse exists)
            pass

    print(f"Migrated {migrated} spouse relationships to marriage table")
    return migrated


def migrate_parent_child(cursor):
    """Migrate parent-child relationships to mother_id/father_id columns."""
    # Get all parent-child relationships
    cursor.execute("""
        SELECT r.id, r.person_id_1 as parent_id, r.person_id_2 as child_id,
               p.forename as parent_forename, p.surname as parent_surname
        FROM relationship r
        JOIN person p ON r.person_id_1 = p.id
        WHERE r.relationship_type = 'parent-child'
    """)
    relationships = cursor.fetchall()

    print(f"Found {len(relationships)} parent-child relationships to migrate")

    # Track updates
    mother_updates = 0
    father_updates = 0
    unknown_updates = 0
    conflicts = 0

    for rel_id, parent_id, child_id, parent_forename, parent_surname in relationships:
        sex = guess_sex(parent_forename)

        # Check current state of child record
        cursor.execute("SELECT mother_id, father_id FROM person WHERE id = ?", (child_id,))
        row = cursor.fetchone()
        if not row:
            continue

        current_mother, current_father = row

        if sex == 'F':
            if current_mother is None:
                cursor.execute("UPDATE person SET mother_id = ? WHERE id = ?", (parent_id, child_id))
                mother_updates += 1
            elif current_mother != parent_id:
                print(f"  Conflict: child {child_id} already has mother {current_mother}, can't set to {parent_id} ({parent_forename})")
                conflicts += 1
        elif sex == 'M':
            if current_father is None:
                cursor.execute("UPDATE person SET father_id = ? WHERE id = ?", (parent_id, child_id))
                father_updates += 1
            elif current_father != parent_id:
                print(f"  Conflict: child {child_id} already has father {current_father}, can't set to {parent_id} ({parent_forename})")
                conflicts += 1
        else:
            # Unknown sex - try to infer or skip
            print(f"  Unknown sex for parent: {parent_forename} {parent_surname} (id={parent_id})")
            unknown_updates += 1

    print(f"\nParent-child migration:")
    print(f"  Mothers set: {mother_updates}")
    print(f"  Fathers set: {father_updates}")
    print(f"  Unknown sex (skipped): {unknown_updates}")
    print(f"  Conflicts: {conflicts}")

    return mother_updates, father_updates, unknown_updates


def drop_relationship_table(cursor):
    """Drop the relationship table after migration."""
    cursor.execute("DROP TABLE IF EXISTS relationship")
    print("Dropped relationship table")


def main():
    # Check for --dry-run flag
    dry_run = '--dry-run' in sys.argv

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("RELATIONSHIP TABLE MIGRATION")
    print("=" * 60)

    if dry_run:
        print("DRY RUN MODE - no changes will be made\n")

    # Check if relationship table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='relationship'")
    if not cursor.fetchone():
        print("relationship table does not exist - nothing to migrate")
        conn.close()
        return

    # Step 1: Create marriage table
    print("\n--- Step 1: Create marriage table ---")
    create_marriage_table(cursor)

    # Step 2: Migrate spouse relationships
    print("\n--- Step 2: Migrate spouse relationships ---")
    migrate_spouses(cursor)

    # Step 3: Migrate parent-child relationships
    print("\n--- Step 3: Migrate parent-child relationships ---")
    migrate_parent_child(cursor)

    # Step 4: Drop relationship table
    print("\n--- Step 4: Drop relationship table ---")
    if not dry_run:
        drop_relationship_table(cursor)
    else:
        print("Would drop relationship table (skipped in dry-run mode)")

    # Verify final state
    print("\n--- Final state ---")
    cursor.execute("SELECT COUNT(*) FROM marriage")
    marriage_count = cursor.fetchone()[0]
    print(f"Marriages: {marriage_count}")

    cursor.execute("SELECT COUNT(*) FROM person WHERE mother_id IS NOT NULL")
    with_mother = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM person WHERE father_id IS NOT NULL")
    with_father = cursor.fetchone()[0]
    print(f"People with mother_id: {with_mother}")
    print(f"People with father_id: {with_father}")

    if not dry_run:
        conn.commit()
        print("\nChanges committed.")
    else:
        conn.rollback()
        print("\nDry run - changes rolled back.")

    conn.close()


if __name__ == "__main__":
    main()
