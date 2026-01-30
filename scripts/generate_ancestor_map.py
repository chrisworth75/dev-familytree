#!/usr/bin/env python3
"""
Generate SVG visualization placing DNA matches on a 2D plane based on ancestor positions.
X-axis: Branch position (paternal left, maternal right) based on ahnentafel
Y-axis: Affinity - pulled toward known anchors they share DNA with
"""

import psycopg2
import math
from collections import defaultdict

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'familytree',
    'user': 'familytree',
    'password': 'familytree'
}

CHRIS_ID = 'E756DE6C-0C8D-443B-8793-ADDB6F35FD6A'


def get_ahnentafel_side(n):
    """Determine if ahnentafel is paternal (left/-1), maternal (right/+1), or self (0)."""
    if n == 1:
        return 0
    while n > 3:
        n = n // 2
    return -1 if n == 2 else 1  # 2=paternal(left), 3=maternal(right)


def get_ahnentafel_x_position(n, width=1800):
    """Calculate X position for an ahnentafel number."""
    if n == 1:
        return width / 2

    side = get_ahnentafel_side(n)
    generation = int(math.log2(n))

    # Position within the side based on generation and index
    gen_start = 2 ** generation
    gen_end = 2 ** (generation + 1) - 1
    index_in_gen = n - gen_start
    gen_size = gen_end - gen_start + 1

    # Normalize position within generation (0 to 1)
    if gen_size > 1:
        pos_in_gen = index_in_gen / (gen_size - 1)
    else:
        pos_in_gen = 0.5

    center = width / 2
    max_offset = width * 0.42  # Use more of the width

    # WIDER SPREAD: Use generation more aggressively
    # Gen 1 (parents): 0.3 of max
    # Gen 2 (grandparents): 0.5 of max
    # Gen 3 (great-grandparents): 0.7 of max
    # Gen 4+ (2xgreat+): 0.85+ of max
    gen_factor = min(0.9, 0.2 + generation * 0.17)

    if side == -1:  # Paternal (left)
        base_offset = -max_offset * gen_factor
        # Spread within generation
        spread = max_offset * 0.15 * (pos_in_gen - 0.5)
        return center + base_offset + spread
    else:  # Maternal (right)
        base_offset = max_offset * gen_factor
        spread = max_offset * 0.15 * (pos_in_gen - 0.5)
        return center + base_offset + spread


def get_anchors(cursor):
    """Get DNA matches with known ahnentafel positions (anchors)."""
    # Get people linked to person table who have ancestors with ahnentafel
    cursor.execute("""
        WITH RECURSIVE person_ancestors AS (
            -- Start with linked DNA matches
            SELECT ap.ancestry_id, ap.name, ap.person_id, p.id as current_id, 0 as depth
            FROM ancestry_person ap
            JOIN person p ON p.id = ap.person_id
            WHERE ap.person_id IS NOT NULL

            UNION ALL

            -- Go up the tree
            SELECT pa.ancestry_id, pa.name, pa.person_id,
                   COALESCE(p.parent_1_id, p.parent_2_id) as current_id,
                   pa.depth + 1
            FROM person_ancestors pa
            JOIN person p ON p.id = pa.current_id
            WHERE (p.parent_1_id IS NOT NULL OR p.parent_2_id IS NOT NULL)
            AND pa.depth < 10
        )
        SELECT DISTINCT pa.ancestry_id, pa.name, pa.person_id, c.ahnentafel_1, c.name as cluster_name
        FROM person_ancestors pa
        JOIN person p ON p.id = pa.current_id
        JOIN cluster c ON c.ahnentafel_1 IS NOT NULL
        JOIN person cp ON cp.id = (
            SELECT id FROM person WHERE ahnentafel = c.ahnentafel_1 LIMIT 1
        )
        WHERE pa.current_id IN (SELECT id FROM person WHERE ahnentafel IS NOT NULL)
           OR EXISTS (
               SELECT 1 FROM cluster c2
               WHERE c2.ahnentafel_1 IS NOT NULL
               AND pa.name ILIKE '%' || split_part(c2.name, ' ', 1) || '%'
           )
    """)

    # Simpler approach: get linked matches and their known ancestor line
    cursor.execute("""
        SELECT ap.ancestry_id, ap.name, ap.person_id,
               am.shared_cm
        FROM ancestry_person ap
        LEFT JOIN ancestry_match am ON (
            (am.person1_id = %s AND am.person2_id = ap.ancestry_id) OR
            (am.person2_id = %s AND am.person1_id = ap.ancestry_id)
        )
        WHERE ap.person_id IS NOT NULL
        ORDER BY am.shared_cm DESC NULLS LAST
    """, (CHRIS_ID, CHRIS_ID))

    anchors = {}
    for row in cursor.fetchall():
        ancestry_id, name, person_id, shared_cm = row
        anchors[ancestry_id] = {
            'name': name,
            'person_id': person_id,
            'shared_cm': float(shared_cm) if shared_cm else 0
        }

    return anchors


def get_ancestor_ahnentafels(cursor):
    """Get ahnentafel positions from cluster table."""
    cursor.execute("""
        SELECT id, name, ahnentafel_1, ahnentafel_2
        FROM cluster
        WHERE ahnentafel_1 IS NOT NULL
        ORDER BY ahnentafel_1
    """)

    ahnentafels = {}
    for row in cursor.fetchall():
        cluster_id, name, ahn1, ahn2 = row
        ahnentafels[cluster_id] = {
            'name': name,
            'ahnentafel': ahn1,
            'ahnentafel_2': ahn2
        }
    return ahnentafels


def assign_anchor_ahnentafels(cursor, anchors):
    """Assign ahnentafel positions to anchors based on their ancestry."""
    # Map known relationships to ahnentafel
    # This is based on the ThruLines data we've seen

    known_positions = {
        'Chris Worthington': 1,
        'Rebecca Hyndman': 1,  # Sister - same position as Chris essentially
        'Toby Yates': 1,  # Nephew

        # PATERNAL - Arthur Worthington line (ahnentafel 4)
        'Bruce Horrocks': 4,  # 1st cousin via Rosalind (Arthur's daughter)

        # PATERNAL - James Howarth line (4th great-grandfather, ~ahnentafel 64)
        'Christopher Bryan': 64,  # 3C1R via George Worthington

        # PATERNAL - James Worthington line (4th great-grandfather, ~ahnentafel 32)
        'Peter Davies': 32,  # 5th cousin via Richard Worthington
        'James Davies': 32,  # 5th cousin 1x removed

        # PATERNAL - Charles Hollows/Betty Marland line (~ahnentafel 48)
        'pcmtdm': 48,  # 4C1R via Martha Hollows
        'youngcodge2': 48,  # Half 2C1R via Jane Hollows

        # PATERNAL - George Parker line (~ahnentafel 40)
        'Doug Parker': 40,  # 3C1R via William Parker
        'nelwell17': 40,  # 4th cousin via Mary Parker
        'P.H.': 40,  # 4C1R via Thomas Parker

        # PATERNAL - John Wrathall line (HLW's father, ahnentafel 36)
        'Clara Faraday-Smith': 36,  # Half 5th cousin via Jane Wrathall
        'Chris Jackson': 36,  # Half 4C1R via Jane Wrathall

        # PATERNAL - HLW line (ahnentafel 18)
        'Helen Brammer': 18,  # Via Leslie Gordon (HLW's son)
        'hugh copland': 18,  # Via Leon Earl (HLW's son)
        'Rachel Wrathall': 18,  # Via Leon Earl → Henry L

        # MATERNAL - Emily Tart line (ahnentafel 31)
        'diane_lovick': 31,  # Via Emily Tart (half relation via Annie)
        'gstewart37': 31,  # Via Emily Tart → Fred
        'James Horridge': 31,  # Via Emily Tart → John

        # MATERNAL - Thomas Eattock line (Emily's father, ~ahnentafel 62)
        'Lynne Colley': 62,  # 3C1R via William H Eatock
        'Dwschloe0105': 62,  # Half 2C2R via Frank C Eattock
        'Edna Lowry': 62,  # Half 2C2R via Edward A Eattock
    }

    for ancestry_id, data in anchors.items():
        name = data['name']
        if name in known_positions:
            data['ahnentafel'] = known_positions[name]
        else:
            data['ahnentafel'] = None

    return anchors


def get_top_matches(cursor, limit=150):
    """Get Chris's top matches by cM."""
    cursor.execute("""
        SELECT ap.ancestry_id, ap.name, ap.person_id, ap.community_id,
               am.shared_cm
        FROM ancestry_person ap
        JOIN ancestry_match am ON (
            (am.person1_id = %s AND am.person2_id = ap.ancestry_id) OR
            (am.person2_id = %s AND am.person1_id = ap.ancestry_id)
        )
        WHERE ap.ancestry_id != %s
        ORDER BY am.shared_cm DESC
        LIMIT %s
    """, (CHRIS_ID, CHRIS_ID, CHRIS_ID, limit))

    matches = []
    for row in cursor.fetchall():
        ancestry_id, name, person_id, community_id, shared_cm = row
        matches.append({
            'ancestry_id': ancestry_id,
            'name': name,
            'person_id': person_id,
            'community_id': community_id,
            'shared_cm': float(shared_cm) if shared_cm else 0
        })
    return matches


def get_shared_matches(cursor, matches, anchors):
    """For each match, find which anchors they also match with."""
    anchor_ids = list(anchors.keys())

    shared_data = defaultdict(list)

    for match in matches:
        match_id = match['ancestry_id']

        # Find edges between this match and anchors
        cursor.execute("""
            SELECT person1_id, person2_id, shared_cm
            FROM ancestry_match
            WHERE (person1_id = %s OR person2_id = %s)
            AND (person1_id = ANY(%s) OR person2_id = ANY(%s))
        """, (match_id, match_id, anchor_ids, anchor_ids))

        for p1, p2, cm in cursor.fetchall():
            anchor_id = p1 if p1 in anchors else p2
            if anchor_id != match_id:
                shared_data[match_id].append({
                    'anchor_id': anchor_id,
                    'shared_cm': float(cm) if cm else 0
                })

    return shared_data


def calculate_match_position(match, shared_with_anchors, anchors, width, height, match_index=0):
    """Calculate X,Y position for a match based on anchor affinities."""

    # If this match IS an anchor, use its ahnentafel position
    if match['ancestry_id'] in anchors:
        anchor = anchors[match['ancestry_id']]
        ahn = anchor.get('ahnentafel', 1)
        if ahn:
            x = get_ahnentafel_x_position(ahn, width)
            # Y based on cM to Chris - spread across full height
            cm = match['shared_cm'] or 0
            # Use log scale for better spread
            import math
            if cm > 0:
                y_ratio = math.log(cm + 1) / math.log(3000)  # normalize to ~0-1
                y = 120 + (1 - y_ratio) * (height - 200)
            else:
                y = height - 100
            return x, y, True

    # For unknown matches, calculate weighted position based on anchor connections
    if not shared_with_anchors:
        # No anchor connections - spread along bottom
        y = height - 80 - (match_index % 5) * 30
        x = width / 2 + (match_index % 20 - 10) * 40
        return x, y, False

    # Weight positions by shared cM with anchors
    total_weight_x = 0
    weighted_x = 0

    for shared in shared_with_anchors:
        anchor_id = shared['anchor_id']
        cm = float(shared['shared_cm']) if shared['shared_cm'] else 0

        if anchor_id not in anchors:
            continue

        anchor = anchors[anchor_id]
        ahn = anchor.get('ahnentafel')

        if not ahn:
            continue

        anchor_x = get_ahnentafel_x_position(ahn, width)
        weight = cm

        # For X position: SKIP center anchors (ahnentafel 1)
        if ahn != 1:
            weighted_x += anchor_x * weight
            total_weight_x += weight

    # Calculate X from non-center anchors only
    if total_weight_x > 0:
        x = weighted_x / total_weight_x
    else:
        x = width / 2

    # Y based on cM to Chris - use log scale for spread
    import math
    chris_cm = match['shared_cm'] or 0
    if chris_cm > 0:
        y_ratio = math.log(chris_cm + 1) / math.log(3000)
        y = 120 + (1 - y_ratio) * (height - 200)
    else:
        y = height - 100

    return x, y, False


def cm_to_color(cm):
    """Map cM to a color (high cM = red, low cM = blue)."""
    if cm >= 500:
        return '#dc2626'  # red
    elif cm >= 200:
        return '#ea580c'  # orange
    elif cm >= 100:
        return '#ca8a04'  # yellow
    elif cm >= 50:
        return '#16a34a'  # green
    elif cm >= 20:
        return '#0891b2'  # cyan
    else:
        return '#6366f1'  # indigo


def generate_svg(matches, anchors, shared_data, width=2000, height=1400):
    """Generate the SVG visualization."""

    svg = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
    .title {{ font-family: sans-serif; font-size: 16px; font-weight: bold; }}
    .subtitle {{ font-family: sans-serif; font-size: 11px; fill: #666; }}
    .anchor-label {{ font-family: sans-serif; font-size: 9px; fill: #333; }}
    .match-label {{ font-family: sans-serif; font-size: 7px; fill: #666; }}
    .axis-label {{ font-family: sans-serif; font-size: 10px; fill: #999; }}
    .legend {{ font-family: sans-serif; font-size: 9px; }}
</style>
<defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="1" dy="1" stdDeviation="1" flood-opacity="0.3"/>
    </filter>
</defs>
<rect width="100%" height="100%" fill="#fafafa"/>

<!-- Title -->
<text x="{width/2}" y="25" text-anchor="middle" class="title">DNA Match Ancestor Map</text>
<text x="{width/2}" y="42" text-anchor="middle" class="subtitle">X: Ancestor branch (paternal ← → maternal) | Y: Affinity to known relatives</text>

<!-- Axis labels -->
<text x="50" y="{height/2}" class="axis-label">← Paternal</text>
<text x="{width-80}" y="{height/2}" class="axis-label">Maternal →</text>
<text x="{width/2}" y="70" text-anchor="middle" class="axis-label">Close relatives (high cM)</text>
<text x="{width/2}" y="{height-20}" text-anchor="middle" class="axis-label">Distant / unknown branch</text>

<!-- Center line -->
<line x1="{width/2}" y1="80" x2="{width/2}" y2="{height-50}" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4"/>

<!-- Branch zones -->
<rect x="100" y="80" width="{width/2-150}" height="{height-130}" fill="#fef2f2" opacity="0.3"/>
<rect x="{width/2+50}" y="80" width="{width/2-150}" height="{height-130}" fill="#eff6ff" opacity="0.3"/>
<text x="200" y="100" class="axis-label" fill="#991b1b">HLW Line (ahn 18)</text>
<text x="{width-250}" y="100" class="axis-label" fill="#1e40af">Tart Line (ahn 31)</text>
''']

    # Calculate positions for all matches
    positions = {}
    for i, match in enumerate(matches):
        match_id = match['ancestry_id']
        shared = shared_data.get(match_id, [])
        x, y, is_anchor = calculate_match_position(match, shared, anchors, width, height, i)

        # Add jitter to prevent overlap
        import random
        random.seed(hash(match_id))
        x += random.uniform(-25, 25)
        y += random.uniform(-20, 20)

        # Keep within bounds
        x = max(100, min(width - 100, x))
        y = max(100, min(height - 80, y))

        positions[match_id] = (x, y, is_anchor)

    # Draw ALL edges between people who share DNA (not just to anchors)
    svg.append('<!-- DNA match connections -->')
    drawn_edges = set()

    for match in matches:
        match_id = match['ancestry_id']
        if match_id not in positions:
            continue
        mx, my, _ = positions[match_id]

        shared = shared_data.get(match_id, [])
        for s in shared:
            other_id = s['anchor_id']
            if other_id in positions:
                # Avoid drawing same edge twice
                edge_key = tuple(sorted([match_id, other_id]))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)

                ox, oy, _ = positions[other_id]
                cm = s['shared_cm']

                # Style based on cM
                if cm >= 100:
                    stroke = "#dc2626"
                    width_val = 1.5
                    opacity = 0.6
                elif cm >= 50:
                    stroke = "#ea580c"
                    width_val = 1.0
                    opacity = 0.5
                elif cm >= 20:
                    stroke = "#94a3b8"
                    width_val = 0.7
                    opacity = 0.4
                else:
                    stroke = "#cbd5e1"
                    width_val = 0.5
                    opacity = 0.3

                svg.append(f'<line x1="{mx:.1f}" y1="{my:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" '
                          f'stroke="{stroke}" stroke-width="{width_val}" opacity="{opacity:.2f}"/>')

    # Track label positions to avoid overlap
    label_positions = []

    def find_label_offset(x, y, label_positions, radius=50):
        """Find offset to avoid label overlap."""
        for lx, ly in label_positions:
            if abs(x - lx) < radius and abs(y - ly) < 20:
                return 25  # Offset down
        return 0

    # Draw matches (non-anchors first, then anchors on top)
    svg.append('<!-- Unknown matches -->')
    for i, match in enumerate(matches):
        match_id = match['ancestry_id']
        if match_id not in positions:
            continue
        x, y, is_anchor = positions[match_id]

        if is_anchor:
            continue

        cm = match['shared_cm']
        color = cm_to_color(cm)
        radius = 5 + min(8, cm / 80)

        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" opacity="0.8"/>')

        # Label for higher cM matches
        if cm >= 30:
            name = match['name'][:18]
            offset = find_label_offset(x, y, label_positions)
            label_y = y - radius - 4 - offset
            label_positions.append((x, label_y))
            svg.append(f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="match-label">{name} ({cm:.0f})</text>')

    # Draw anchors (known relatives)
    svg.append('<!-- Anchors (known relatives) -->')
    for match in matches:
        match_id = match['ancestry_id']
        if match_id not in positions:
            continue
        x, y, is_anchor = positions[match_id]

        if not is_anchor:
            continue

        cm = match['shared_cm'] or 0
        color = '#7c3aed'  # Purple for anchors
        radius = 10 + min(12, cm / 150)

        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" filter="url(#shadow)"/>')

        name = match['name'][:22]
        cm_str = f"({cm:.0f} cM)" if cm else ""
        offset = find_label_offset(x, y, label_positions)
        label_y = y - radius - 5 - offset
        label_positions.append((x, label_y))
        svg.append(f'<text x="{x:.1f}" y="{label_y:.1f}" text-anchor="middle" class="anchor-label" font-weight="bold">{name}</text>')
        if cm_str:
            svg.append(f'<text x="{x:.1f}" y="{label_y - 11:.1f}" text-anchor="middle" class="match-label">{cm_str}</text>')

    # Legend
    svg.append(f'''
<!-- Legend -->
<rect x="{width-180}" y="60" width="170" height="200" fill="white" stroke="#e5e7eb" rx="4"/>
<text x="{width-170}" y="78" class="legend" font-weight="bold">cM to Chris (circles):</text>
<circle cx="{width-160}" cy="95" r="5" fill="#dc2626"/>
<text x="{width-148}" y="98" class="legend">500+ cM</text>
<circle cx="{width-160}" cy="112" r="5" fill="#ea580c"/>
<text x="{width-148}" y="115" class="legend">200-500 cM</text>
<circle cx="{width-160}" cy="129" r="5" fill="#ca8a04"/>
<text x="{width-148}" y="132" class="legend">100-200 cM</text>
<circle cx="{width-160}" cy="146" r="5" fill="#16a34a"/>
<text x="{width-148}" y="149" class="legend">50-100 cM</text>
<circle cx="{width-160}" cy="163" r="5" fill="#0891b2"/>
<text x="{width-148}" y="166" class="legend">20-50 cM</text>
<circle cx="{width-160}" cy="180" r="7" fill="#7c3aed"/>
<text x="{width-148}" y="183" class="legend">Known anchor</text>

<text x="{width-170}" y="205" class="legend" font-weight="bold">Lines (shared DNA):</text>
<line x1="{width-165}" y1="218" x2="{width-145}" y2="218" stroke="#dc2626" stroke-width="1.5"/>
<text x="{width-140}" y="221" class="legend">100+ cM</text>
<line x1="{width-165}" y1="235" x2="{width-145}" y2="235" stroke="#ea580c" stroke-width="1"/>
<text x="{width-140}" y="238" class="legend">50-100 cM</text>
<line x1="{width-165}" y1="252" x2="{width-145}" y2="252" stroke="#94a3b8" stroke-width="0.7"/>
<text x="{width-140}" y="255" class="legend">20-50 cM</text>
''')

    svg.append('</svg>')
    return '\n'.join(svg)


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Getting anchors (linked DNA matches)...")
    anchors = get_anchors(cursor)
    anchors = assign_anchor_ahnentafels(cursor, anchors)
    print(f"  Found {len(anchors)} anchors")

    print("Getting top matches...")
    matches = get_top_matches(cursor, limit=150)
    print(f"  Found {len(matches)} matches")

    print("Finding triangulation data...")
    shared_data = get_shared_matches(cursor, matches, anchors)
    matches_with_triangulation = sum(1 for m in matches if m['ancestry_id'] in shared_data)
    print(f"  {matches_with_triangulation} matches have anchor connections")

    print("Generating SVG...")
    svg = generate_svg(matches, anchors, shared_data)

    output_path = '/Users/chris/dev-familytree/output/ancestor_map.svg'
    with open(output_path, 'w') as f:
        f.write(svg)

    print(f"Generated: {output_path}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
