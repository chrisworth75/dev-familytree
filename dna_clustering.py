#!/usr/bin/env python3
"""
DNA Match Clustering Tool
Finds cliques (fully connected groups) and clusters (communities) from DNA match data.
Uses the new ancestry_person/ancestry_match graph schema.
"""

import argparse
import psycopg2
import networkx as nx
from collections import defaultdict

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'familytree',
    'user': 'familytree',
    'password': 'familytree'
}

# Chris's ancestry_id
CHRIS_ID = 'E756DE6C-0C8D-443B-8793-ADDB6F35FD6A'


def build_graph(cursor, min_cm=0):
    """
    Build a graph from ancestry_person (nodes) and ancestry_match (edges).
    """
    # Get all people (nodes)
    cursor.execute("""
        SELECT ancestry_id, name, person_id
        FROM ancestry_person
    """)
    people = {row[0]: {'name': row[1], 'person_id': row[2]} for row in cursor.fetchall()}

    # Get all edges above threshold
    cursor.execute("""
        SELECT person1_id, person2_id, shared_cm
        FROM ancestry_match
        WHERE shared_cm >= %s OR shared_cm IS NULL
    """, (min_cm,))
    edges = cursor.fetchall()

    # Build networkx graph
    G = nx.Graph()

    # Add nodes
    for ancestry_id, data in people.items():
        G.add_node(ancestry_id, **data)

    # Add edges
    for p1, p2, cm in edges:
        G.add_edge(p1, p2, shared_cm=float(cm) if cm else 0.0)

    return G, people


def calculate_density(G, nodes):
    """Calculate density of a subgraph (edges present / edges possible)."""
    subgraph = G.subgraph(nodes)
    n = len(nodes)
    if n < 2:
        return 1.0
    possible_edges = n * (n - 1) / 2
    actual_edges = subgraph.number_of_edges()
    return actual_edges / possible_edges


def find_cliques(G, min_size=3, max_cliques=100):
    """Find maximal cliques of at least min_size."""
    cliques = []
    for i, clique in enumerate(nx.find_cliques(G)):
        if len(clique) >= min_size:
            density = calculate_density(G, clique)
            cliques.append({
                'nodes': set(clique),
                'size': len(clique),
                'density': density
            })
        if len(cliques) >= max_cliques:
            break
    return cliques


def find_communities(G, min_size=3):
    """Find communities using Louvain algorithm."""
    try:
        import community.community_louvain as community_louvain
        partition = community_louvain.best_partition(G, weight='shared_cm')

        # Group by community
        communities_dict = defaultdict(set)
        for node, comm_id in partition.items():
            communities_dict[comm_id].add(node)

        communities = []
        for comm_id, nodes in communities_dict.items():
            if len(nodes) >= min_size:
                density = calculate_density(G, nodes)
                communities.append({
                    'nodes': nodes,
                    'size': len(nodes),
                    'density': density
                })
        return communities
    except ImportError:
        # Fall back to greedy modularity
        from networkx.algorithms.community import greedy_modularity_communities
        communities = []
        for community in greedy_modularity_communities(G):
            if len(community) >= min_size:
                density = calculate_density(G, community)
                communities.append({
                    'nodes': set(community),
                    'size': len(community),
                    'density': density
                })
        return communities


def get_display_name(node, people):
    """Get display name for a node."""
    if node in people:
        name = people[node]['name']
        if node == CHRIS_ID:
            return f"[{name}]"  # Brackets for test-taker
        return name
    return node[:8] + "..."


def print_cliques(cliques, people, limit=20):
    """Print cliques with their members."""
    print("\n" + "=" * 60)
    print(f"CLIQUES (fully connected groups) - showing top {limit}")
    print("=" * 60)

    # Sort by size descending
    cliques_sorted = sorted(cliques, key=lambda x: x['size'], reverse=True)[:limit]

    for i, clique in enumerate(cliques_sorted, 1):
        names = sorted([get_display_name(n, people) for n in clique['nodes']])
        print(f"\nClique {i}: {clique['size']} members")

        # Show first 10 members
        for name in names[:10]:
            print(f"  - {name}")
        if len(names) > 10:
            print(f"  ... and {len(names) - 10} more")


def print_communities(communities, people, limit=20):
    """Print communities with their members."""
    print("\n" + "=" * 60)
    print(f"COMMUNITIES (Louvain clusters) - showing top {limit}")
    print("=" * 60)

    # Sort by size descending
    communities_sorted = sorted(communities, key=lambda x: x['size'], reverse=True)[:limit]

    for i, comm in enumerate(communities_sorted, 1):
        names = sorted([get_display_name(n, people) for n in comm['nodes']])
        has_chris = CHRIS_ID in comm['nodes']
        marker = " ★" if has_chris else ""

        print(f"\nCommunity {i}: {comm['size']} members, density={comm['density']:.3f}{marker}")

        # Show first 10 members
        for name in names[:10]:
            print(f"  - {name}")
        if len(names) > 10:
            print(f"  ... and {len(names) - 10} more")


def analyze_components(G, people):
    """Analyze connected components."""
    components = list(nx.connected_components(G))

    print("\n" + "=" * 60)
    print("CONNECTED COMPONENTS")
    print("=" * 60)
    print(f"Total components: {len(components)}")

    # Sort by size
    components_sorted = sorted(components, key=len, reverse=True)

    for i, comp in enumerate(components_sorted[:10], 1):
        has_chris = CHRIS_ID in comp
        marker = " ★ (main component)" if has_chris else ""
        sample = [get_display_name(n, people) for n in list(comp)[:3]]
        print(f"  {i}. {len(comp):,} nodes{marker}")
        print(f"     Sample: {', '.join(sample)}")


def main():
    parser = argparse.ArgumentParser(description="DNA Match Clustering Tool")
    parser.add_argument("--min-cm", type=float, default=20, help="Minimum cM for edges (default: 20)")
    parser.add_argument("--min-size", type=int, default=3, help="Minimum cluster size (default: 3)")
    parser.add_argument("--no-cliques", action="store_true", help="Skip clique finding (slow on large graphs)")
    parser.add_argument("--limit", type=int, default=20, help="Max results to show (default: 20)")
    args = parser.parse_args()

    print("=" * 60)
    print("DNA CLUSTERING ANALYSIS")
    print("=" * 60)

    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print(f"Building graph (min_cm={args.min_cm})...")
    G, people = build_graph(cursor, min_cm=args.min_cm)
    print(f"  Nodes: {G.number_of_nodes():,}")
    print(f"  Edges: {G.number_of_edges():,}")

    # Analyze components
    analyze_components(G, people)

    # Find communities
    print("\nFinding communities...")
    communities = find_communities(G, min_size=args.min_size)
    print(f"  Found {len(communities)} communities of size >= {args.min_size}")
    print_communities(communities, people, limit=args.limit)

    # Find cliques (optional, can be slow)
    if not args.no_cliques:
        print("\nFinding cliques (this may take a while)...")
        cliques = find_cliques(G, min_size=args.min_size, max_cliques=100)
        print(f"  Found {len(cliques)} cliques of size >= {args.min_size}")
        print_cliques(cliques, people, limit=args.limit)

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == '__main__':
    main()
