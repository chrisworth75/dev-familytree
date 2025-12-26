#!/usr/bin/env python3
"""
Import family relationships from Ancestry trees.

Fetches each person's page and extracts Father/Mother IDs to build the family tree structure.

Usage:
    python import_tree_relationships.py TREE_ID [--limit N] [--headless]
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


def get_tree_persons_api(session, tree_id, limit=None):
    """Get all persons from a tree via API."""
    persons = []
    page = 1

    while True:
        url = f"{BASE_URL}/api/treesui-list/trees/{tree_id}/persons?page={page}"
        resp = session.get(url, timeout=30)

        if resp.status_code != 200:
            print(f"  Error fetching page {page}: {resp.status_code}")
            break

        data = resp.json()
        if not data:
            break

        for person in data:
            gid_data = person.get('gid', {})
            gid = gid_data.get('v', '') if isinstance(gid_data, dict) else str(gid_data)

            # Parse GID - format is "personId:something:treeId"
            if ':' in gid:
                parts = gid.split(':')
                ancestry_id = parts[0]
            else:
                ancestry_id = gid

            name_data = person.get('Names', [{}])[0]
            name = f"{name_data.get('g', '')} {name_data.get('s', '')}".strip()

            persons.append({
                'ancestry_id': ancestry_id,
                'name': name,
                'gid': gid
            })

            if limit and len(persons) >= limit:
                return persons

        print(f"  Page {page}: {len(data)} persons (total: {len(persons)})")
        page += 1

        if len(data) < 20:  # Less than page size means last page
            break

    return persons


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
    # Format: "SpouseList":[{"Id":123,"FullName":"Name",...}]
    spouses_match = re.search(r'"SpouseList":\[(.*?)\]', html)
    if spouses_match:
        spouses_json = spouses_match.group(1)
        # Extract individual spouse IDs
        for spouse_match in re.finditer(r'"Id":(\d+),"FullName":"([^"]+)"', spouses_json):
            family['spouses'].append({
                'id': spouse_match.group(1),
                'name': spouse_match.group(2)
            })

    return family


def fetch_person_family(session, tree_id, ancestry_person_id):
    """Fetch a person's page and extract family data."""
    url = f"{BASE_URL}/family-tree/person/tree/{tree_id}/person/{ancestry_person_id}"

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return extract_family_from_html(resp.text)
        else:
            return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def import_relationships(tree_id, limit=None, delay=0.5):
    """Import family relationships for a tree."""
    print(f"\n{'=' * 60}")
    print(f"IMPORTING FAMILY RELATIONSHIPS FOR TREE {tree_id}")
    print(f"{'=' * 60}")

    # Create session
    session = make_session()
    if not session.cookies:
        print("ERROR: No cookies found. Log into Ancestry in Chrome first.")
        return

    # Check if we need to get persons from API or use existing DB data
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check for existing tree
    cursor.execute("SELECT id, name FROM tree WHERE ancestry_tree_id = ?", (str(tree_id),))
    tree_row = cursor.fetchone()
    if tree_row:
        local_tree_id = tree_row[0]
        print(f"\nFound tree in DB: {tree_row[1]} (local ID: {local_tree_id})")
    else:
        print(f"\nTree {tree_id} not found in DB, will fetch from API")
        local_tree_id = None

    # Get persons to process
    print("\nFetching persons from Ancestry API...")
    persons = get_tree_persons_api(session, tree_id, limit)
    print(f"Found {len(persons)} persons to process")

    if not persons:
        print("No persons found")
        conn.close()
        return

    # Process each person
    imported = 0
    with_parents = 0
    with_spouses = 0
    errors = 0

    for i, person in enumerate(persons):
        ancestry_id = person['ancestry_id']
        name = person['name']

        print(f"\n[{i+1}/{len(persons)}] {name} (ID: {ancestry_id})", end='', flush=True)

        # Check if already imported
        cursor.execute(
            "SELECT id FROM tree_relationship WHERE tree_id = ? AND ancestry_person_id = ?",
            (tree_id, ancestry_id)
        )
        if cursor.fetchone():
            print(" - already imported", end='')
            continue

        # Fetch family data
        family = fetch_person_family(session, tree_id, ancestry_id)

        if family is None:
            print(" - ERROR fetching", end='')
            errors += 1
            continue

        # Store relationship
        spouse_ids = json.dumps([s['id'] for s in family['spouses']]) if family['spouses'] else None

        try:
            cursor.execute("""
                INSERT INTO tree_relationship
                (tree_id, ancestry_person_id, father_id, mother_id, spouse_ids)
                VALUES (?, ?, ?, ?, ?)
            """, (tree_id, ancestry_id, family['father_id'], family['mother_id'], spouse_ids))
            conn.commit()
            imported += 1

            # Status
            parts = []
            if family['father_id']:
                parts.append(f"F:{family['father_name']}")
                with_parents += 1
            if family['mother_id']:
                parts.append(f"M:{family['mother_name']}")
            if family['spouses']:
                parts.append(f"S:{len(family['spouses'])}")
                with_spouses += 1

            if parts:
                print(f" - {', '.join(parts)}", end='')
            else:
                print(" - no family links", end='')

        except sqlite3.IntegrityError:
            print(" - duplicate", end='')

        # Rate limiting
        time.sleep(delay)

    conn.close()

    print(f"\n\n{'=' * 60}")
    print("IMPORT COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Imported:     {imported}")
    print(f"  With parents: {with_parents}")
    print(f"  With spouses: {with_spouses}")
    print(f"  Errors:       {errors}")


def show_tree_stats(tree_id):
    """Show relationship statistics for a tree."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(father_id) as with_father,
            COUNT(mother_id) as with_mother,
            COUNT(spouse_ids) as with_spouse
        FROM tree_relationship
        WHERE tree_id = ?
    """, (tree_id,))

    row = cursor.fetchone()
    print(f"\nTree {tree_id} relationship stats:")
    print(f"  Total persons:    {row[0]}")
    print(f"  With father:      {row[1]}")
    print(f"  With mother:      {row[2]}")
    print(f"  With spouse(s):   {row[3]}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import Ancestry tree relationships")
    parser.add_argument("tree_id", help="Ancestry tree ID")
    parser.add_argument("--limit", type=int, help="Limit number of persons to process")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests (seconds)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    args = parser.parse_args()

    if args.stats:
        show_tree_stats(args.tree_id)
    else:
        import_relationships(args.tree_id, limit=args.limit, delay=args.delay)
        show_tree_stats(args.tree_id)


if __name__ == "__main__":
    main()
