#!/usr/bin/env python3
"""
Generate SVG visualization of DNA match adjacency matrix for a community.
"""

import psycopg2
import networkx as nx
from collections import defaultdict

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'familytree',
    'user': 'familytree',
    'password': 'familytree'
}

CHRIS_ID = 'E756DE6C-0C8D-443B-8793-ADDB6F35FD6A'


def get_community_members(cursor, min_cm=20):
    """Get Chris's community members using Louvain algorithm."""
    try:
        import community.community_louvain as community_louvain
    except ImportError:
        print("Installing python-louvain...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'python-louvain'])
        import community.community_louvain as community_louvain

    # Build graph
    cursor.execute("SELECT ancestry_id, name, person_id FROM ancestry_person")
    people = {row[0]: {'name': row[1], 'person_id': row[2]} for row in cursor.fetchall()}

    cursor.execute("""
        SELECT person1_id, person2_id, shared_cm
        FROM ancestry_match
        WHERE shared_cm >= %s OR shared_cm IS NULL
    """, (min_cm,))
    edges = cursor.fetchall()

    G = nx.Graph()
    for ancestry_id, data in people.items():
        G.add_node(ancestry_id, **data)
    for p1, p2, cm in edges:
        G.add_edge(p1, p2, shared_cm=float(cm) if cm else 0.0)

    # Find communities
    partition = community_louvain.best_partition(G, weight='shared_cm')

    # Get Chris's community
    chris_community = partition.get(CHRIS_ID)
    members = [node for node, comm in partition.items() if comm == chris_community]

    return G, people, members


def generate_svg(G, people, members, output_path, max_members=50):
    """Generate SVG adjacency matrix."""

    # Sort members by cM to Chris (highest first), limit to max_members
    chris_edges = {}
    for m in members:
        if G.has_edge(CHRIS_ID, m):
            chris_edges[m] = G[CHRIS_ID][m].get('shared_cm', 0)
        elif m == CHRIS_ID:
            chris_edges[m] = 9999  # Chris at top
        else:
            chris_edges[m] = 0

    sorted_members = sorted(members, key=lambda x: -chris_edges.get(x, 0))[:max_members]
    n = len(sorted_members)

    # SVG dimensions
    cell_size = 12
    label_width = 180
    margin = 20
    header_height = 180

    width = label_width + n * cell_size + margin * 2
    height = header_height + n * cell_size + margin * 2

    # Start SVG
    svg = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
    .label {{ font-family: monospace; font-size: 9px; }}
    .header {{ font-family: monospace; font-size: 9px; }}
    .title {{ font-family: sans-serif; font-size: 14px; font-weight: bold; }}
    .match {{ fill: #2563eb; }}
    .self {{ fill: #9333ea; }}
    .no-match {{ fill: #f3f4f6; }}
    .grid {{ stroke: #e5e7eb; stroke-width: 0.5; }}
</style>
<rect width="100%" height="100%" fill="white"/>
<text x="{margin}" y="{margin + 12}" class="title">DNA Match Adjacency Matrix - Chris's Community (top {n} by cM)</text>
''']

    # Draw rotated column headers
    for i, m in enumerate(sorted_members):
        name = people.get(m, {}).get('name', m[:8])[:20]
        cm = chris_edges.get(m, 0)
        if m == CHRIS_ID:
            label = f"[Chris]"
        else:
            label = f"{name} ({cm:.0f})"

        x = label_width + margin + i * cell_size + cell_size/2
        y = header_height - 5
        svg.append(f'<text x="{x}" y="{y}" class="header" transform="rotate(-45 {x} {y})">{label}</text>')

    # Draw row labels and cells
    for i, m1 in enumerate(sorted_members):
        name = people.get(m1, {}).get('name', m1[:8])[:20]
        cm = chris_edges.get(m1, 0)
        if m1 == CHRIS_ID:
            label = "[Chris Worthington]"
        else:
            label = f"{name} ({cm:.0f})"

        y = header_height + margin + i * cell_size

        # Row label
        svg.append(f'<text x="{margin}" y="{y + cell_size - 2}" class="label">{label}</text>')

        # Cells
        for j, m2 in enumerate(sorted_members):
            x = label_width + margin + j * cell_size

            if m1 == m2:
                css_class = "self"
            elif G.has_edge(m1, m2):
                css_class = "match"
            else:
                css_class = "no-match"

            svg.append(f'<rect x="{x}" y="{y}" width="{cell_size-1}" height="{cell_size-1}" class="{css_class}"/>')

    # Grid lines
    for i in range(n + 1):
        x = label_width + margin + i * cell_size
        y1 = header_height + margin
        y2 = header_height + margin + n * cell_size
        svg.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" class="grid"/>')

        y = header_height + margin + i * cell_size
        x1 = label_width + margin
        x2 = label_width + margin + n * cell_size
        svg.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="grid"/>')

    # Legend
    legend_y = height - 25
    svg.append(f'<rect x="{margin}" y="{legend_y}" width="12" height="12" class="match"/>')
    svg.append(f'<text x="{margin + 16}" y="{legend_y + 10}" class="label">DNA Match</text>')
    svg.append(f'<rect x="{margin + 90}" y="{legend_y}" width="12" height="12" class="self"/>')
    svg.append(f'<text x="{margin + 106}" y="{legend_y + 10}" class="label">Self</text>')
    svg.append(f'<rect x="{margin + 150}" y="{legend_y}" width="12" height="12" class="no-match"/>')
    svg.append(f'<text x="{margin + 166}" y="{legend_y + 10}" class="label">No Match</text>')

    svg.append('</svg>')

    with open(output_path, 'w') as f:
        f.write('\n'.join(svg))

    print(f"Generated SVG: {output_path}")
    print(f"  Members shown: {n}")
    print(f"  Dimensions: {width}x{height}")


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Finding Chris's community...")
    G, people, members = get_community_members(cursor, min_cm=20)
    print(f"  Community has {len(members)} members")

    output_path = '/Users/chris/dev-familytree/output/community_matrix.svg'
    generate_svg(G, people, members, output_path, max_members=50)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
