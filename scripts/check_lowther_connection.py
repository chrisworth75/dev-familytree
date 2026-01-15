#!/usr/bin/env python3
"""
Check DNA matches for potential Lowther connections.

This script:
1. Extracts all surnames from the Lowther tree
2. Checks DNA match names against Lowther surnames
3. Imports match trees and searches for Lowther surnames
4. Flags cluster 17 matches (unknown father line) for special attention

Usage:
    python scripts/check_lowther_connection.py                    # Check all matches
    python scripts/check_lowther_connection.py --cluster 17       # Check cluster 17 only
    python scripts/check_lowther_connection.py --import-trees     # Import and search match trees
    python scripts/check_lowther_connection.py --match "John Doe" # Check specific match
"""

import sqlite3
import argparse
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
LOWTHER_TREE_ID = 169  # Local tree ID for Lowther tree

# Key Lowther-connected surnames (distinctive ones, not common names)
KEY_SURNAMES = [
    'Lowther', 'Lonsdale', 'Harrington', 'Eyre', 'Westenra', 'Sherard',
    'Monckton', 'Molesworth', 'Palgrave', 'Boucher', 'Carey', 'Rodney',
    'Zouch', 'Feetham', 'Fountayne', 'Whichcote', 'Stanhow'
]


def get_lowther_surnames(cursor):
    """Extract all surnames from Lowther tree."""
    cursor.execute("""
        SELECT DISTINCT TRIM(SUBSTR(name, INSTR(name || ' ', ' ') + 1)) as surname
        FROM person
        WHERE tree_id = ?
          AND name IS NOT NULL
          AND LENGTH(TRIM(SUBSTR(name, INSTR(name || ' ', ' ') + 1))) >= 4
    """, (LOWTHER_TREE_ID,))

    # Filter out common first names that might appear as "surnames"
    common_names = {'Henry', 'John', 'William', 'Mary', 'James', 'Thomas', 'Ann',
                    'Elizabeth', 'George', 'Robert', 'Jane', 'Sarah', 'Margaret',
                    'Edward', 'Charles', 'Richard', 'Anne', 'Catherine', 'Frances'}

    surnames = set()
    for row in cursor.fetchall():
        surname = row[0]
        if surname and surname not in common_names:
            surnames.add(surname)

    return surnames


def check_match_surname(cursor, match_name, lowther_surnames):
    """Check if a match's surname appears in the Lowther tree."""
    matches = []
    for surname in lowther_surnames:
        if surname.lower() in match_name.lower():
            matches.append(surname)
    return matches


def search_match_tree(cursor, tree_id, lowther_surnames):
    """Search a match's tree for Lowther surnames."""
    if not tree_id:
        return []

    # Get local tree ID
    cursor.execute("SELECT id FROM tree WHERE ancestry_tree_id = ?", (str(tree_id),))
    row = cursor.fetchone()
    if not row:
        return []

    local_tree_id = row[0]

    found = []
    for surname in lowther_surnames:
        cursor.execute("""
            SELECT name, birth_year_estimate
            FROM person
            WHERE tree_id = ? AND name LIKE ?
            LIMIT 5
        """, (local_tree_id, f'%{surname}%'))

        for person_row in cursor.fetchall():
            found.append({
                'surname': surname,
                'person': person_row[0],
                'birth_year': person_row[1]
            })

    return found


def check_all_matches(cursor, lowther_surnames, cluster_id=None, min_cm=10):
    """Check all DNA matches for Lowther connections."""

    query = """
        SELECT id, name, shared_cm, cluster_id, has_tree, tree_size, linked_tree_id,
               predicted_relationship
        FROM dna_match
        WHERE shared_cm >= ?
    """
    params = [min_cm]

    if cluster_id:
        query += " AND cluster_id = ?"
        params.append(cluster_id)

    query += " ORDER BY shared_cm DESC"

    cursor.execute(query, params)
    matches = cursor.fetchall()

    results = {
        'surname_matches': [],
        'tree_matches': [],
        'cluster17_priority': []
    }

    for match in matches:
        match_id, name, shared_cm, clust, has_tree, tree_size, linked_tree_id, relationship = match

        # Check surname
        surname_hits = check_match_surname(cursor, name, lowther_surnames)
        if surname_hits:
            results['surname_matches'].append({
                'name': name,
                'shared_cm': shared_cm,
                'surnames': surname_hits,
                'cluster': clust,
                'has_tree': has_tree
            })

        # Check tree if available
        if linked_tree_id:
            tree_hits = search_match_tree(cursor, linked_tree_id, KEY_SURNAMES)
            if tree_hits:
                results['tree_matches'].append({
                    'name': name,
                    'shared_cm': shared_cm,
                    'tree_id': linked_tree_id,
                    'found_in_tree': tree_hits[:10],  # Limit to 10
                    'cluster': clust
                })

        # Flag cluster 17 matches with trees
        if clust == 17 and has_tree and tree_size and tree_size > 50:
            results['cluster17_priority'].append({
                'name': name,
                'shared_cm': shared_cm,
                'tree_size': tree_size,
                'linked_tree_id': linked_tree_id
            })

    return results


def print_results(results):
    """Print results in a readable format."""

    print("\n" + "=" * 70)
    print("LOWTHER CONNECTION CHECK RESULTS")
    print("=" * 70)

    # Surname matches
    print(f"\n## DNA MATCHES WITH LOWTHER TREE SURNAMES ({len(results['surname_matches'])})")
    print("-" * 50)
    if results['surname_matches']:
        for m in sorted(results['surname_matches'], key=lambda x: x['shared_cm'], reverse=True)[:20]:
            cluster_str = f" [Cluster {m['cluster']}]" if m['cluster'] else ""
            tree_str = " (has tree)" if m['has_tree'] else ""
            print(f"  {m['name']}: {m['shared_cm']} cM - {', '.join(m['surnames'])}{cluster_str}{tree_str}")
    else:
        print("  None found")

    # Tree matches
    print(f"\n## MATCH TREES CONTAINING LOWTHER SURNAMES ({len(results['tree_matches'])})")
    print("-" * 50)
    if results['tree_matches']:
        for m in sorted(results['tree_matches'], key=lambda x: x['shared_cm'], reverse=True)[:15]:
            cluster_str = f" [Cluster {m['cluster']}]" if m['cluster'] else ""
            print(f"\n  {m['name']}: {m['shared_cm']} cM{cluster_str}")
            print(f"    Tree {m['tree_id']} contains:")
            for hit in m['found_in_tree'][:5]:
                year = f" ({hit['birth_year']})" if hit['birth_year'] else ""
                print(f"      - {hit['person']}{year} [{hit['surname']}]")
    else:
        print("  None found (try --import-trees to import more match trees)")

    # Cluster 17 priority
    print(f"\n## CLUSTER 17 MATCHES WITH TREES TO INVESTIGATE ({len(results['cluster17_priority'])})")
    print("-" * 50)
    print("  These are matches through Henry Wrathall's unknown father")
    print("  If Lowther claim is true, their trees might contain Lowthers")
    if results['cluster17_priority']:
        for m in sorted(results['cluster17_priority'], key=lambda x: x['shared_cm'], reverse=True)[:15]:
            imported = "✓" if m['linked_tree_id'] else "not imported"
            print(f"  {m['name']}: {m['shared_cm']} cM, tree size: {m['tree_size']} [{imported}]")
    else:
        print("  None with trees > 50 people")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Check DNA matches for Lowther connections")
    parser.add_argument('--cluster', type=int, help="Check specific cluster only (e.g., 17)")
    parser.add_argument('--min-cm', type=float, default=10, help="Minimum cM to check (default: 10)")
    parser.add_argument('--match', type=str, help="Check specific match by name")
    parser.add_argument('--import-trees', action='store_true', help="Import cluster 17 trees and search")
    parser.add_argument('--key-only', action='store_true', help="Only check key Lowther surnames")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get Lowther surnames
    if args.key_only:
        lowther_surnames = set(KEY_SURNAMES)
    else:
        lowther_surnames = get_lowther_surnames(cursor)

    print(f"Loaded {len(lowther_surnames)} surnames from Lowther tree")

    if args.match:
        # Check specific match
        surname_hits = check_match_surname(cursor, args.match, lowther_surnames)
        if surname_hits:
            print(f"\n'{args.match}' matches Lowther surnames: {', '.join(surname_hits)}")
        else:
            print(f"\n'{args.match}' does not match any Lowther surnames")

        # Check if they have a tree
        cursor.execute("""
            SELECT linked_tree_id, tree_size, cluster_id, shared_cm
            FROM dna_match WHERE name LIKE ?
        """, (f'%{args.match}%',))
        row = cursor.fetchone()
        if row:
            tree_id, tree_size, cluster, cm = row
            print(f"  Shared DNA: {cm} cM")
            print(f"  Cluster: {cluster}")
            if tree_id:
                print(f"  Tree ID: {tree_id} ({tree_size} people)")
                tree_hits = search_match_tree(cursor, tree_id, KEY_SURNAMES)
                if tree_hits:
                    print(f"  Lowther surnames found in their tree:")
                    for hit in tree_hits[:10]:
                        print(f"    - {hit['person']} [{hit['surname']}]")
    else:
        # Check all matches
        results = check_all_matches(cursor, lowther_surnames,
                                    cluster_id=args.cluster,
                                    min_cm=args.min_cm)
        print_results(results)

        # Summary stats
        print("\nQUICK STATS:")
        cursor.execute("SELECT COUNT(*) FROM dna_match WHERE shared_cm >= ?", (args.min_cm,))
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dna_match WHERE cluster_id = 17")
        cluster17 = cursor.fetchone()[0]
        print(f"  Total matches >= {args.min_cm} cM: {total}")
        print(f"  Cluster 17 matches (unknown father): {cluster17}")
        print(f"  Surname matches found: {len(results['surname_matches'])}")
        print(f"  Tree matches found: {len(results['tree_matches'])}")

    conn.close()


if __name__ == "__main__":
    main()
