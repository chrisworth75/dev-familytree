#!/usr/bin/env python3
"""
Migration to add ancestral line tracking using ahnentafel numbering.

Ahnentafel numbering:
  1 = self
  2 = father, 3 = mother
  4 = father's father, 5 = father's mother, 6 = mother's father, 7 = mother's mother
  etc. (father = n*2, mother = n*2+1)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "genealogy.db"


def ahnentafel_to_path(n: int) -> str:
    """Convert ahnentafel number to human readable path like "Dad's Dad's Mum"."""
    if n == 1:
        return "Me"

    path_parts = []
    current = n

    while current > 1:
        if current % 2 == 0:
            path_parts.append("Dad")
        else:
            path_parts.append("Mum")
        current //= 2

    # Reverse to get from me outward
    path_parts.reverse()

    # Build possessive path
    if len(path_parts) == 1:
        return path_parts[0]

    result = path_parts[0]
    for part in path_parts[1:]:
        result += "'s " + part

    return result


def get_generation(n: int) -> int:
    """Get generation number from ahnentafel (1=self=gen 0, 2-3=parents=gen 1, etc)."""
    if n < 1:
        return -1
    gen = 0
    while n > 1:
        n //= 2
        gen += 1
    return gen


def migrate():
    """Run the migration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating ancestors table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ancestor (
            ahnentafel INTEGER PRIMARY KEY,
            name TEXT,
            birth_year INTEGER,
            death_year INTEGER,
            birth_place TEXT,
            death_place TEXT,
            known BOOLEAN DEFAULT 0,
            path_description TEXT
        )
    """)

    print("Creating cluster table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cluster (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assigned_ahnentafel INTEGER REFERENCES ancestor(ahnentafel),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("Creating match_ancestor table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_ancestor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER REFERENCES dna_match(id),
            ahnentafel INTEGER REFERENCES ancestor(ahnentafel),
            confidence TEXT CHECK(confidence IN ('confirmed', 'probable', 'possible')),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add cluster_id to dna_match if not exists
    print("Adding cluster_id to dna_match table...")
    try:
        cursor.execute("ALTER TABLE dna_match ADD COLUMN cluster_id INTEGER REFERENCES cluster(id)")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  cluster_id column already exists")
        else:
            raise

    # Pre-populate ancestors 1-63 (6 generations)
    print("Pre-populating ancestors 1-63...")
    for n in range(1, 64):
        path = ahnentafel_to_path(n)
        cursor.execute("""
            INSERT OR IGNORE INTO ancestor (ahnentafel, known, path_description)
            VALUES (?, 0, ?)
        """, (n, path))

    # Create view for matches with ancestral line info
    print("Creating match_ancestry_view...")
    cursor.execute("DROP VIEW IF EXISTS match_ancestry_view")
    cursor.execute("""
        CREATE VIEW match_ancestry_view AS
        SELECT
            dm.id as match_id,
            dm.name as match_name,
            dm.shared_cm,
            dm.relationship_range,
            c.id as cluster_id,
            c.description as cluster_description,
            a.ahnentafel,
            a.path_description as ancestral_line,
            a.name as ancestor_name,
            ma.confidence,
            ma.notes
        FROM dna_match dm
        LEFT JOIN cluster c ON dm.cluster_id = c.id
        LEFT JOIN match_ancestor ma ON ma.match_id = dm.id
        LEFT JOIN ancestor a ON ma.ahnentafel = a.ahnentafel
    """)

    conn.commit()
    conn.close()

    print("\nMigration complete!")
    print("\nAhnentafel examples:")
    for n in [1, 2, 3, 4, 5, 6, 7, 8, 18, 32, 63]:
        print(f"  {n:3d} = {ahnentafel_to_path(n)} (generation {get_generation(n)})")


if __name__ == "__main__":
    migrate()
