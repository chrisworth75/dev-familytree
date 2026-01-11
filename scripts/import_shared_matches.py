#!/usr/bin/env python3
"""
Import shared matches between DNA matches.

For each of your DNA matches, this fetches who they share DNA with
(and how much cM), which helps with clustering and finding common ancestors.

Usage:
    python import_shared_matches.py [--limit N] [--min-cm 20] [--delay 0.5]
"""

import sqlite3
import json
import re
import time
import sys
import argparse
from pathlib import Path
from datetime import datetime

import browser_cookie3
from playwright.sync_api import sync_playwright

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
BASE_URL = "https://www.ancestry.co.uk"

# Your test GUID
MY_TEST_GUID = "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A"


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


def get_matches_to_process(min_cm=20, limit=None):
    """Get DNA matches that need shared match data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get matches ordered by cM, prioritizing those with fewer shared matches
    cursor.execute("""
        SELECT dm.id, dm.ancestry_id, dm.name, dm.shared_cm,
               (SELECT COUNT(*) FROM shared_match sm WHERE sm.match1_id = dm.id) as existing_shared
        FROM dna_match dm
        WHERE dm.ancestry_id IS NOT NULL
        AND dm.shared_cm >= ?
        ORDER BY dm.shared_cm DESC
    """, (min_cm,))

    matches = cursor.fetchall()
    conn.close()

    if limit:
        matches = matches[:limit]

    return matches


def fetch_shared_matches(page, match_guid, match_name):
    """Fetch all shared matches for a DNA match."""
    shared_url = f"{BASE_URL}/discoveryui-matches/compare/{MY_TEST_GUID}/with/{match_guid}/sharedmatches"

    shared_matches = []

    try:
        page.goto(shared_url, wait_until='networkidle', timeout=60000)
        time.sleep(2)

        # Check for error page
        content = page.content()
        if "no longer available" in content.lower() or "sorry" in content.lower():
            return []

        # Scroll to load all matches (they lazy load)
        last_count = 0
        scroll_attempts = 0
        max_scrolls = 20

        while scroll_attempts < max_scrolls:
            # Count current matches
            match_cards = page.query_selector_all('[data-testid="match-card"], .matchCard, .match-card, [class*="MatchCard"]')
            current_count = len(match_cards)

            if current_count == last_count:
                scroll_attempts += 1
                if scroll_attempts >= 3:
                    break
            else:
                scroll_attempts = 0
                last_count = current_count

            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

        # Now extract the data
        # Try to get from page content/JSON
        content = page.content()

        # Method 1: Look for match data in the HTML
        # Pattern: name followed by cM value
        body_text = page.inner_text('body')

        # Split by lines and look for patterns
        lines = body_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for cM values
            cm_match = re.match(r'^(\d+\.?\d*)\s*cM', line)
            if cm_match:
                cm_value = float(cm_match.group(1))
                # Look backwards for name (usually 1-3 lines before)
                name = None
                for j in range(1, 4):
                    if i - j >= 0:
                        potential_name = lines[i - j].strip()
                        # Name should be non-empty, not a cM value, not too long
                        if (potential_name and
                            not re.match(r'^\d+\.?\d*\s*cM', potential_name) and
                            len(potential_name) < 50 and
                            len(potential_name) > 1 and
                            not potential_name.startswith('Shared') and
                            not potential_name.startswith('View')):
                            name = potential_name
                            break

                if name and cm_value > 0:
                    shared_matches.append({
                        'name': name,
                        'shared_cm': cm_value
                    })
            i += 1

        # Method 2: Try to extract from JSON in page
        json_matches = re.findall(r'"displayName"\s*:\s*"([^"]+)"[^}]*"sharedCentimorgans"\s*:\s*(\d+\.?\d*)', content)
        for name, cm in json_matches:
            cm_val = float(cm)
            # Avoid duplicates
            if not any(m['name'] == name for m in shared_matches):
                shared_matches.append({
                    'name': name,
                    'shared_cm': cm_val
                })

        # Alternative JSON pattern
        json_matches2 = re.findall(r'"sharedCentimorgans"\s*:\s*(\d+\.?\d*)[^}]*"displayName"\s*:\s*"([^"]+)"', content)
        for cm, name in json_matches2:
            cm_val = float(cm)
            if not any(m['name'] == name for m in shared_matches):
                shared_matches.append({
                    'name': name,
                    'shared_cm': cm_val
                })

    except Exception as e:
        print(f" [ERR: {e}]", end='')

    return shared_matches


def save_shared_matches(match_id, match_name, shared_matches):
    """Save shared matches to database."""
    if not shared_matches:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    saved = 0
    for sm in shared_matches:
        try:
            # Check if match2 exists in our database
            cursor.execute(
                "SELECT id, shared_cm FROM dna_match WHERE name = ?",
                (sm['name'],)
            )
            match2_row = cursor.fetchone()
            match2_id = match2_row[0] if match2_row else None
            you_to_match2_cm = match2_row[1] if match2_row else None

            # Insert or update
            cursor.execute("""
                INSERT INTO shared_match (match1_id, match2_id, match2_name, match1_to_match2_cm, you_to_match2_cm)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(match1_id, match2_name) DO UPDATE SET
                    match1_to_match2_cm = excluded.match1_to_match2_cm,
                    match2_id = COALESCE(excluded.match2_id, match2_id)
            """, (match_id, match2_id, sm['name'], sm['shared_cm'], you_to_match2_cm))
            saved += 1

        except Exception as e:
            print(f" [DB ERR: {e}]", end='')

    conn.commit()
    conn.close()
    return saved


def import_shared_matches(min_cm=20, limit=None, delay=0.5, skip_existing=True, min_new=5):
    """Import shared matches for DNA matches."""
    print(f"\n{'=' * 60}")
    print("IMPORTING SHARED MATCHES")
    print(f"{'=' * 60}")

    cookies = get_cookies()
    if not cookies:
        print("ERROR: No cookies found. Log into Ancestry in Chrome first.")
        return

    matches = get_matches_to_process(min_cm, limit)
    print(f"Found {len(matches)} matches >= {min_cm} cM")

    if skip_existing:
        # Filter to those with fewer shared matches than expected
        matches = [m for m in matches if m[4] < min_new]
        print(f"After filtering (need at least {min_new} new): {len(matches)} matches")

    if not matches:
        print("No matches need processing!")
        return

    total_saved = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()

        for i, (match_id, ancestry_id, name, cm, existing) in enumerate(matches):
            print(f"\n[{i+1}/{len(matches)}] {name} ({cm:.1f} cM, existing: {existing})", end='', flush=True)

            shared = fetch_shared_matches(page, ancestry_id, name)

            if shared:
                saved = save_shared_matches(match_id, name, shared)
                print(f" -> {len(shared)} found, {saved} saved", end='')
                total_saved += saved
            else:
                print(f" -> no shared matches", end='')

            time.sleep(delay)

        browser.close()

    print(f"\n\n{'=' * 60}")
    print(f"IMPORT COMPLETE: {total_saved} shared match records saved")
    print(f"{'=' * 60}")


def show_stats():
    """Show current shared match statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM dna_match")
    total_matches = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shared_match")
    total_shared = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT match1_id) FROM shared_match")
    matches_with_shared = cursor.fetchone()[0]

    cursor.execute("""
        SELECT dm.name, dm.shared_cm, COUNT(sm.id) as shared_count
        FROM dna_match dm
        LEFT JOIN shared_match sm ON sm.match1_id = dm.id
        GROUP BY dm.id
        ORDER BY dm.shared_cm DESC
        LIMIT 20
    """)
    top_matches = cursor.fetchall()

    print(f"\n{'=' * 60}")
    print("SHARED MATCH STATISTICS")
    print(f"{'=' * 60}")
    print(f"Total DNA matches:        {total_matches}")
    print(f"Matches with shared data: {matches_with_shared} ({100*matches_with_shared/total_matches:.1f}%)")
    print(f"Total shared records:     {total_shared}")

    print(f"\n{'Name':<25} {'cM':>8} {'Shared':>8}")
    print("-" * 45)
    for name, cm, count in top_matches:
        print(f"{name[:25]:<25} {cm:>8.1f} {count:>8}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import shared matches from Ancestry")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--limit", type=int, help="Limit number of matches to process")
    parser.add_argument("--min-cm", type=float, default=20, help="Minimum cM (default 20)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests")
    parser.add_argument("--force", action="store_true", help="Process all matches, even with existing data")
    parser.add_argument("--min-new", type=int, default=5, help="Only process if fewer than N shared matches exist")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        import_shared_matches(
            min_cm=args.min_cm,
            limit=args.limit,
            delay=args.delay,
            skip_existing=not args.force,
            min_new=args.min_new
        )
        show_stats()


if __name__ == "__main__":
    main()
