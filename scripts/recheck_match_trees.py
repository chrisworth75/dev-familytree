#!/usr/bin/env python3
"""
Recheck DNA match trees for changes.

This script:
1. Checks all DNA matches for tree availability/size changes
2. Updates tree_check_date after each check
3. Flags trees that have grown or become public
4. Optionally re-imports trees that have changed

Usage:
    python recheck_match_trees.py [--min-cm 20] [--limit N] [--days-since 7] [--reimport]
"""

import sqlite3
import re
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

import browser_cookie3
from playwright.sync_api import sync_playwright

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
BASE_URL = "https://www.ancestry.co.uk"

# Your test GUID
MY_TEST_GUID = "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A"

# Your tree IDs to exclude when finding match trees
MY_TREE_IDS = {"193991232", "193798041"}


def get_cookies():
    """Get ancestry cookies from Chrome."""
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
    return cookie_list


def get_matches_to_check(min_cm=20, limit=None, days_since=None):
    """Get DNA matches that need tree checking."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Base query - get matches above threshold
    query = """
        SELECT id, ancestry_id, name, shared_cm, tree_size, has_tree,
               linked_tree_id, tree_check_date
        FROM dna_match
        WHERE ancestry_id IS NOT NULL
        AND shared_cm >= ?
    """
    params = [min_cm]

    # Filter by days since last check
    if days_since is not None:
        cutoff = (datetime.now() - timedelta(days=days_since)).strftime('%Y-%m-%d')
        query += " AND (tree_check_date IS NULL OR tree_check_date < ?)"
        params.append(cutoff)

    query += " ORDER BY shared_cm DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    matches = cursor.fetchall()
    conn.close()

    return matches


def check_match_tree(page, match_guid):
    """Check a match's tree availability and size.

    Returns: (has_tree, tree_id, tree_size, is_public)
    """
    trees_url = f"{BASE_URL}/discoveryui-matches/compare/{MY_TEST_GUID}/with/{match_guid}/trees"

    try:
        page.goto(trees_url, wait_until='networkidle', timeout=60000)
        time.sleep(1)

        html = page.content()

        # Find tree IDs, excluding our own trees
        all_tree_ids = set(re.findall(r'/family-tree/tree/(\d+)', html))
        tree_ids = [tid for tid in all_tree_ids if tid not in MY_TREE_IDS]

        if not tree_ids:
            # Check for "no tree" or "private tree" indicators
            if 'private' in html.lower() or 'not shared' in html.lower():
                return (True, None, 0, False)  # Has tree but private
            return (False, None, 0, False)  # No tree

        tree_id = tree_ids[0]

        # Try to get tree size from the page
        tree_size = 0
        size_match = re.search(r'(\d+)\s*(?:people|persons|members)', html, re.IGNORECASE)
        if size_match:
            tree_size = int(size_match.group(1))

        # Check if tree is accessible (public)
        is_public = True  # If we can see tree ID, it's accessible

        return (True, tree_id, tree_size, is_public)

    except Exception as e:
        print(f" Error: {e}", end='')
        return (None, None, None, None)  # Error - couldn't check


def update_match_tree_info(match_id, has_tree, tree_id, tree_size, is_public):
    """Update DNA match with current tree info."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("""
        UPDATE dna_match
        SET has_tree = ?,
            linked_tree_id = COALESCE(?, linked_tree_id),
            tree_size = COALESCE(?, tree_size),
            has_public_tree = ?,
            tree_check_date = ?
        WHERE id = ?
    """, (has_tree, tree_id, tree_size, is_public, today, match_id))

    # Also update ancestry_person_count on the tree table if we have this tree
    if tree_id and tree_size:
        cursor.execute("""
            UPDATE tree
            SET ancestry_person_count = ?
            WHERE ancestry_tree_id = ?
        """, (tree_size, tree_id))

    conn.commit()
    conn.close()


def get_ancestry_tree_size(tree_id):
    """Get the ancestry_person_count for a tree (what's on Ancestry, not local)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ancestry_person_count FROM tree WHERE ancestry_tree_id = ?
    """, (str(tree_id),))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def recheck_trees(min_cm=20, limit=None, days_since=7, delay=0.5, reimport=False):
    """Recheck all DNA match trees for changes."""
    print(f"\n{'=' * 60}")
    print("RECHECKING DNA MATCH TREES")
    print(f"{'=' * 60}")
    print(f"Min cM: {min_cm}")
    print(f"Days since last check: {days_since if days_since else 'all'}")
    print(f"Reimport changed: {reimport}")

    cookies = get_cookies()
    if not cookies:
        print("ERROR: No cookies found. Log into Ancestry in Chrome first.")
        return

    matches = get_matches_to_check(min_cm, limit, days_since)
    print(f"\nFound {len(matches)} matches to check")

    stats = {
        'checked': 0,
        'new_trees': 0,
        'grown_trees': 0,
        'now_public': 0,
        'errors': 0,
    }

    changes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()

        for i, (match_id, ancestry_id, name, cm, old_size, old_has_tree,
                old_tree_id, last_check) in enumerate(matches):

            print(f"\n[{i+1}/{len(matches)}] {name} ({cm:.1f} cM)", end='', flush=True)

            if last_check:
                print(f" [last: {last_check}]", end='')

            has_tree, tree_id, tree_size, is_public = check_match_tree(page, ancestry_id)

            if has_tree is None:
                stats['errors'] += 1
                continue

            stats['checked'] += 1

            # Detect changes
            change = None

            if has_tree and not old_has_tree:
                change = 'NEW_TREE'
                stats['new_trees'] += 1
                print(f" -> NEW TREE! (ID: {tree_id}, {tree_size} people)", end='')

            elif tree_id and not old_tree_id:
                change = 'NOW_PUBLIC'
                stats['now_public'] += 1
                print(f" -> NOW PUBLIC! (ID: {tree_id}, {tree_size} people)", end='')

            elif tree_size and old_size and tree_size > old_size:
                growth = tree_size - old_size
                change = 'GROWN'
                stats['grown_trees'] += 1
                print(f" -> GREW by {growth} (was {old_size}, now {tree_size})", end='')

            elif has_tree:
                size_str = f" ({tree_size} people)" if tree_size else ""
                print(f" -> OK{size_str}", end='')
            else:
                print(f" -> No tree", end='')

            # Record change
            if change:
                changes.append({
                    'match_id': match_id,
                    'name': name,
                    'cm': cm,
                    'change': change,
                    'old_size': old_size,
                    'new_size': tree_size,
                    'tree_id': tree_id,
                })

            # Update database
            update_match_tree_info(match_id, has_tree, tree_id, tree_size, is_public)

            time.sleep(delay)

        browser.close()

    # Summary
    print(f"\n\n{'=' * 60}")
    print("RECHECK COMPLETE")
    print(f"{'=' * 60}")
    print(f"Checked:      {stats['checked']}")
    print(f"New trees:    {stats['new_trees']}")
    print(f"Grown trees:  {stats['grown_trees']}")
    print(f"Now public:   {stats['now_public']}")
    print(f"Errors:       {stats['errors']}")

    if changes:
        print(f"\n{'=' * 60}")
        print("CHANGES DETECTED")
        print(f"{'=' * 60}")
        for c in changes:
            print(f"  {c['name']} ({c['cm']:.1f} cM): {c['change']}")
            if c['change'] == 'GROWN':
                print(f"    {c['old_size']} -> {c['new_size']} people")
            if c['tree_id']:
                print(f"    Tree ID: {c['tree_id']}")

        # Reimport if requested
        if reimport and changes:
            print(f"\n{'=' * 60}")
            print("REIMPORTING CHANGED TREES")
            print(f"{'=' * 60}")
            from import_ancestry_tree import import_tree

            for c in changes:
                if c['tree_id']:
                    print(f"\nReimporting {c['name']} tree {c['tree_id']}...")
                    try:
                        import_tree(c['tree_id'], delay=delay)
                    except Exception as e:
                        print(f"  Error: {e}")


def show_check_status(min_cm=20):
    """Show tree check status for matches."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            CASE
                WHEN tree_check_date IS NULL THEN 'Never checked'
                WHEN tree_check_date >= date('now', '-7 days') THEN 'Last 7 days'
                WHEN tree_check_date >= date('now', '-30 days') THEN 'Last 30 days'
                ELSE 'Over 30 days ago'
            END as status,
            COUNT(*) as count
        FROM dna_match
        WHERE shared_cm >= ?
        GROUP BY status
        ORDER BY count DESC
    """, (min_cm,))

    print(f"\nTree check status (matches >= {min_cm} cM):")
    print("-" * 40)
    for status, count in cursor.fetchall():
        print(f"  {status}: {count}")

    # Show matches never checked
    cursor.execute("""
        SELECT name, shared_cm, has_tree, tree_size
        FROM dna_match
        WHERE shared_cm >= ?
        AND tree_check_date IS NULL
        ORDER BY shared_cm DESC
        LIMIT 20
    """, (min_cm,))

    print(f"\nTop unchecked matches:")
    print(f"{'Name':<30} {'cM':>8} {'Has Tree':>10} {'Size':>8}")
    print("-" * 60)
    for name, cm, has_tree, size in cursor.fetchall():
        has_str = 'Yes' if has_tree else 'No'
        size_str = str(size) if size else '-'
        print(f"{name:<30} {cm:>8.1f} {has_str:>10} {size_str:>8}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Recheck DNA match trees for changes")
    parser.add_argument("--min-cm", type=float, default=20, help="Minimum cM (default 20)")
    parser.add_argument("--limit", type=int, help="Limit number to check")
    parser.add_argument("--days-since", type=int, default=7,
                        help="Only check if not checked in N days (default 7, 0=all)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    parser.add_argument("--reimport", action="store_true",
                        help="Reimport trees that have changed")
    parser.add_argument("--status", action="store_true", help="Show check status only")
    args = parser.parse_args()

    if args.status:
        show_check_status(args.min_cm)
    else:
        days = args.days_since if args.days_since > 0 else None
        recheck_trees(args.min_cm, args.limit, days, args.delay, args.reimport)


if __name__ == "__main__":
    main()
