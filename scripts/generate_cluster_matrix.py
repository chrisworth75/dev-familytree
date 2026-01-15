#!/usr/bin/env python3
"""Generate HTML cluster matrix for MRCA groups."""

import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

def get_cluster_matches(cursor, mrca):
    """Get all matches in a cluster."""
    cursor.execute("""
        SELECT id, name, shared_cm, ancestry_id
        FROM dna_match
        WHERE mrca = ?
        ORDER BY shared_cm DESC
    """, (mrca,))
    return cursor.fetchall()

def get_shared_matches(cursor, match_ids):
    """Get all shared match relationships for given matches."""
    if not match_ids:
        return {}

    placeholders = ','.join('?' * len(match_ids))
    cursor.execute(f"""
        SELECT match1_id, match2_id
        FROM shared_match
        WHERE match1_id IN ({placeholders})
          AND match2_id IN ({placeholders})
    """, match_ids + match_ids)

    shared = defaultdict(set)
    for match1_id, match2_id in cursor.fetchall():
        if match2_id:  # match2_id can be NULL
            shared[match1_id].add(match2_id)
            shared[match2_id].add(match1_id)

    return shared

def cluster_matches_by_shared(matches, shared):
    """Group matches into clusters based on shared DNA."""
    match_ids = [m[0] for m in matches]
    if not match_ids:
        return [matches]

    # Build adjacency
    adj = defaultdict(set)
    for mid in match_ids:
        adj[mid] = shared.get(mid, set()) & set(match_ids)

    # Find connected components using simple BFS
    visited = set()
    clusters = []

    for mid in match_ids:
        if mid in visited:
            continue
        cluster = []
        queue = [mid]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for neighbor in adj[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        clusters.append(cluster)

    # Sort clusters by total cM
    match_dict = {m[0]: m for m in matches}
    def cluster_cm(c):
        return sum(match_dict[mid][2] or 0 for mid in c)
    clusters.sort(key=cluster_cm, reverse=True)

    # Convert back to match tuples, sorted by cM within each cluster
    result = []
    for cluster in clusters:
        cluster_matches = [match_dict[mid] for mid in cluster]
        cluster_matches.sort(key=lambda m: m[2] or 0, reverse=True)
        result.append(cluster_matches)

    return result

def generate_html(mrca, clusters, shared, output_path):
    """Generate HTML matrix."""
    # Flatten matches for display
    all_matches = []
    cluster_starts = []
    for cluster in clusters:
        cluster_starts.append(len(all_matches))
        all_matches.extend(cluster)
    cluster_starts.append(len(all_matches))  # sentinel

    total_cm = sum(m[2] or 0 for m in all_matches)

    html = f'''<!DOCTYPE html>
<html>
<head>
<title>{mrca} Cluster Matrix (Grouped)</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 20px; background: #fff; }}
h1 {{ font-size: 18px; margin-bottom: 5px; }}
.subtitle {{ font-size: 12px; color: #666; margin-bottom: 15px; }}
.matrix {{ border-collapse: collapse; font-size: 9px; }}
.matrix th, .matrix td {{ width: 16px; height: 16px; text-align: center; padding: 0; }}
.matrix th {{ font-weight: normal; }}
.matrix th.name {{ text-align: left; width: auto; padding-right: 6px; white-space: nowrap; font-size: 10px; }}
.matrix th.cm {{ text-align: right; padding-left: 6px; font-size: 9px; color: #666; width: 30px; }}
.matrix th.top {{ writing-mode: vertical-lr; transform: rotate(180deg); height: 80px; font-size: 9px; }}
.match {{ background: #9b4d96; }}
.self {{ background: #333; }}
.empty {{ background: #f8f4f8; }}
.cluster-border {{ border-top: 2px solid #333; }}
.legend {{ margin-top: 20px; font-size: 11px; }}
.legend-item {{ display: inline-block; margin-right: 15px; }}
.legend-color {{ display: inline-block; width: 12px; height: 12px; margin-right: 4px; vertical-align: middle; }}
</style>
</head>
<body>
<h1>{mrca} Cluster Matrix</h1>
<p class="subtitle">{len(all_matches)} matches ({total_cm:,.0f} cM total) • Grouped by shared DNA clusters • Colored cells = share DNA</p>
<table class="matrix">
<tr><th></th><th class="cm">cM</th>
'''

    # Header row with rotated names
    for i, match in enumerate(all_matches):
        name_short = match[1][:15] + '...' if len(match[1]) > 15 else match[1]
        html += f'<th class="top">{name_short}</th>'
    html += '</tr>\n'

    # Data rows
    current_cluster = 0
    for i, match in enumerate(all_matches):
        # Check if we're at a new cluster boundary
        border_class = ''
        while current_cluster < len(cluster_starts) - 1 and i >= cluster_starts[current_cluster + 1]:
            current_cluster += 1
        if i == cluster_starts[current_cluster]:
            border_class = ' class="cluster-border"'

        name = match[1]
        cm = match[2] or 0
        mid = match[0]

        html += f'<tr{border_class}><th class="name">{name}</th><th class="cm">{cm:.0f}</th>'

        for j, other in enumerate(all_matches):
            oid = other[0]
            if mid == oid:
                html += '<td class="self"></td>'
            elif oid in shared.get(mid, set()):
                html += '<td class="match"></td>'
            else:
                html += '<td class="empty"></td>'

        html += '</tr>\n'

    html += '''</table>
<div class="legend">
<span class="legend-item"><span class="legend-color" style="background:#9b4d96;"></span>Shared DNA</span>
<span class="legend-item"><span class="legend-color" style="background:#333;"></span>Self</span>
<span class="legend-item"><span class="legend-color" style="background:#f8f4f8;"></span>No shared DNA</span>
</div>
</body>
</html>'''

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated: {output_path}")
    print(f"  Matches: {len(all_matches)}")
    print(f"  Total cM: {total_cm:,.0f}")
    print(f"  Sub-clusters: {len(clusters)}")

def main():
    parser = argparse.ArgumentParser(description='Generate cluster matrix HTML')
    parser.add_argument('mrca', help='MRCA cluster name (e.g., "UNK-PAT", "32-63")')
    parser.add_argument('--output', '-o', help='Output file path (default: Desktop/{mrca}-cluster-matrix.html)')
    parser.add_argument('--db', default=str(DB_PATH), help='Database path')
    args = parser.parse_args()

    # Sanitize mrca for filename
    safe_name = args.mrca.replace('+', 'plus').replace(' ', '_').replace('/', '-')
    output = args.output or f'/Users/chris/Desktop/{safe_name}-cluster-matrix.html'

    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    matches = get_cluster_matches(cursor, args.mrca)
    if not matches:
        print(f"No matches found for MRCA '{args.mrca}'")
        conn.close()
        return

    match_ids = [m[0] for m in matches]
    shared = get_shared_matches(cursor, match_ids)
    clusters = cluster_matches_by_shared(matches, shared)

    generate_html(args.mrca, clusters, shared, output)

    conn.close()

if __name__ == '__main__':
    main()
