#!/usr/bin/env python3
"""
Import trees from DNA matches.

This script:
1. Finds DNA matches with linked trees
2. Gets their tree IDs from Ancestry
3. Imports those trees with people and relationships
4. Links the tree to the DNA match in the database

Usage:
    python import_match_trees.py [--limit N] [--min-cm 20] [--delay 0.5]
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

# Your test GUID (from notes)
MY_TEST_GUID = "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A"


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


def get_match_tree_ids_playwright(page, match_guid):
    """Get tree IDs for a DNA match using Playwright."""
    trees_url = f"{BASE_URL}/discoveryui-matches/compare/{MY_TEST_GUID}/with/{match_guid}/trees"

    try:
        page.goto(trees_url, wait_until='networkidle', timeout=60000)
        time.sleep(1)

        html = page.content()

        # Find all tree IDs in links
        tree_ids = list(set(re.findall(r'/family-tree/tree/(\d+)', html)))

        return tree_ids

    except Exception as e:
        print(f" Error: {e}", end='')
        return []


def add_tree_id_column():
    """Add tree_id column to dna_match if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE dna_match ADD COLUMN linked_tree_id TEXT")
        conn.commit()
    except:
        pass  # Column already exists
    conn.close()


def get_matches_to_process(min_cm=20, limit=None):
    """Get DNA matches with trees that we haven't processed yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT id, ancestry_id, name, shared_cm, tree_size
        FROM dna_match
        WHERE has_tree = 1
        AND ancestry_id IS NOT NULL
        AND shared_cm >= ?
        AND (linked_tree_id IS NULL OR linked_tree_id = '')
        ORDER BY shared_cm DESC
    """
    params = [min_cm]

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    matches = cursor.fetchall()
    conn.close()

    return matches


def update_match_tree_id(match_id, tree_id):
    """Update the linked_tree_id for a DNA match."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE dna_match SET linked_tree_id = ? WHERE id = ?",
        (tree_id, match_id)
    )
    conn.commit()
    conn.close()


def import_tree(session, ancestry_tree_id, dna_match_id, delay=0.5):
    """Import a tree with people and relationships."""
    from import_ancestry_tree import import_tree as do_import

    # This will use the existing import function
    # We just need to also link the tree to the DNA match

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if tree already imported
    cursor.execute(
        "SELECT id FROM tree WHERE ancestry_tree_id = ?",
        (str(ancestry_tree_id),)
    )
    existing = cursor.fetchone()

    if existing:
        tree_id = existing[0]
        # Just link to DNA match
        cursor.execute(
            "UPDATE tree SET dna_match_id = ? WHERE id = ?",
            (dna_match_id, tree_id)
        )
        conn.commit()
        conn.close()
        return tree_id, "already_imported"

    conn.close()

    # Import the tree
    do_import(ancestry_tree_id, delay=delay)

    # Link to DNA match
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tree SET dna_match_id = ? WHERE ancestry_tree_id = ?",
        (dna_match_id, str(ancestry_tree_id))
    )
    cursor.execute(
        "SELECT id FROM tree WHERE ancestry_tree_id = ?",
        (str(ancestry_tree_id),)
    )
    row = cursor.fetchone()
    tree_id = row[0] if row else None
    conn.commit()
    conn.close()

    return tree_id, "imported"


def discover_tree_ids(min_cm=20, limit=None, delay=0.3):
    """Discover tree IDs for DNA matches using Playwright."""
    from playwright.sync_api import sync_playwright

    print(f"\n{'=' * 60}")
    print("DISCOVERING TREE IDs FOR DNA MATCHES")
    print(f"{'=' * 60}")

    add_tree_id_column()

    # Get cookies
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for c in cookies:
                cookie_list.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path,
                    "secure": bool(c.secure),
                })
        except:
            pass

    if not cookie_list:
        print("ERROR: No cookies found. Log into Ancestry in Chrome first.")
        return

    matches = get_matches_to_process(min_cm, limit)
    print(f"Found {len(matches)} matches to check (>= {min_cm} cM)")

    found = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        for i, (match_id, ancestry_id, name, cm, tree_size) in enumerate(matches):
            print(f"\n[{i+1}/{len(matches)}] {name} ({cm:.1f} cM)", end='', flush=True)

            tree_ids = get_match_tree_ids_playwright(page, ancestry_id)

            if tree_ids:
                # Store first tree ID (primary tree)
                tree_id = tree_ids[0]
                update_match_tree_id(match_id, tree_id)
                print(f" -> Tree {tree_id}", end='')
                if len(tree_ids) > 1:
                    print(f" (+{len(tree_ids)-1} more)", end='')
                found += 1
            else:
                print(" -> No tree found", end='')

            time.sleep(delay)

        browser.close()

    print(f"\n\n{'=' * 60}")
    print(f"DISCOVERY COMPLETE: Found {found}/{len(matches)} tree IDs")
    print(f"{'=' * 60}")


def import_match_trees(min_cm=20, limit=None, max_tree_size=5000, delay=0.5):
    """Import trees from DNA matches."""
    print(f"\n{'=' * 60}")
    print("IMPORTING TREES FROM DNA MATCHES")
    print(f"{'=' * 60}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get matches with tree IDs that haven't been imported
    cursor.execute("""
        SELECT dm.id, dm.ancestry_id, dm.name, dm.shared_cm, dm.linked_tree_id, dm.tree_size
        FROM dna_match dm
        WHERE dm.linked_tree_id IS NOT NULL
        AND dm.linked_tree_id != ''
        AND dm.shared_cm >= ?
        AND NOT EXISTS (
            SELECT 1 FROM tree t WHERE t.ancestry_tree_id = dm.linked_tree_id
        )
        ORDER BY dm.shared_cm DESC
    """, (min_cm,))

    matches = cursor.fetchall()
    conn.close()

    if limit:
        matches = matches[:limit]

    print(f"Found {len(matches)} trees to import")

    # Filter by tree size
    filtered = []
    for m in matches:
        tree_size = m[5] or 0
        if tree_size <= max_tree_size:
            filtered.append(m)
        else:
            print(f"  Skipping {m[2]} - tree too large ({tree_size} people)")

    matches = filtered
    print(f"After size filter: {len(matches)} trees")

    for i, (match_id, ancestry_id, name, cm, tree_id, tree_size) in enumerate(matches):
        print(f"\n{'=' * 60}")
        print(f"[{i+1}/{len(matches)}] {name} ({cm:.1f} cM) - Tree {tree_id}")
        print(f"{'=' * 60}")

        local_tree_id, status = import_tree(None, tree_id, match_id, delay)
        print(f"  Status: {status}, Local tree ID: {local_tree_id}")


def show_matches_with_trees():
    """Show DNA matches and their tree status."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT dm.name, dm.shared_cm, dm.tree_size, dm.linked_tree_id,
               t.id as local_tree_id, t.person_count
        FROM dna_match dm
        LEFT JOIN tree t ON t.ancestry_tree_id = dm.linked_tree_id
        WHERE dm.has_tree = 1 AND dm.shared_cm >= 20
        ORDER BY dm.shared_cm DESC
        LIMIT 30
    """)

    print(f"\n{'Name':<25} {'cM':>8} {'Tree Size':>10} {'Tree ID':>12} {'Imported':>10}")
    print("-" * 75)

    for row in cursor.fetchall():
        name, cm, size, tree_id, local_id, imported_count = row
        imported = f"Yes ({imported_count})" if local_id else "No"
        tree_id_str = tree_id or "-"
        size_str = str(size) if size else "-"
        print(f"{name:<25} {cm:>8.1f} {size_str:>10} {tree_id_str:>12} {imported:>10}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import trees from DNA matches")
    parser.add_argument("--discover", action="store_true", help="Discover tree IDs for matches")
    parser.add_argument("--import-trees", action="store_true", help="Import discovered trees")
    parser.add_argument("--show", action="store_true", help="Show match tree status")
    parser.add_argument("--limit", type=int, help="Limit number to process")
    parser.add_argument("--min-cm", type=float, default=20, help="Minimum cM (default 20)")
    parser.add_argument("--max-tree-size", type=int, default=5000, help="Max tree size to import")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests")
    args = parser.parse_args()

    if args.show:
        show_matches_with_trees()
    elif args.discover:
        discover_tree_ids(args.min_cm, args.limit, args.delay)
    elif args.import_trees:
        import_match_trees(args.min_cm, args.limit, args.max_tree_size, args.delay)
    else:
        # Default: show status
        show_matches_with_trees()


if __name__ == "__main__":
    main()
