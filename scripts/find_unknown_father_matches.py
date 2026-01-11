#!/usr/bin/env python3
"""
Find DNA matches who likely connect through Henry Wrathall's unknown father (ahnentafel 36).

Logic:
1. Focus on DISTANT matches (20-100 cM) - these are specific to ~1-2 ancestral lines
2. Require TRUE TRIANGULATION - matches must share DNA with each other, not just with you
3. EXCLUDE matches who connect to KNOWN ancestors (Wrathall, Saul, Metcalfe, etc.)
4. Focus on PATERNAL side (since position 36 is paternal)

The "specificity" concept:
- 2000+ cM (siblings): Share DNA from ALL 16 great-great-grandparent positions
- 500-1000 cM (1st cousins): Share from ~8 positions
- 100-200 cM (2nd cousins): Share from ~4 positions
- 20-50 cM (3rd-4th cousins): Share from ~1-2 positions (MOST USEFUL)
"""

import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict
import json

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

# Known ancestor surnames - matches with these in their trees likely connect through known lines
KNOWN_PATERNAL_SURNAMES = [
    'Wrathall', 'Wraithall', 'Rathall',  # Henry's mother Susan's line
    'Metcalfe',  # Mary Alice Metcalfe (Henry's wife)
    'Saul',      # Known paternal line
    'Worthington',  # Known connection
    'Horrocks',  # Bruce Horrocks line (known)
    'Yates',     # Known line
    'Lightfoot', # Known paternal cluster
    'Copland',   # Known connection
]

# Known maternal surnames - definitely NOT the unknown father
KNOWN_MATERNAL_SURNAMES = [
    'Tart', 'Heywood', 'Brown', 'Virgo',
    'Frame', 'Gessler', 'Ganley',  # From the Dec 22 analysis
]


def get_match_info(cursor, match_id):
    """Get full info for a match."""
    cursor.execute("""
        SELECT id, name, shared_cm, match_side, ancestry_id, linked_tree_id
        FROM dna_match WHERE id = ?
    """, (match_id,))
    return cursor.fetchone()


def get_triangulation_data(min_cm=20, max_cm=100, min_shared=15):
    """
    Get matches in the target cM range who triangulate with each other.

    Returns dict of match_id -> {info, triangulates_with: [(other_id, shared_cm)]}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all matches in target range with shared data
    cursor.execute("""
        SELECT dm.id, dm.name, dm.shared_cm, dm.match_side, dm.linked_tree_id
        FROM dna_match dm
        WHERE dm.shared_cm >= ? AND dm.shared_cm <= ?
        AND dm.match_side IN ('paternal', 'both')
        AND EXISTS (SELECT 1 FROM shared_match sm WHERE sm.match1_id = dm.id)
    """, (min_cm, max_cm))

    target_matches = {}
    for row in cursor.fetchall():
        target_matches[row[0]] = {
            'id': row[0],
            'name': row[1],
            'cm': row[2],
            'side': row[3],
            'tree_id': row[4],
            'triangulates_with': [],
            'surnames_in_tree': set(),
        }

    print(f"Found {len(target_matches)} paternal/both matches in {min_cm}-{max_cm} cM range")

    # Find triangulation - which target matches share DNA with each other
    target_ids = list(target_matches.keys())

    cursor.execute("""
        SELECT sm.match1_id, sm.match2_id, sm.match1_to_match2_cm
        FROM shared_match sm
        WHERE sm.match1_id IN ({})
        AND sm.match2_id IN ({})
        AND sm.match1_to_match2_cm >= ?
    """.format(','.join('?' * len(target_ids)), ','.join('?' * len(target_ids))),
    target_ids + target_ids + [min_shared])

    triangulation_edges = []
    for m1, m2, cm in cursor.fetchall():
        if m1 in target_matches and m2 in target_matches:
            target_matches[m1]['triangulates_with'].append((m2, cm))
            triangulation_edges.append((m1, m2, cm))

    print(f"Found {len(triangulation_edges)} triangulation edges (matches sharing >= {min_shared} cM with each other)")

    # Get surnames from linked trees
    for match_id, match_data in target_matches.items():
        if match_data['tree_id']:
            cursor.execute("""
                SELECT DISTINCT
                    CASE
                        WHEN name LIKE '% %' THEN SUBSTR(name, INSTR(name, ' ') + 1)
                        ELSE name
                    END as surname
                FROM person
                WHERE tree_id = (SELECT id FROM tree WHERE ancestry_tree_id = ?)
            """, (match_data['tree_id'],))
            for row in cursor.fetchall():
                if row[0]:
                    match_data['surnames_in_tree'].add(row[0].strip().title())

    conn.close()
    return target_matches, triangulation_edges


def classify_matches(target_matches):
    """
    Classify matches as:
    - KNOWN_PATERNAL: Has known paternal surnames in tree
    - KNOWN_MATERNAL: Has known maternal surnames in tree
    - UNKNOWN: No known surnames - candidate for unknown father
    """
    for match_id, data in target_matches.items():
        surnames = data['surnames_in_tree']

        # Check for known surnames
        has_known_paternal = any(s in surnames for s in KNOWN_PATERNAL_SURNAMES)
        has_known_maternal = any(s in surnames for s in KNOWN_MATERNAL_SURNAMES)

        if has_known_maternal:
            data['classification'] = 'KNOWN_MATERNAL'
        elif has_known_paternal:
            data['classification'] = 'KNOWN_PATERNAL'
        else:
            data['classification'] = 'UNKNOWN'

        # Store which known surnames were found
        data['known_surnames_found'] = [s for s in surnames if s in KNOWN_PATERNAL_SURNAMES + KNOWN_MATERNAL_SURNAMES]


def build_triangulation_groups(target_matches, triangulation_edges, min_group_size=3):
    """
    Build groups of matches who all triangulate with each other.
    Uses connected components in the triangulation graph.
    """
    from collections import deque

    # Build adjacency list
    adj = defaultdict(set)
    for m1, m2, cm in triangulation_edges:
        adj[m1].add(m2)
        adj[m2].add(m1)

    # Find connected components
    visited = set()
    groups = []

    for start in target_matches.keys():
        if start in visited:
            continue
        if start not in adj:
            continue  # No triangulation connections

        # BFS to find component
        component = []
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

        if len(component) >= min_group_size:
            groups.append(component)

    return groups


def analyze_group(group, target_matches, triangulation_edges):
    """Analyze a triangulation group."""
    members = [target_matches[mid] for mid in group]

    # Count classifications
    classifications = defaultdict(int)
    for m in members:
        classifications[m.get('classification', 'UNKNOWN')] += 1

    # Calculate average cM
    avg_cm = sum(m['cm'] for m in members) / len(members)

    # Count triangulation edges within group
    group_set = set(group)
    internal_edges = [(m1, m2, cm) for m1, m2, cm in triangulation_edges
                      if m1 in group_set and m2 in group_set]

    # Density = actual edges / possible edges
    possible_edges = len(group) * (len(group) - 1) / 2
    density = len(internal_edges) / possible_edges if possible_edges > 0 else 0

    # Collect all surnames found
    all_surnames = set()
    for m in members:
        all_surnames.update(m.get('surnames_in_tree', set()))

    return {
        'size': len(group),
        'avg_cm': avg_cm,
        'classifications': dict(classifications),
        'internal_edges': len(internal_edges),
        'density': density,
        'members': members,
        'all_surnames': all_surnames,
    }


def find_unknown_father_candidates(min_cm=20, max_cm=100, min_shared=15, min_group_size=3):
    """Main function to find unknown father candidates."""

    print("=" * 70)
    print("FINDING UNKNOWN FATHER CANDIDATES (Ahnentafel 36)")
    print("=" * 70)
    print(f"\nParameters:")
    print(f"  Match cM range: {min_cm}-{max_cm} cM (distant = specific)")
    print(f"  Min triangulation: {min_shared} cM shared between matches")
    print(f"  Min group size: {min_group_size}")
    print(f"  Side filter: paternal or both")

    # Get triangulation data
    print(f"\n--- Step 1: Get triangulating matches ---")
    target_matches, triangulation_edges = get_triangulation_data(min_cm, max_cm, min_shared)

    # Classify by known surnames
    print(f"\n--- Step 2: Classify by known surnames ---")
    classify_matches(target_matches)

    class_counts = defaultdict(int)
    for m in target_matches.values():
        class_counts[m.get('classification', 'UNKNOWN')] += 1
    print(f"  KNOWN_PATERNAL: {class_counts['KNOWN_PATERNAL']} (connect to Wrathall/Metcalfe/etc)")
    print(f"  KNOWN_MATERNAL: {class_counts['KNOWN_MATERNAL']} (connect to Tart/Heywood/etc)")
    print(f"  UNKNOWN: {class_counts['UNKNOWN']} (candidates for unknown father)")

    # Build triangulation groups
    print(f"\n--- Step 3: Build triangulation groups ---")
    groups = build_triangulation_groups(target_matches, triangulation_edges, min_group_size)
    print(f"  Found {len(groups)} triangulation groups with >= {min_group_size} members")

    # Analyze each group
    print(f"\n--- Step 4: Analyze groups ---")

    unknown_father_groups = []
    known_paternal_groups = []
    known_maternal_groups = []
    mixed_groups = []

    for i, group in enumerate(sorted(groups, key=len, reverse=True)):
        analysis = analyze_group(group, target_matches, triangulation_edges)

        # Classify group
        if analysis['classifications'].get('KNOWN_MATERNAL', 0) > 0:
            known_maternal_groups.append((i, analysis))
        elif analysis['classifications'].get('KNOWN_PATERNAL', 0) > len(group) * 0.5:
            known_paternal_groups.append((i, analysis))
        elif analysis['classifications'].get('UNKNOWN', 0) > len(group) * 0.5:
            unknown_father_groups.append((i, analysis))
        else:
            mixed_groups.append((i, analysis))

    # Report results
    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")

    print(f"\n## UNKNOWN FATHER CANDIDATES ({len(unknown_father_groups)} groups)")
    print("These are paternal matches who triangulate but DON'T connect to known lines:")

    for i, analysis in unknown_father_groups:
        print(f"\n### Group {i+1}: {analysis['size']} members, avg {analysis['avg_cm']:.1f} cM")
        print(f"    Triangulation density: {analysis['density']:.2f} ({analysis['internal_edges']} edges)")
        print(f"    Classifications: {analysis['classifications']}")
        if analysis['all_surnames']:
            print(f"    Surnames in trees: {', '.join(sorted(analysis['all_surnames'])[:20])}")
        print(f"    Members:")
        for m in sorted(analysis['members'], key=lambda x: -x['cm'])[:10]:
            tree_note = f" [tree: {m['tree_id']}]" if m['tree_id'] else " [no tree]"
            known_note = f" KNOWN:{','.join(m['known_surnames_found'])}" if m.get('known_surnames_found') else ""
            print(f"      - {m['name']} ({m['cm']:.1f} cM, {m['side']}){tree_note}{known_note}")

    print(f"\n## KNOWN PATERNAL GROUPS ({len(known_paternal_groups)} groups)")
    print("These connect to known paternal lines (Wrathall, Metcalfe, etc) - EXCLUDED:")

    for i, analysis in known_paternal_groups[:5]:
        print(f"\n### Group {i+1}: {analysis['size']} members, avg {analysis['avg_cm']:.1f} cM")
        print(f"    Classifications: {analysis['classifications']}")
        surnames_found = set()
        for m in analysis['members']:
            surnames_found.update(m.get('known_surnames_found', []))
        print(f"    Known surnames: {', '.join(surnames_found)}")

    print(f"\n## KNOWN MATERNAL GROUPS ({len(known_maternal_groups)} groups)")
    print("These connect to maternal lines - definitely NOT the unknown father:")

    for i, analysis in known_maternal_groups[:5]:
        print(f"\n### Group {i+1}: {analysis['size']} members, avg {analysis['avg_cm']:.1f} cM")
        surnames_found = set()
        for m in analysis['members']:
            surnames_found.update(m.get('known_surnames_found', []))
        print(f"    Known surnames: {', '.join(surnames_found)}")

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    total_unknown_matches = sum(a['size'] for _, a in unknown_father_groups)
    print(f"  Total unknown father candidate matches: {total_unknown_matches}")
    print(f"  In {len(unknown_father_groups)} triangulation groups")
    print(f"\nThese matches are:")
    print(f"  - Paternal or both-sided")
    print(f"  - Distant enough (20-100 cM) to be specific to ~1-2 ancestors")
    print(f"  - Triangulate with each other (share DNA among themselves)")
    print(f"  - Do NOT have known Wrathall/Metcalfe/Saul/etc surnames in their trees")
    print(f"\nNext steps:")
    print(f"  1. Import trees for these matches")
    print(f"  2. Look for common surnames/locations")
    print(f"  3. Search for connections to Westmorland/Cumberland")
    print(f"  4. Look for Lowther or Lonsdale surnames")

    return unknown_father_groups, target_matches


def show_triangulation_detail(target_matches, triangulation_edges, match_names):
    """Show detailed triangulation for specific matches."""

    # Find matches by name
    name_to_id = {m['name']: mid for mid, m in target_matches.items()}

    print(f"\n{'=' * 70}")
    print("TRIANGULATION DETAIL")
    print(f"{'=' * 70}")

    for name in match_names:
        if name not in name_to_id:
            print(f"\n{name}: NOT FOUND in target range")
            continue

        mid = name_to_id[name]
        m = target_matches[mid]

        print(f"\n## {name} ({m['cm']:.1f} cM, {m['side']})")
        print(f"   Classification: {m.get('classification', 'UNKNOWN')}")
        if m['surnames_in_tree']:
            print(f"   Tree surnames: {', '.join(sorted(m['surnames_in_tree'])[:15])}")

        # Find who they triangulate with
        triangulates = m.get('triangulates_with', [])
        if triangulates:
            print(f"   Triangulates with {len(triangulates)} other matches:")
            for other_id, shared_cm in sorted(triangulates, key=lambda x: -x[1])[:10]:
                other = target_matches.get(other_id, {})
                print(f"     - {other.get('name', '?')} ({other.get('cm', 0):.1f} cM): shares {shared_cm:.1f} cM")
        else:
            print(f"   No triangulation found with other target matches")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find unknown father candidates")
    parser.add_argument("--min-cm", type=float, default=20, help="Minimum cM for matches")
    parser.add_argument("--max-cm", type=float, default=100, help="Maximum cM for matches")
    parser.add_argument("--min-shared", type=float, default=15, help="Minimum shared cM for triangulation")
    parser.add_argument("--min-group", type=int, default=3, help="Minimum group size")
    parser.add_argument("--detail", nargs='+', help="Show triangulation detail for specific matches")
    args = parser.parse_args()

    groups, matches = find_unknown_father_candidates(
        min_cm=args.min_cm,
        max_cm=args.max_cm,
        min_shared=args.min_shared,
        min_group_size=args.min_group
    )

    if args.detail:
        show_triangulation_detail(matches, [], args.detail)
