#!/usr/bin/env python3
"""
Import Ancestry tree with people AND relationships.

This script:
1. Fetches all persons from a tree via API
2. Stores each person with their ancestry_person_id
3. Fetches each person's page to get parent/spouse relationships
4. Stores relationships in tree_relationship table

Usage:
    python import_ancestry_tree.py TREE_ID [--limit N] [--delay 0.5]
"""

import sqlite3
import json
import re
import time
import sys
import argparse
from pathlib import Path
from datetime import datetime

import requests
import browser_cookie3

DB_PATH = Path(__file__).parent / "genealogy.db"
BASE_URL = "https://www.ancestry.co.uk"


def get_cookies():
    """Get ancestry cookies from Chrome."""
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append(cookie)
        except:
            pass
    return cookie_list


def make_session():
    """Create authenticated session."""
    session = requests.Session()
    cookies = get_cookies()
    for c in cookies:
        session.cookies.set(c.name, c.value, domain=c.domain)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def get_or_create_tree(cursor, ancestry_tree_id, owner_name=None):
    """Get or create a tree record."""
    cursor.execute(
        "SELECT id FROM tree WHERE ancestry_tree_id = ?",
        (str(ancestry_tree_id),)
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute("""
        INSERT INTO tree (name, ancestry_tree_id, owner_name, created_at)
        VALUES (?, ?, ?, ?)
    """, (f"Tree {ancestry_tree_id}", str(ancestry_tree_id), owner_name, datetime.now().isoformat()))
    return cursor.lastrowid


def parse_person_from_api(person_data):
    """Parse person data from API response."""
    gid_data = person_data.get('gid', {})
    gid = gid_data.get('v', '') if isinstance(gid_data, dict) else str(gid_data)

    # Parse GID - format is "personId:something:treeId"
    if ':' in gid:
        parts = gid.split(':')
        ancestry_id = parts[0]
    else:
        ancestry_id = gid

    # Name
    name_data = person_data.get('Names', [{}])[0]
    given_name = name_data.get('g', '')
    surname = name_data.get('s', '')
    name = f"{given_name} {surname}".strip() or "Unknown"

    # Gender
    gender_data = person_data.get('Genders', [{}])[0]
    gender = gender_data.get('g', '')

    # Events (birth/death)
    birth_year = None
    birth_place = None
    death_year = None

    for event in person_data.get('Events', []):
        event_type = event.get('t', '').lower()
        if event_type == 'birth':
            # Parse date like "1925-05-16" or "16th may 1925"
            nd = event.get('nd', '')  # normalized date
            if nd and '-' in nd:
                try:
                    birth_year = int(nd.split('-')[0])
                except:
                    pass
            birth_place = event.get('p', '')
        elif event_type == 'death':
            nd = event.get('nd', '')
            if nd and '-' in nd:
                try:
                    death_year = int(nd.split('-')[0])
                except:
                    pass

    return {
        'ancestry_id': ancestry_id,
        'name': name,
        'gender': gender,
        'birth_year': birth_year,
        'birth_place': birth_place,
        'death_year': death_year,
    }


def extract_family_from_html(html):
    """Extract Father/Mother/Spouse IDs from person page HTML."""
    family = {
        'father_id': None,
        'father_name': None,
        'mother_id': None,
        'mother_name': None,
        'spouses': [],
    }

    # Extract Father
    father_match = re.search(r'"Father":\{"Id":(\d+),"FullName":"([^"]+)"', html)
    if father_match:
        family['father_id'] = father_match.group(1)
        family['father_name'] = father_match.group(2)

    # Extract Mother
    mother_match = re.search(r'"Mother":\{"Id":(\d+),"FullName":"([^"]+)"', html)
    if mother_match:
        family['mother_id'] = mother_match.group(1)
        family['mother_name'] = mother_match.group(2)

    # Extract Spouses from SpouseList
    spouses_match = re.search(r'"SpouseList":\[(.*?)\]', html)
    if spouses_match:
        spouses_json = spouses_match.group(1)
        for spouse_match in re.finditer(r'"Id":(\d+),"FullName":"([^"]+)"', spouses_json):
            family['spouses'].append({
                'id': spouse_match.group(1),
                'name': spouse_match.group(2)
            })

    return family


def import_tree(ancestry_tree_id, limit=None, delay=0.5, skip_existing=True, max_size=None):
    """Import a complete tree with people and relationships.

    Args:
        max_size: If set, abort if tree has more than this many people.
    """
    print(f"\n{'=' * 60}")
    print(f"IMPORTING ANCESTRY TREE {ancestry_tree_id}")
    print(f"{'=' * 60}")

    # Create session
    session = make_session()
    if not session.cookies:
        print("ERROR: No cookies found. Log into Ancestry in Chrome first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get or create tree
    tree_id = get_or_create_tree(cursor, ancestry_tree_id)
    print(f"Local tree ID: {tree_id}")

    # Check existing count
    cursor.execute("SELECT COUNT(*) FROM person WHERE tree_id = ? AND ancestry_person_id IS NOT NULL", (tree_id,))
    existing_with_ids = cursor.fetchone()[0]
    print(f"Existing persons with ancestry_id: {existing_with_ids}")

    # Fetch all persons from API
    print("\nFetching persons from Ancestry API...")
    persons = []
    page = 1

    while True:
        url = f"{BASE_URL}/api/treesui-list/trees/{ancestry_tree_id}/persons?page={page}"
        resp = session.get(url, timeout=30)

        if resp.status_code != 200:
            print(f"  Error fetching page {page}: {resp.status_code}")
            break

        data = resp.json()
        if not data:
            break

        for p in data:
            persons.append(parse_person_from_api(p))

        print(f"  Page {page}: {len(data)} persons (total: {len(persons)})")
        page += 1

        if limit and len(persons) >= limit:
            persons = persons[:limit]
            break

        if len(data) < 20:
            break

    print(f"\nTotal persons to import: {len(persons)}")

    # Check if tree is too large
    if max_size and len(persons) > max_size:
        print(f"\nABORTING: Tree has {len(persons)} people, exceeds max_size of {max_size}")
        conn.close()
        return False

    # Import persons and relationships
    imported_persons = 0
    imported_rels = 0
    skipped = 0

    for i, person in enumerate(persons):
        ancestry_id = person['ancestry_id']
        name = person['name']

        # Check if already exists with ancestry_id
        if skip_existing:
            cursor.execute(
                "SELECT id FROM person WHERE tree_id = ? AND ancestry_person_id = ?",
                (tree_id, ancestry_id)
            )
            if cursor.fetchone():
                skipped += 1
                continue

        print(f"\n[{i+1}/{len(persons)}] {name}", end='', flush=True)

        # Insert or update person
        cursor.execute("""
            INSERT INTO person (name, birth_year_estimate, birth_place, death_year, tree_id, ancestry_person_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET ancestry_person_id = excluded.ancestry_person_id
        """, (
            person['name'],
            person['birth_year'],
            person['birth_place'],
            person['death_year'],
            tree_id,
            ancestry_id
        ))
        imported_persons += 1

        # Fetch relationships from person page
        person_url = f"{BASE_URL}/family-tree/person/tree/{ancestry_tree_id}/person/{ancestry_id}"
        try:
            resp = session.get(person_url, timeout=30)
            if resp.status_code == 200:
                family = extract_family_from_html(resp.text)

                # Store relationship
                spouse_ids = json.dumps([s['id'] for s in family['spouses']]) if family['spouses'] else None

                cursor.execute("""
                    INSERT OR REPLACE INTO tree_relationship
                    (tree_id, ancestry_person_id, father_id, mother_id, spouse_ids)
                    VALUES (?, ?, ?, ?, ?)
                """, (ancestry_tree_id, ancestry_id, family['father_id'], family['mother_id'], spouse_ids))
                imported_rels += 1

                # Status
                parts = []
                if family['father_id']:
                    parts.append(f"F")
                if family['mother_id']:
                    parts.append(f"M")
                if family['spouses']:
                    parts.append(f"S:{len(family['spouses'])}")
                if parts:
                    print(f" [{','.join(parts)}]", end='')

        except Exception as e:
            print(f" [ERR: {e}]", end='')

        # Commit periodically
        if imported_persons % 50 == 0:
            conn.commit()

        time.sleep(delay)

    conn.commit()

    # Update tree person count
    cursor.execute("SELECT COUNT(*) FROM person WHERE tree_id = ?", (tree_id,))
    total_persons = cursor.fetchone()[0]
    cursor.execute("UPDATE tree SET person_count = ? WHERE id = ?", (total_persons, tree_id))
    conn.commit()
    conn.close()

    print(f"\n\n{'=' * 60}")
    print("IMPORT COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Persons imported:       {imported_persons}")
    print(f"  Relationships imported: {imported_rels}")
    print(f"  Skipped (existing):     {skipped}")
    print(f"  Total in tree:          {total_persons}")


def show_stats(ancestry_tree_id):
    """Show import statistics for a tree."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.id, t.name, t.person_count,
               (SELECT COUNT(*) FROM person WHERE tree_id = t.id) as actual_persons,
               (SELECT COUNT(*) FROM person WHERE tree_id = t.id AND ancestry_person_id IS NOT NULL) as with_ancestry_id,
               (SELECT COUNT(*) FROM tree_relationship WHERE tree_id = ?) as relationships
        FROM tree t
        WHERE t.ancestry_tree_id = ?
    """, (ancestry_tree_id, str(ancestry_tree_id)))

    row = cursor.fetchone()
    if row:
        print(f"\nTree {ancestry_tree_id} stats:")
        print(f"  Local ID:          {row[0]}")
        print(f"  Name:              {row[1]}")
        print(f"  Persons:           {row[3]}")
        print(f"  With Ancestry ID:  {row[4]}")
        print(f"  Relationships:     {row[5]}")
    else:
        print(f"Tree {ancestry_tree_id} not found in database")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import Ancestry tree with relationships")
    parser.add_argument("tree_id", help="Ancestry tree ID")
    parser.add_argument("--limit", type=int, help="Limit number of persons")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    parser.add_argument("--max-size", type=int, help="Abort if tree exceeds this many persons")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--force", action="store_true", help="Re-import existing persons")
    args = parser.parse_args()

    if args.stats:
        show_stats(args.tree_id)
    else:
        import_tree(args.tree_id, limit=args.limit, delay=args.delay,
                    skip_existing=not args.force, max_size=args.max_size)
        show_stats(args.tree_id)


if __name__ == "__main__":
    main()
