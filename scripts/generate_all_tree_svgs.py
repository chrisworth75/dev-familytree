#!/usr/bin/env python3
"""
Generate SVG family trees for the family-tree-app.

Creates descendant tree SVGs for each configured family, starting from the
earliest ancestor in each line.

Usage:
    python scripts/generate_all_tree_svgs.py
    python scripts/generate_all_tree_svgs.py --family wrathall
    python scripts/generate_all_tree_svgs.py --output-dir /path/to/dir
"""

import argparse
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "family-tree-app" / "src" / "main" / "resources" / "static" / "trees"

# Family configurations - root person and display info
# Using specific person IDs where known, or queries to find the best root
FAMILY_CONFIGS = {
    'wrathall': {
        'surname': 'Wrathall',
        'root_id': 1,  # Henry S. Wrathall (1843) - father of HLW
    },
    'worthington': {
        'surname': 'Worthington',
        'root_id': 575426,  # Henry Worthington (1777-1854) - 5th Great-Grandfather
    },
    'wood': {
        'surname': 'Wood',
        'root_id': 56,  # Joseph Wood (1830) - has 7 children
    },
    'goodall': {
        'surname': 'Goodall',
        'root_query': """
            SELECT p.id FROM person p
            WHERE p.surname = 'Goodall' AND p.tree_id = 1
            AND EXISTS (SELECT 1 FROM person c WHERE c.mother_id = p.id OR c.father_id = p.id)
            ORDER BY p.birth_year_estimate ASC
            LIMIT 1
        """,
    },
    'heywood': {
        'surname': 'Heywood',
        'root_id': 37,  # Samuel Heywood (1870)
    },
    'virgo': {
        'surname': 'Virgo',
        'root_query': """
            SELECT p.id FROM person p
            WHERE p.surname = 'Virgo' AND p.tree_id = 1
            AND EXISTS (SELECT 1 FROM person c WHERE c.mother_id = p.id OR c.father_id = p.id)
            ORDER BY p.birth_year_estimate ASC
            LIMIT 1
        """,
    },
    'tart': {
        'surname': 'Tart',
        'root_id': 40,  # Matilda Tart (1843) - has 5 children
    },
}

FEMALE_NAMES = {'mary', 'alice', 'constance', 'blanche', 'evelyn', 'ethel', 'jane',
                'margaret', 'angela', 'janet', 'betty', 'susan', 'ann', 'elizabeth',
                'doris', 'marjorie', 'patricia', 'nina', 'rachel', 'verity', 'kathleen',
                'muriel', 'agnes', 'sarah', 'emma', 'lily', 'rose', 'irene', 'annie',
                'loreen', 'betsy', 'theodora', 'maria', 'ellen', 'elsie', 'grace',
                'rebecca', 'jennifer', 'helen', 'florence', 'mildred', 'harriet',
                'dorothy', 'edith', 'gladys', 'mabel', 'clara', 'charlotte', 'caroline',
                'catherine', 'kate', 'lucy', 'amy', 'julia', 'laura', 'eleanor', 'frances',
                'virginia', 'beatrice', 'lillian', 'hazel', 'gertrude', 'josephine', 'esther',
                'norah', 'miriam', 'hannah', 'ruth', 'fanny', 'emily', 'harriet', 'eliza',
                'minnie', 'matilda', 'sophia', 'hilda', 'maggie', 'maud', 'antoinette'}


@dataclass
class Person:
    id: int
    forename: str
    surname: str
    birth_year: int | None
    death_year: int | None
    sex: str = "M"
    children: list['Person'] = field(default_factory=list)
    spouse_name: str | None = None


def guess_sex(forename: str) -> str:
    """Guess sex from first name."""
    if not forename:
        return "M"
    first_name = forename.lower().split()[0]
    if first_name in FEMALE_NAMES:
        return "F"
    return "M"


def get_spouse_name(conn, person_id: int) -> str | None:
    """Get spouse name from relationship table or marriage table."""
    cursor = conn.cursor()

    # Try relationship table first
    cursor.execute("""
        SELECT p.forename, p.surname
        FROM relationship r
        JOIN person p ON (r.person_id_2 = p.id AND r.person_id_1 = ?)
                      OR (r.person_id_1 = p.id AND r.person_id_2 = ?)
        WHERE r.relationship_type = 'spouse'
        LIMIT 1
    """, (person_id, person_id))
    row = cursor.fetchone()
    if row:
        return f"{row[0] or ''} {row[1] or ''}".strip()

    # Try marriage table
    cursor.execute("""
        SELECT p.forename, p.surname
        FROM marriage m
        JOIN person p ON (m.person_id_2 = p.id AND m.person_id_1 = ?)
                      OR (m.person_id_1 = p.id AND m.person_id_2 = ?)
        LIMIT 1
    """, (person_id, person_id))
    row = cursor.fetchone()
    if row:
        return f"{row[0] or ''} {row[1] or ''}".strip()

    return None


def get_descendants(conn, root_id: int, visited: set = None, max_depth: int = 15) -> Person | None:
    """Recursively fetch a person and all their descendants."""
    if visited is None:
        visited = set()

    if root_id in visited or max_depth <= 0:
        return None
    visited.add(root_id)

    cursor = conn.cursor()

    # Get person details
    cursor.execute("""
        SELECT id, forename, surname, birth_year_estimate, death_year_estimate
        FROM person WHERE id = ?
    """, (root_id,))
    row = cursor.fetchone()
    if not row:
        return None

    person = Person(
        id=row[0],
        forename=row[1] or "",
        surname=row[2] or "",
        birth_year=row[3],
        death_year=row[4],
        sex=guess_sex(row[1])
    )

    # Get spouse
    person.spouse_name = get_spouse_name(conn, root_id)

    # Get children
    cursor.execute("""
        SELECT DISTINCT id FROM person
        WHERE mother_id = ? OR father_id = ?
        ORDER BY birth_year_estimate
    """, (root_id, root_id))

    for (child_id,) in cursor.fetchall():
        child = get_descendants(conn, child_id, visited, max_depth - 1)
        if child:
            person.children.append(child)

    person.children.sort(key=lambda c: c.birth_year or 9999)
    return person


def find_root_person(conn, config: dict) -> int | None:
    """Find the root person for a family."""
    cursor = conn.cursor()

    # Use specific root_id if provided
    if 'root_id' in config:
        return config['root_id']

    # Try the root query
    if 'root_query' in config:
        cursor.execute(config['root_query'])
        row = cursor.fetchone()
        if row:
            return row[0]

    # Fallback: find by forename and surname
    if 'fallback_forename' in config:
        cursor.execute("""
            SELECT id FROM person
            WHERE forename LIKE ? AND surname LIKE ?
            AND tree_id = 1
            ORDER BY birth_year_estimate
            LIMIT 1
        """, (f"%{config['fallback_forename']}%", f"%{config['surname']}%"))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Last resort: find earliest person with that surname who has children
    cursor.execute("""
        SELECT p.id FROM person p
        WHERE p.surname LIKE ? AND p.tree_id = 1
        AND EXISTS (SELECT 1 FROM person c WHERE c.mother_id = p.id OR c.father_id = p.id)
        ORDER BY p.birth_year_estimate ASC
        LIMIT 1
    """, (f"%{config['surname']}%",))
    row = cursor.fetchone()
    return row[0] if row else None


class SVGGenerator:
    """Generate SVG family tree with staggered sibling layout."""

    CARD_WIDTH = 160
    CARD_HEIGHT = 55
    CARD_SPACING_X = 10
    ROW_HEIGHT_SAME_GEN = 60
    GEN_HEIGHT = 100
    PADDING = 30

    def __init__(self):
        self.elements = []
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.max_y = 0
        self.person_positions = {}

    def generate(self, root: Person, title: str = None) -> str:
        """Generate SVG for the tree."""
        self.elements = []
        self.person_positions = {}

        # Do layout
        self._layout_person(root, x=0, y=80, gen=0)

        # Shift to positive coordinates
        shift_x = self.PADDING - self.min_x
        self.elements = []
        old_positions = self.person_positions.copy()
        self.person_positions = {}
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.max_y = 0

        root_new_x = old_positions[root.id][0] + shift_x
        self._layout_person(root, x=root_new_x, y=80, gen=0)

        width = self.max_x + self.PADDING
        height = self.max_y + self.PADDING
        root_center_x = self.person_positions[root.id][0] + self.CARD_WIDTH / 2

        if title is None:
            title = f"{root.forename} {root.surname} - Descendants"

        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" data-root-x="{root_center_x}">
  <defs>
    <style>
      .card {{ fill: #fff; stroke: #d0d0d0; stroke-width: 1; }}
      .card:hover {{ stroke: #4a90a4; stroke-width: 2; cursor: pointer; }}
      .avatar-male {{ fill: url(#maleGradient); }}
      .avatar-female {{ fill: url(#femaleGradient); }}
      .name {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 11px; font-weight: 600; fill: #333; }}
      .dates {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 9px; fill: #666; }}
      .spouse {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 8px; fill: #888; font-style: italic; }}
      .connector {{ stroke: #c0c0c0; stroke-width: 1.5; fill: none; }}
      .connector-long {{ stroke: #c0c0c0; stroke-width: 1.5; fill: none; stroke-dasharray: 4,2; }}
    </style>
    <linearGradient id="maleGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#6b8e9f"/>
      <stop offset="100%" style="stop-color:#4a7085"/>
    </linearGradient>
    <linearGradient id="femaleGradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#c48b9f"/>
      <stop offset="100%" style="stop-color:#a06b7f"/>
    </linearGradient>
  </defs>

  <rect width="100%" height="100%" fill="#fff"/>

  <text x="{root_center_x}" y="30" text-anchor="middle" class="name" style="font-size: 16px;">
    {title}
  </text>
  <text x="{root_center_x}" y="48" text-anchor="middle" class="dates">
    Click on any person to view their details
  </text>
  <line x1="30" y1="58" x2="{width - 30}" y2="58" stroke="#e0e0e0"/>

  {''.join(self.elements)}
</svg>'''
        return svg

    def _layout_person(self, person: Person, x: float, y: float, gen: int) -> float:
        """Layout a person and descendants. Returns width used."""
        self.person_positions[person.id] = (x, y)
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x + self.CARD_WIDTH)
        self.max_y = max(self.max_y, y + self.CARD_HEIGHT)

        self._draw_person_card(person, x, y)

        if not person.children:
            return self.CARD_WIDTH

        num_children = len(person.children)

        # All children on one row - compact layout
        child_y = y + self.GEN_HEIGHT
        parent_cx = x + self.CARD_WIDTH / 2

        # Use fixed card width, not subtree width - more compact
        total_width = num_children * self.CARD_WIDTH + (num_children - 1) * self.CARD_SPACING_X

        # Center children under parent
        start_x = parent_cx - total_width / 2
        current_x = start_x
        connector_points = []

        for child in person.children:
            self._layout_person(child, current_x, child_y, gen + 1)
            connector_points.append(current_x + self.CARD_WIDTH / 2)
            current_x += self.CARD_WIDTH + self.CARD_SPACING_X

        # Draw connectors
        parent_bottom = y + self.CARD_HEIGHT
        junction_y = y + self.CARD_HEIGHT + 20
        self._draw_connector(parent_cx, parent_bottom, parent_cx, junction_y, False)

        if connector_points:
            min_x_conn = min(connector_points + [parent_cx])
            max_x_conn = max(connector_points + [parent_cx])
            self._draw_connector(min_x_conn, junction_y, max_x_conn, junction_y, False)

            for child_cx in connector_points:
                self._draw_connector(child_cx, junction_y, child_cx, child_y, False)

        if connector_points:
            actual_width = max(connector_points) - min(connector_points) + self.CARD_WIDTH
        else:
            actual_width = self.CARD_WIDTH

        return max(self.CARD_WIDTH, actual_width)

    def _estimate_subtree_width(self, person: Person) -> float:
        if not person.children:
            return self.CARD_WIDTH
        total = 0
        for child in person.children:
            total += self._estimate_subtree_width(child) + self.CARD_SPACING_X
        return max(self.CARD_WIDTH, total - self.CARD_SPACING_X)

    def _draw_person_card(self, person: Person, x: float, y: float):
        avatar_class = "avatar-female" if person.sex == "F" else "avatar-male"

        dates = ""
        if person.birth_year:
            dates = str(person.birth_year)
            if person.death_year:
                dates += f"-{person.death_year}"
            else:
                dates += "-"

        name = f"{person.forename} {person.surname}".strip()
        if not name:
            name = "Unknown"
        elif len(name) > 22:
            name = name[:20] + "..."

        spouse_line = ""
        if person.spouse_name:
            spouse_short = person.spouse_name[:18] + "..." if len(person.spouse_name) > 20 else person.spouse_name
            spouse_line = f'<text x="{x + 40}" y="{y + 47}" class="spouse">m. {spouse_short}</text>'

        card = f'''
  <g class="person-card" data-person-id="{person.id}">
    <rect x="{x}" y="{y}" width="{self.CARD_WIDTH}" height="{self.CARD_HEIGHT}" rx="5" class="card"/>
    <circle cx="{x + 20}" cy="{y + 28}" r="14" class="{avatar_class}"/>
    <text x="{x + 40}" y="{y + 20}" class="name">{self._escape_xml(name)}</text>
    <text x="{x + 40}" y="{y + 33}" class="dates">{dates}</text>
    {spouse_line}
  </g>'''
        self.elements.append(card)

    def _draw_connector(self, x1: float, y1: float, x2: float, y2: float, dashed: bool):
        css_class = "connector-long" if dashed else "connector"
        self.elements.append(f'  <path d="M{x1} {y1} L{x2} {y2}" class="{css_class}"/>\n')

    def _escape_xml(self, s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def count_people(person: Person) -> int:
    count = 1
    for child in person.children:
        count += count_people(child)
    return count


def generate_family_svg(conn, family_name: str, output_dir: Path) -> bool:
    """Generate SVG for a specific family."""
    if family_name not in FAMILY_CONFIGS:
        print(f"Unknown family: {family_name}")
        return False

    config = FAMILY_CONFIGS[family_name]
    print(f"\nGenerating {family_name.title()} family tree...")

    root_id = find_root_person(conn, config)
    if not root_id:
        print(f"  Could not find root person for {family_name}")
        return False

    # Get person details
    cursor = conn.cursor()
    cursor.execute("SELECT forename, surname, birth_year_estimate FROM person WHERE id = ?", (root_id,))
    row = cursor.fetchone()
    print(f"  Root: {row[0]} {row[1]} (b. {row[2]}) - ID {root_id}")

    # Build tree
    root = get_descendants(conn, root_id)
    if not root:
        print(f"  Could not build tree for {family_name}")
        return False

    people_count = count_people(root)
    print(f"  People in tree: {people_count}")

    # Generate SVG
    generator = SVGGenerator()
    title = f"{config['surname']} Family Tree"
    svg = generator.generate(root, title)

    # Save
    output_path = output_dir / f"{family_name}.svg"
    output_path.write_text(svg)
    print(f"  Saved to: {output_path}")

    return True


def main():
    parser = argparse.ArgumentParser(description='Generate family tree SVGs')
    parser.add_argument('--family', help='Generate SVG for specific family only')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT,
                       help='Output directory for SVG files')
    parser.add_argument('--list', action='store_true', help='List available families')
    args = parser.parse_args()

    if args.list:
        print("Available families:")
        for name in FAMILY_CONFIGS:
            print(f"  - {name}")
        return

    conn = sqlite3.connect(DB_PATH)

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.family:
        generate_family_svg(conn, args.family.lower(), args.output_dir)
    else:
        # Generate all families
        print("Generating SVGs for all configured families...")
        for family_name in FAMILY_CONFIGS:
            generate_family_svg(conn, family_name, args.output_dir)

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
