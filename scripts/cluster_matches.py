#!/usr/bin/env python3
"""
Cluster DNA matches based on shared match data.

Uses graph community detection to identify groups of matches
that share DNA with each other (indicating common ancestors).
"""

import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict

import networkx as nx
import community.community_louvain as community_louvain

DB_PATH = Path(__file__).parent.parent / "genealogy.db"


def build_shared_match_graph(min_cm=15, min_shared_cm=20):
    """
    Build a graph where:
    - Nodes are DNA matches (your matches)
    - Edges connect matches who share DNA with each other
    - Edge weight = cM shared between the two matches
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all matches above threshold with shared data
    cursor.execute("""
        SELECT DISTINCT dm.id, dm.name, dm.shared_cm, dm.match_side
        FROM dna_match dm
        WHERE dm.shared_cm >= ?
        AND EXISTS (SELECT 1 FROM shared_match sm WHERE sm.match1_id = dm.id)
    """, (min_cm,))
    matches = {row[0]: {'name': row[1], 'cm': row[2], 'side': row[3]} for row in cursor.fetchall()}

    print(f"Found {len(matches)} matches with shared data (>= {min_cm} cM)")

    # Build edges from shared match data
    # If match A shares DNA with match B (both are your matches), create an edge
    cursor.execute("""
        SELECT sm.match1_id, sm.match2_id, sm.match1_to_match2_cm
        FROM shared_match sm
        WHERE sm.match2_id IS NOT NULL
        AND sm.match1_to_match2_cm >= ?
        AND sm.match1_id IN (SELECT id FROM dna_match WHERE shared_cm >= ?)
        AND sm.match2_id IN (SELECT id FROM dna_match WHERE shared_cm >= ?)
    """, (min_shared_cm, min_cm, min_cm))

    edges = []
    for match1_id, match2_id, shared_cm in cursor.fetchall():
        if match1_id in matches and match2_id in matches:
            edges.append((match1_id, match2_id, shared_cm))

    conn.close()

    print(f"Found {len(edges)} edges (shared DNA >= {min_shared_cm} cM between matches)")

    # Build graph
    G = nx.Graph()
    for match_id, data in matches.items():
        G.add_node(match_id, **data)

    for m1, m2, cm in edges:
        # Use max if edge already exists (data might have both directions)
        if G.has_edge(m1, m2):
            G[m1][m2]['weight'] = max(G[m1][m2]['weight'], cm)
        else:
            G.add_edge(m1, m2, weight=cm)

    return G, matches


def detect_communities(G, resolution=1.0):
    """Use Louvain algorithm to detect communities."""
    if len(G.edges()) == 0:
        print("No edges in graph - cannot cluster")
        return {}

    # Louvain community detection
    partition = community_louvain.best_partition(G, weight='weight', resolution=resolution)
    return partition


def analyze_clusters(G, partition, matches):
    """Analyze the detected clusters."""
    # Group matches by cluster
    clusters = defaultdict(list)
    for match_id, cluster_id in partition.items():
        clusters[cluster_id].append(match_id)

    print(f"\n{'='*60}")
    print(f"FOUND {len(clusters)} CLUSTERS")
    print(f"{'='*60}")

    results = []

    for cluster_id in sorted(clusters.keys(), key=lambda c: -len(clusters[c])):
        members = clusters[cluster_id]

        # Calculate cluster stats
        sides = defaultdict(int)
        total_cm = 0
        for mid in members:
            if mid in matches:
                sides[matches[mid]['side']] += 1
                total_cm += matches[mid]['cm']

        avg_cm = total_cm / len(members) if members else 0

        # Determine dominant side
        dominant_side = max(sides.keys(), key=lambda s: sides[s]) if sides else 'unknown'

        # Get top members by cM
        top_members = sorted(members, key=lambda m: -matches.get(m, {}).get('cm', 0))[:10]

        results.append({
            'cluster_id': cluster_id,
            'size': len(members),
            'avg_cm': avg_cm,
            'sides': dict(sides),
            'dominant_side': dominant_side,
            'members': members,
            'top_members': top_members
        })

        # Print summary
        print(f"\n--- Cluster {cluster_id} ({len(members)} members, avg {avg_cm:.1f} cM) ---")
        print(f"    Sides: {dict(sides)}")
        print(f"    Top matches:")
        for mid in top_members[:5]:
            m = matches.get(mid, {})
            print(f"      - {m.get('name', '?')} ({m.get('cm', 0):.1f} cM, {m.get('side', '?')})")

    return results


def save_clusters_to_db(results, prefix="auto"):
    """Save new cluster assignments to database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create new clusters
    for r in results:
        cluster_num = r['cluster_id']
        size = r['size']
        dominant = r['dominant_side']

        # Insert cluster definition
        desc = f"{prefix}_cluster_{cluster_num} ({size} members, {dominant})"
        cursor.execute("""
            INSERT INTO cluster (description) VALUES (?)
        """, (desc,))
        new_cluster_id = cursor.lastrowid

        # Update matches with new cluster
        for match_id in r['members']:
            cursor.execute("""
                UPDATE dna_match SET cluster_id = ? WHERE id = ?
            """, (new_cluster_id, match_id))

        print(f"Saved cluster {new_cluster_id}: {desc}")

    conn.commit()
    conn.close()


def analyze_existing_cluster(cluster_id):
    """Analyze an existing cluster's shared match network."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get cluster members
    cursor.execute("""
        SELECT id, name, shared_cm, match_side
        FROM dna_match
        WHERE cluster_id = ?
        ORDER BY shared_cm DESC
    """, (cluster_id,))
    members = cursor.fetchall()

    print(f"\n{'='*60}")
    print(f"ANALYZING CLUSTER {cluster_id}")
    print(f"{'='*60}")
    print(f"Members: {len(members)}")

    # Check shared connections between members
    member_ids = [m[0] for m in members]

    # Build connection matrix
    connections = defaultdict(set)
    for mid in member_ids:
        cursor.execute("""
            SELECT match2_name, match1_to_match2_cm
            FROM shared_match
            WHERE match1_id = ? AND match1_to_match2_cm > 0
        """, (mid,))
        for name, cm in cursor.fetchall():
            connections[mid].add(name)

    # Find who shares with whom
    print(f"\nShared match connections within cluster:")

    member_names = {m[0]: m[1] for m in members}
    connection_counts = []

    for mid, name, cm, side in members[:20]:
        # Count how many other cluster members this person shares matches with
        shared_names = connections.get(mid, set())
        shared_with_cluster = sum(1 for other_id, other_name in member_names.items()
                                  if other_id != mid and other_name in shared_names)
        connection_counts.append((name, cm, side, shared_with_cluster, len(shared_names)))

    print(f"\n{'Name':<25} {'cM':>8} {'Side':<10} {'In-cluster':>12} {'Total shared':>12}")
    print("-" * 70)
    for name, cm, side, in_cluster, total in sorted(connection_counts, key=lambda x: -x[3]):
        print(f"{name[:25]:<25} {cm:>8.1f} {side or 'unknown':<10} {in_cluster:>12} {total:>12}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Cluster DNA matches")
    parser.add_argument("--min-cm", type=float, default=15, help="Minimum cM for matches to include")
    parser.add_argument("--min-shared", type=float, default=20, help="Minimum shared cM between matches for edge")
    parser.add_argument("--resolution", type=float, default=1.0, help="Louvain resolution (higher = more clusters)")
    parser.add_argument("--save", action="store_true", help="Save clusters to database")
    parser.add_argument("--analyze-cluster", type=int, help="Analyze existing cluster ID")
    args = parser.parse_args()

    if args.analyze_cluster:
        analyze_existing_cluster(args.analyze_cluster)
        return

    print(f"Building shared match graph...")
    G, matches = build_shared_match_graph(min_cm=args.min_cm, min_shared_cm=args.min_shared)

    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Find connected components first
    components = list(nx.connected_components(G))
    print(f"Connected components: {len(components)}")
    for i, comp in enumerate(sorted(components, key=len, reverse=True)[:5]):
        print(f"  Component {i+1}: {len(comp)} nodes")

    print(f"\nDetecting communities (resolution={args.resolution})...")
    partition = detect_communities(G, resolution=args.resolution)

    results = analyze_clusters(G, partition, matches)

    if args.save:
        print("\nSaving clusters to database...")
        save_clusters_to_db(results)


if __name__ == "__main__":
    main()
