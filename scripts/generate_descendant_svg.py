#!/usr/bin/env python3
"""
Generate an interactive SVG family tree from the genealogy database.
Starts from a specified ancestor and shows all descendants.
Uses staggered layout for siblings (older on top, younger below).
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

@dataclass
class Person:
    id: int
    forename: str
    surname: str
    birth_year: int | None
    death_year: int | None
    sex: str = "M"  # M or F
    children: list['Person'] = field(default_factory=list)
    spouse_name: str | None = None


FEMALE_NAMES = {'mary', 'alice', 'constance', 'blanche', 'evelyn', 'ethel', 'jane',
                'margaret', 'angela', 'janet', 'betty', 'susan', 'ann', 'elizabeth',
                'doris', 'marjorie', 'patricia', 'nina', 'rachel', 'verity', 'kathleen',
                'muriel', 'agnes', 'sarah', 'emma', 'lily', 'rose', 'irene', 'annie',
                'loreen', 'betsy', 'theodora', 'maria', 'ellen', 'elsie', 'grace',
                'rebecca', 'jennifer', 'helen', 'florence', 'mildred', 'harriet',
                'dorothy', 'edith', 'gladys', 'mabel', 'clara', 'charlotte', 'caroline',
                'catherine', 'kate', 'lucy', 'amy', 'julia', 'laura', 'eleanor', 'frances',
                'virginia', 'beatrice', 'lillian', 'hazel', 'gertrude', 'josephine', 'esther',
                'norah', 'miriam', 'hannah', 'ruth'}

MALE_NAMES = {'henry', 'leon', 'donald', 'reginald', 'leslie', 'arthur', 'william',
              'james', 'john', 'thomas', 'george', 'richard', 'david', 'peter', 'stephen',
              'kenneth', 'mervyn', 'albert', 'samuel', 'edmund', 'louis', 'lupton',
              'sydney', 'oliver', 'andrew', 'timothy', 'harry', 'frank', 'francis'}


def guess_sex(forename: str) -> str:
    """Guess sex from first name."""
    if not forename:
        return "M"
    first_name = forename.lower().split()[0]
    if first_name in FEMALE_NAMES:
        return "F"
    if first_name in MALE_NAMES:
        return "M"
    # Default to male if unknown
    return "M"


def get_descendants(conn, root_person_id: int, visited: set = None) -> Person | None:
    """Recursively fetch a person and all their descendants using mother_id/father_id."""
    if visited is None:
        visited = set()

    if root_person_id in visited:
        return None
    visited.add(root_person_id)

    cursor = conn.cursor()

    # Get person details
    cursor.execute("""
        SELECT id, forename, surname, birth_year_estimate, death_year_estimate
        FROM person WHERE id = ?
    """, (root_person_id,))
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

    # Get spouse (still using relationship table for this)
    cursor.execute("""
        SELECT p.forename, p.surname
        FROM relationship r
        JOIN person p ON (r.person_id_2 = p.id AND r.person_id_1 = ?)
                      OR (r.person_id_1 = p.id AND r.person_id_2 = ?)
        WHERE r.relationship_type = 'spouse'
        LIMIT 1
    """, (root_person_id, root_person_id))
    spouse_row = cursor.fetchone()
    if spouse_row:
        person.spouse_name = f"{spouse_row[0] or ''} {spouse_row[1] or ''}".strip()

    # Get children using the new mother_id/father_id columns
    cursor.execute("""
        SELECT DISTINCT id
        FROM person
        WHERE mother_id = ? OR father_id = ?
        ORDER BY birth_year_estimate
    """, (root_person_id, root_person_id))

    child_ids = [row[0] for row in cursor.fetchall()]

    for child_id in child_ids:
        child = get_descendants(conn, child_id, visited)
        if child:
            person.children.append(child)

    # Sort children by birth year
    person.children.sort(key=lambda c: c.birth_year or 9999)

    return person

def find_person_by_name(conn, forename_pattern: str, surname: str, birth_year: int = None) -> int | None:
    """Find a person ID by name pattern."""
    cursor = conn.cursor()
    query = """
        SELECT id, forename, surname, birth_year_estimate
        FROM person
        WHERE forename LIKE ? AND surname LIKE ?
    """
    params = [f"%{forename_pattern}%", f"%{surname}%"]

    if birth_year:
        query += " AND birth_year_estimate = ?"
        params.append(birth_year)

    query += " ORDER BY birth_year_estimate LIMIT 10"
    cursor.execute(query, params)

    rows = cursor.fetchall()
    if rows:
        # Prefer the one with most relationships (likely main record)
        for row in rows:
            cursor.execute("""
                SELECT COUNT(*) FROM relationship
                WHERE person_id_1 = ? OR person_id_2 = ?
            """, (row[0], row[0]))
            count = cursor.fetchone()[0]
            if count > 0:
                return row[0]
        return rows[0][0]
    return None


class SVGGenerator:
    """Generate SVG family tree with staggered sibling layout."""

    CARD_WIDTH = 160
    CARD_HEIGHT = 55  # Increased to fit spouse line
    CARD_SPACING_X = 20
    ROW_HEIGHT_SAME_GEN = 80  # Between older/younger rows in same gen
    GEN_HEIGHT = 170  # Between generations
    PADDING = 50

    def __init__(self):
        self.elements = []
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.max_y = 0
        self.person_positions = {}  # person_id -> (x, y)

    def generate(self, root: Person) -> str:
        """Generate SVG for the tree starting from root."""
        self.elements = []
        self.person_positions = {}

        # Do layout starting at x=0
        self._layout_person(root, x=0, y=80, gen=0)

        # Shift all coordinates so min_x becomes PADDING (all positive coords)
        shift_x = self.PADDING - self.min_x

        # Reset and redo layout with shift applied
        self.elements = []
        old_positions = self.person_positions.copy()
        self.person_positions = {}
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.max_y = 0

        # Redo layout with shifted starting position
        root_new_x = old_positions[root.id][0] + shift_x
        self._layout_person(root, x=root_new_x, y=80, gen=0)

        # Calculate dimensions - all coords are now positive
        width = self.max_x + self.PADDING
        height = self.max_y + self.PADDING

        # Store root center for the viewer
        root_center_x = self.person_positions[root.id][0] + self.CARD_WIDTH / 2

        # Build SVG - viewBox starts at 0 since all coords are positive
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
      .gen-label {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 10px; fill: #aaa; }}
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

  <!-- Title centered above root -->
  <text x="{root_center_x}" y="30" text-anchor="middle" class="name" style="font-size: 16px;">
    {root.forename} {root.surname} - Descendants
  </text>
  <text x="{root_center_x}" y="48" text-anchor="middle" class="dates">
    Generated from genealogy database
  </text>
  <line x1="30" y1="58" x2="{width - 30}" y2="58" stroke="#e0e0e0"/>

  {''.join(self.elements)}
</svg>'''
        return svg

    def _layout_person(self, person: Person, x: float, y: float, gen: int) -> float:
        """Layout a person and their descendants. Returns the width used."""
        self.person_positions[person.id] = (x, y)
        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x + self.CARD_WIDTH)
        self.max_y = max(self.max_y, y + self.CARD_HEIGHT)

        # Draw this person's card
        self._draw_person_card(person, x, y)

        if not person.children:
            return self.CARD_WIDTH

        # Calculate children layout with staggering
        num_children = len(person.children)

        if num_children == 1:
            # Single child - straight down
            child = person.children[0]
            child_y = y + self.GEN_HEIGHT
            child_width = self._layout_person(child, x, child_y, gen + 1)

            # Draw connector
            self._draw_connector(x + self.CARD_WIDTH/2, y + self.CARD_HEIGHT,
                               x + self.CARD_WIDTH/2, child_y, dashed=False)
            return max(self.CARD_WIDTH, child_width)

        # Multiple children - stagger older (top row) and younger (bottom row)
        # This keeps siblings close together while using vertical space
        older_children = person.children[::2]  # Even indices (0, 2, 4...)
        younger_children = person.children[1::2]  # Odd indices (1, 3, 5...)

        older_y = y + self.GEN_HEIGHT
        younger_y = y + self.GEN_HEIGHT + self.ROW_HEIGHT_SAME_GEN

        # Calculate widths for each row separately
        older_widths = [(child, self._estimate_subtree_width(child)) for child in older_children]
        younger_widths = [(child, self._estimate_subtree_width(child)) for child in younger_children]

        older_total = sum(w for _, w in older_widths) + max(0, len(older_widths) - 1) * self.CARD_SPACING_X
        younger_total = sum(w for _, w in younger_widths) + max(0, len(younger_widths) - 1) * self.CARD_SPACING_X

        # Use the wider row's width as base
        max_row_width = max(older_total, younger_total, self.CARD_WIDTH)

        # Center the parent's column
        parent_cx = x + self.CARD_WIDTH / 2

        # Layout older row (centered under parent)
        older_start_x = parent_cx - older_total / 2
        connector_points = []
        current_x = older_start_x
        for child, est_width in older_widths:
            actual_width = self._layout_person(child, current_x, older_y, gen + 1)
            connector_points.append((current_x + self.CARD_WIDTH/2, older_y, False))
            current_x += actual_width + self.CARD_SPACING_X

        # Layout younger row (centered, offset horizontally for stagger effect)
        younger_start_x = parent_cx - younger_total / 2
        current_x = younger_start_x
        for child, est_width in younger_widths:
            actual_width = self._layout_person(child, current_x, younger_y, gen + 1)
            connector_points.append((current_x + self.CARD_WIDTH/2, younger_y, True))
            current_x += actual_width + self.CARD_SPACING_X

        # Draw connectors
        parent_bottom = y + self.CARD_HEIGHT
        junction_y = y + self.CARD_HEIGHT + 30
        self._draw_connector(parent_cx, parent_bottom, parent_cx, junction_y, False)

        if connector_points:
            # Horizontal bar must span from leftmost child to rightmost child
            # AND include the parent's center point
            all_x_points = [p[0] for p in connector_points] + [parent_cx]
            min_x = min(all_x_points)
            max_x = max(all_x_points)
            self._draw_connector(min_x, junction_y, max_x, junction_y, False)

            for child_cx, child_y, dashed in connector_points:
                self._draw_connector(child_cx, junction_y, child_cx, child_y, dashed)

        # Calculate actual width used
        all_x = [p[0] for p in connector_points]
        if all_x:
            actual_width = max(all_x) - min(all_x) + self.CARD_WIDTH
        else:
            actual_width = self.CARD_WIDTH

        return max(self.CARD_WIDTH, actual_width)

    def _estimate_subtree_width(self, person: Person) -> float:
        """Estimate the width needed for a person's subtree."""
        if not person.children:
            return self.CARD_WIDTH

        total = 0
        for child in person.children:
            total += self._estimate_subtree_width(child) + self.CARD_SPACING_X
        return max(self.CARD_WIDTH, total - self.CARD_SPACING_X)

    def _draw_person_card(self, person: Person, x: float, y: float):
        """Draw a person card at the given position."""
        avatar_class = "avatar-female" if person.sex == "F" else "avatar-male"

        dates = ""
        if person.birth_year:
            dates = str(person.birth_year)
            if person.death_year:
                dates += f"-{person.death_year}"
            else:
                dates += "-"

        name = f"{person.forename} {person.surname}".strip()
        if not name or name == " ":
            name = "Private"
        elif len(name) > 22:
            name = name[:20] + "..."

        spouse_line = ""
        if person.spouse_name:
            spouse_short = person.spouse_name
            if len(spouse_short) > 20:
                spouse_short = spouse_short[:18] + "..."
            spouse_line = f'<text x="{x + 40}" y="{y + 47}" class="spouse">m. {spouse_short}</text>'

        card = f'''
  <g class="person-card" data-person-id="{person.id}">
    <rect x="{x}" y="{y}" width="{self.CARD_WIDTH}" height="{self.CARD_HEIGHT}" rx="5" class="card"/>
    <circle cx="{x + 20}" cy="{y + 28}" r="14" class="{avatar_class}"/>
    <text x="{x + 40}" y="{y + 20}" class="name">{name}</text>
    <text x="{x + 40}" y="{y + 33}" class="dates">{dates}</text>
    {spouse_line}
  </g>'''
        self.elements.append(card)

    def _draw_connector(self, x1: float, y1: float, x2: float, y2: float, dashed: bool):
        """Draw a connector line."""
        css_class = "connector-long" if dashed else "connector"
        self.elements.append(f'  <path d="M{x1} {y1} L{x2} {y2}" class="{css_class}"/>\n')


def find_hlw_children(conn) -> list[int]:
    """Find all children of Henry Lonsdale Wrathall from the database."""
    cursor = conn.cursor()

    # Known children of HLW with their approximate birth years
    # We'll look for people matching these and having parent-child relationships
    children_patterns = [
        ("Leon Earl", "Wrathall", 1886),
        ("Constance Mary", "%Wrathall", 1887),  # Matches Wrathall or Lonsdale-Wrathall
        ("Blanche", "Wrathall", 1889),
        ("Reginald", "Wrathall", 1891),
        ("Leslie Gordon", "Wrathall", 1904),
    ]

    child_ids = []
    for forename, surname, birth_year in children_patterns:
        cursor.execute("""
            SELECT DISTINCT p.id, p.forename, p.surname, p.birth_year_estimate,
                   (SELECT COUNT(*) FROM relationship r WHERE r.person_id_1 = p.id) as rel_count
            FROM person p
            WHERE p.forename LIKE ?
              AND p.surname LIKE ?
              AND p.birth_year_estimate BETWEEN ? AND ?
            ORDER BY rel_count DESC
            LIMIT 1
        """, (f"%{forename}%", f"%{surname}%", birth_year - 2, birth_year + 2))
        row = cursor.fetchone()
        if row and row[0] not in child_ids:
            child_ids.append(row[0])
            print(f"  Found child: {row[1]} {row[2]} ({row[3]}) - id={row[0]}")

    return child_ids


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Finding HLW's children from database...")
    child_ids = find_hlw_children(conn)

    if not child_ids:
        print("Could not find any children of HLW")
        return

    # Build the tree for each child
    print(f"\nBuilding descendant trees for {len(child_ids)} children...")
    hlw_children = []
    visited = set()  # Share visited set across all children to avoid duplicates

    for child_id in child_ids:
        child = get_descendants(conn, child_id, visited.copy())
        if child:
            hlw_children.append(child)
            desc_count = count_descendants(child)
            print(f"  {child.forename} {child.surname}: {desc_count} descendants")

    # Create HLW as the root
    hlw = Person(
        id=0,
        forename="Henry Lonsdale",
        surname="Wrathall",
        birth_year=1863,
        death_year=1927,
        sex="M",
        spouse_name="Mary Alice Metcalfe",
        children=hlw_children
    )

    # Sort children by birth year
    hlw.children.sort(key=lambda c: c.birth_year or 9999)

    total = count_descendants(hlw)
    print(f"\nTotal people in tree: {total}")

    # Generate SVG
    generator = SVGGenerator()
    svg = generator.generate(hlw)

    # Save to desktop
    output_path = Path.home() / "Desktop" / "wrathall-descendants.svg"
    output_path.write_text(svg)
    print(f"\nSVG saved to: {output_path}")

    conn.close()


def count_descendants(person: Person) -> int:
    """Count total people in a tree."""
    count = 1
    for child in person.children:
        count += count_descendants(child)
    return count


if __name__ == "__main__":
    main()
