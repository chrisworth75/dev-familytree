#!/usr/bin/env python3
"""
Ancestry DNA Match Importer
Pulls all DNA matches from Ancestry.com and imports into local SQLite database.

Usage:
    1. Log into Ancestry.com in Chrome (then close the browser)
    2. Activate venv: source venv/bin/activate
    3. Run: python ancestry_import.py --browser   (uses Playwright to scrape all matches)
       Or:  python ancestry_import.py             (uses API, limited to 200 matches)
"""

import sqlite3
import json
import sys
import time
import re
import os
from datetime import datetime
from pathlib import Path

import requests
import browser_cookie3

# Configuration
DB_PATH = Path(__file__).parent / "genealogy.db"
ANCESTRY_BASE_URL = "https://www.ancestry.co.uk"
CHROME_USER_DATA = Path.home() / "Library/Application Support/Google/Chrome"


def fetch_matches_with_browser(test_guid=None, headless=False):
    """
    Use Playwright to scrape DNA matches from Ancestry website.
    This bypasses the 200-match API limit by using actual browser automation.

    Args:
        test_guid: Optional test GUID (will be auto-detected if not provided)
        headless: Run browser in headless mode (default False so you can see it working)

    Returns:
        List of match dictionaries
    """
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("BROWSER AUTOMATION MODE (Playwright)")
    print("=" * 60)

    matches = []

    # Get cookies from browser first
    print("\nExtracting cookies from Chrome...", flush=True)
    cookie_list = []

    # Try both .co.uk and .com domains
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": bool(cookie.secure),
                })
        except Exception as e:
            print(f"  Warning: {domain}: {e}")

    print(f"  Found {len(cookie_list)} Ancestry cookies", flush=True)

    if len(cookie_list) == 0:
        print("\n" + "=" * 60)
        print("NO COOKIES FOUND!")
        print("=" * 60)
        print("\nPlease:")
        print("  1. Open Chrome")
        print("  2. Go to https://www.ancestry.co.uk and LOG IN")
        print("  3. CLOSE Chrome completely (Cmd+Q)")
        print("  4. Run this script again")
        print("\nNote: Cookies may have been cleared by a previous run.")
        return []

    with sync_playwright() as p:
        # Launch a fresh browser (not using Chrome profile to avoid lock issues)
        print("\nLaunching browser...", flush=True)

        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Add cookies to the browser context
        print("Injecting cookies...", flush=True)
        context.add_cookies(cookie_list)

        page = context.pages[0] if context.pages else context.new_page()

        try:
            # Navigate to DNA section first (to get redirected to correct URL with GUID)
            print("Navigating to DNA section...", flush=True)
            page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="networkidle", timeout=60000)
            time.sleep(2)

            print(f"Redirected to: {page.url}", flush=True)

            # Extract test GUID from URL
            guid_match = re.search(r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
                                   page.url, re.IGNORECASE)
            if guid_match:
                test_guid = guid_match.group(1).upper()
                print(f"Found test GUID: {test_guid}", flush=True)

            # Now navigate to the matches page using the correct URL structure
            # Try clicking on DNA Matches link or navigate directly
            matches_url = f"{ANCESTRY_BASE_URL}/discoveryui-matches/match-list/{test_guid}" if test_guid else f"{ANCESTRY_BASE_URL}/dna"
            print(f"Navigating to matches: {matches_url}...", flush=True)
            page.goto(matches_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            print(f"Current URL: {page.url}", flush=True)

            # Save screenshot for debugging
            page.screenshot(path="/tmp/ancestry_debug.png")
            print("Saved screenshot to /tmp/ancestry_debug.png", flush=True)

            # Check if we're logged in (look for matches or login page)
            if "sign-in" in page.url.lower() or "login" in page.url.lower():
                print("\n⚠️  Not logged in! Please log into Ancestry in Chrome first.")
                print("   Then close Chrome and run this script again.")
                context.close()
                browser.close()
                return []

            # Wait for matches to load - save HTML first to find correct selectors
            print("Waiting for matches to load...", flush=True)
            time.sleep(3)

            # Dismiss any popup dialogs (like "Welcome to Pro Tools for DNA!")
            try:
                got_it_btn = page.query_selector('button:has-text("Got it")')
                if got_it_btn:
                    got_it_btn.click()
                    print("Dismissed popup dialog", flush=True)
                    time.sleep(1)
            except Exception:
                pass  # No popup to dismiss

            # Save HTML for debugging selectors
            html = page.content()
            with open("/tmp/ancestry_matches.html", "w") as f:
                f.write(html)
            print("Saved HTML to /tmp/ancestry_matches.html", flush=True)

            # Try to set 50 matches per page (click the 50 option at bottom left)
            print("Setting 50 matches per page...", flush=True)
            try:
                # Look for the page size selector
                fifty_btn = page.query_selector('button:has-text("50"), [aria-label*="50"]')
                if fifty_btn:
                    fifty_btn.click()
                    time.sleep(2)
                    print("  Set to 50 per page", flush=True)
                else:
                    # Try clicking on text that says "50"
                    page.click('text=50', timeout=3000)
                    time.sleep(2)
                    print("  Set to 50 per page", flush=True)
            except Exception as e:
                print(f"  Could not set page size: {e}", flush=True)

            # Use PAGINATION to load all matches (not scrolling)
            # The page has a <ui-pagination data-testid="paginator"> element
            # that shows total count and allows clicking through pages
            all_matches_data = []
            seen_guids = set()

            # Get pagination info first
            pagination_info = page.evaluate("""
                () => {
                    const paginator = document.querySelector('ui-pagination[data-testid="paginator"]');
                    if (!paginator) return null;
                    return {
                        total: parseInt(paginator.getAttribute('total') || '0'),
                        itemsPerPage: parseInt(paginator.getAttribute('items-per-page') || '20'),
                        currentPage: parseInt(paginator.getAttribute('page') || '1')
                    };
                }
            """)

            if pagination_info:
                total_value = pagination_info['total']
                items_per_page = pagination_info['itemsPerPage']
                # Note: 'total' might mean total PAGES, not total matches!
                # If total=1318 and items_per_page=20, user reports 2000+ matches on Ancestry
                # So total might be pages. Let's paginate until we can't anymore.
                # Set a high limit but don't calculate pages from total/items_per_page
                max_pages = max(total_value + 10, 2000)  # Allow for at least total_value pages
                print(f"\nFound pagination: total={total_value}, {items_per_page}/page")
                print(f"Will paginate up to {max_pages} pages (stopping when no more content)")
            else:
                print("\nNo pagination found, will try to extract visible matches only")
                max_pages = 1

            total_pages = max_pages  # Use max_pages as the limit

            # Function to extract matches from current page
            def extract_current_page_matches():
                return page.evaluate("""
                    () => {
                        const matches = [];
                        const entries = document.querySelectorAll('.matchEntryGridDesktop');
                        entries.forEach((entry) => {
                            try {
                                const nameEl = entry.querySelector('a[data-testid="matchNameLink"]');
                                let matchGuid = null;
                                if (nameEl && nameEl.href) {
                                    const guidMatch = nameEl.href.match(/with\\/([A-F0-9-]+)/i);
                                    if (guidMatch) {
                                        matchGuid = guidMatch[1].toUpperCase();
                                    }
                                }
                                if (matchGuid) {
                                    const name = nameEl ? nameEl.textContent.trim() : null;
                                    const cmEl = entry.querySelector('[data-testid="sharedDnaAmount"]');
                                    const cmText = cmEl ? cmEl.textContent : '';
                                    let sharedCm = null;
                                    const cmMatch = cmText.match(/([\\d,]+)\\s*cM/i);
                                    if (cmMatch) {
                                        sharedCm = parseFloat(cmMatch[1].replace(/,/g, ''));
                                    }
                                    const relEl = entry.querySelector('.relationshipLabel');
                                    const relationship = relEl ? relEl.textContent.trim() : null;
                                    const sideEl = entry.querySelector('.sharedDnaContainer .secondaryText');
                                    const matchSide = sideEl ? sideEl.textContent.trim() : null;

                                    // Tree info
                                    let hasTree = false;
                                    let treeSize = null;
                                    let linkedTreeId = null;
                                    const treeLink = entry.querySelector('[data-testid="treeCountLink"]');
                                    if (treeLink) {
                                        hasTree = true;
                                        const sizeMatch = treeLink.textContent.match(/(\\d[\\d,]*)\\s*people/i);
                                        if (sizeMatch) treeSize = parseInt(sizeMatch[1].replace(/,/g, ''));
                                        const treeIdMatch = treeLink.href.match(/family-tree\\/tree\\/(\\d+)/);
                                        if (treeIdMatch) linkedTreeId = treeIdMatch[1];
                                    }

                                    matches.push({
                                        guid: matchGuid,
                                        name: name,
                                        sharedCm: sharedCm,
                                        relationship: relationship,
                                        matchSide: matchSide,
                                        hasTree: hasTree,
                                        treeSize: treeSize,
                                        linkedTreeId: linkedTreeId
                                    });
                                }
                            } catch (e) {}
                        });
                        return matches;
                    }
                """)

            print("\nPaginating through matches...")
            current_page = 1
            consecutive_failures = 0
            max_failures = 3

            while current_page <= total_pages and consecutive_failures < max_failures:
                # Extract matches from current page
                current_matches = extract_current_page_matches()

                # Count new matches
                new_count = 0
                for m in current_matches:
                    if m['guid'] and m['guid'] not in seen_guids:
                        seen_guids.add(m['guid'])
                        all_matches_data.append(m)
                        new_count += 1

                if current_page % 5 == 0 or current_page == 1:
                    print(f"  Page {current_page}/{total_pages}: +{new_count} new ({len(all_matches_data)} total)", flush=True)

                if new_count == 0:
                    consecutive_failures += 1
                else:
                    consecutive_failures = 0

                # Move to next page by clicking pagination buttons
                if current_page < total_pages:
                    next_page = current_page + 1

                    # Click the next button using JavaScript
                    clicked = page.evaluate("""
                        () => {
                            // The ui-pagination element is a web component
                            const paginator = document.querySelector('ui-pagination[data-testid="paginator"]');
                            if (!paginator) return {success: false, error: 'No paginator found'};

                            // Web components often use shadow DOM - try both
                            let nextBtn = null;

                            // Check shadow root first
                            if (paginator.shadowRoot) {
                                nextBtn = paginator.shadowRoot.querySelector(
                                    'button[aria-label*="forward" i], ' +
                                    'button[aria-label*="next" i], ' +
                                    '[data-testid="forward"]'
                                );
                            }

                            // Fallback to light DOM
                            if (!nextBtn) {
                                nextBtn = paginator.querySelector(
                                    'button[aria-label*="forward" i], ' +
                                    'button[aria-label*="next" i]'
                                );
                            }

                            // Try to find a forward arrow button by icon type
                            if (!nextBtn && paginator.shadowRoot) {
                                const allBtns = paginator.shadowRoot.querySelectorAll('button, ui-button');
                                for (const btn of allBtns) {
                                    const icon = btn.querySelector('ui-icon');
                                    if (icon && (icon.getAttribute('type') || '').includes('forward')) {
                                        nextBtn = btn;
                                        break;
                                    }
                                }
                            }

                            if (nextBtn && !nextBtn.disabled) {
                                nextBtn.click();
                                return {success: true};
                            }

                            // Last resort: dispatch a custom event to the paginator
                            try {
                                paginator.setAttribute('page', String(parseInt(paginator.getAttribute('page') || '1') + 1));
                                paginator.dispatchEvent(new CustomEvent('page-change', {bubbles: true}));
                                return {success: true, method: 'attribute'};
                            } catch (e) {
                                return {success: false, error: e.message};
                            }
                        }
                    """)

                    if clicked and clicked.get('success'):
                        time.sleep(1.5)  # Wait for page content to update
                    else:
                        if current_page % 10 == 0:
                            print(f"  Navigation issue at page {current_page}: {clicked}", flush=True)

                current_page += 1

            print(f"\nTotal unique matches collected: {len(all_matches_data)}")

            # Convert collected data to expected format
            matches = []
            for m in all_matches_data:
                # Parse match_side
                side_text = m.get('matchSide', '') or ''
                side = 'unknown'
                if 'Paternal' in side_text:
                    side = 'paternal'
                elif 'Maternal' in side_text:
                    side = 'maternal'
                elif 'Both sides' in side_text:
                    side = 'both'
                elif 'Parent 1' in side_text:
                    side = 'parent1'
                elif 'Parent 2' in side_text:
                    side = 'parent2'

                matches.append({
                    'name': m.get('name'),
                    'shared_cm': m.get('sharedCm'),
                    'predicted_relationship': m.get('relationship'),
                    'ancestry_id': m.get('guid'),
                    'match_side': side,
                    'tree_size': m.get('treeSize'),
                    'has_tree': m.get('hasTree', False),
                    'linked_tree_id': m.get('linkedTreeId')
                })

            print(f"Formatted {len(matches)} matches for import", flush=True)

        except Exception as e:
            print(f"\nError during browser automation: {e}", flush=True)
            import traceback
            traceback.print_exc()

        finally:
            print("\nClosing browser...", flush=True)
            context.close()
            browser.close()

    return matches


ANCESTRY_DNA_API = "https://www.ancestry.co.uk/discoveryui-matchesservice/api"

# Endpoints
ENDPOINTS = {
    "tests": "/dna/secure/tests",
    "matches": "/discoveryui-matchesservice/api/samples/{test_guid}/matches/list",
    "match_details": "/discoveryui-matchesservice/api/samples/{test_guid}/matches/{match_guid}",
    "shared_matches": "/discoveryui-matchesservice/api/samples/{test_guid}/matches/{match_guid}/sharedmatches",
}


def get_browser_cookies():
    """Extract Ancestry cookies from browser."""
    print("Extracting cookies from browser...")

    cookies = None

    # Try Chrome first (check both .co.uk and .com domains)
    try:
        cookies = browser_cookie3.chrome(domain_name=".ancestry.co.uk")
        print("  Found Chrome cookies (.co.uk)")
        return cookies
    except Exception as e:
        print(f"  Chrome (.co.uk): {e}")

    try:
        cookies = browser_cookie3.chrome(domain_name=".ancestry.com")
        print("  Found Chrome cookies (.com)")
        return cookies
    except Exception as e:
        print(f"  Chrome (.com): {e}")

    # Try Firefox
    try:
        cookies = browser_cookie3.firefox(domain_name=".ancestry.co.uk")
        print("  Found Firefox cookies (.co.uk)")
        return cookies
    except Exception as e:
        print(f"  Firefox (.co.uk): {e}")

    try:
        cookies = browser_cookie3.firefox(domain_name=".ancestry.com")
        print("  Found Firefox cookies (.com)")
        return cookies
    except Exception as e:
        print(f"  Firefox (.com): {e}")

    # Try Safari
    try:
        cookies = browser_cookie3.safari(domain_name=".ancestry.co.uk")
        print("  Found Safari cookies (.co.uk)")
        return cookies
    except Exception as e:
        print(f"  Safari (.co.uk): {e}")

    try:
        cookies = browser_cookie3.safari(domain_name=".ancestry.com")
        print("  Found Safari cookies (.com)")
        return cookies
    except Exception as e:
        print(f"  Safari (.com): {e}")

    return None


def create_session():
    """Create a requests session with Ancestry authentication."""
    cookies = get_browser_cookies()

    if not cookies:
        print("\nERROR: Could not find Ancestry cookies in any browser.")
        print("Make sure you:")
        print("  1. Log into ancestry.com in Chrome, Firefox, or Safari")
        print("  2. CLOSE the browser (so cookies can be read)")
        print("  3. Run this script again")
        return None

    session = requests.Session()
    session.cookies = cookies
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    })

    return session


def get_test_guid(session):
    """Get the DNA test GUID for the logged-in user by following redirects."""
    print("\nFetching your DNA test info...")

    # The DNA page redirects to a URL containing the test GUID
    url = f"{ANCESTRY_BASE_URL}/dna"

    try:
        response = session.get(url, allow_redirects=True)
        final_url = response.url

        # Extract GUID from URL like: /dna/insights/E756DE6C-0C8D-443B-8793-ADDB6F35FD6A
        import re
        guid_match = re.search(r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})', final_url, re.IGNORECASE)

        if guid_match:
            guid = guid_match.group(1).upper()
            print(f"  Found test GUID: {guid}")
            return guid
        else:
            print(f"  Could not find GUID in URL: {final_url}")

    except Exception as e:
        print(f"  Error: {e}")

    return None


def fetch_matches(session, test_guid, page=1, page_size=50, min_cm=None, max_cm=None, bucket_id=None):
    """Fetch a page of DNA matches."""
    url = f"https://www.ancestry.co.uk/discoveryui-matchesservice/api/samples/{test_guid}/matches/list"

    params = {
        "page": page,
        "pagesize": page_size,
        "sortby": "RELATIONSHIP",
    }

    # Try cM range filtering
    if min_cm is not None:
        params["mincm"] = min_cm
    if max_cm is not None:
        params["maxcm"] = max_cm
    if bucket_id is not None:
        params["bucketid"] = bucket_id

    try:
        response = session.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Error fetching page {page}: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"  Error fetching page {page}: {e}")
        return None


def explore_api_response(session, test_guid):
    """Explore the API response to find pagination mechanisms."""
    print("\n" + "=" * 60)
    print("EXPLORING API RESPONSE STRUCTURE")
    print("=" * 60)

    url = f"https://www.ancestry.co.uk/discoveryui-matchesservice/api/samples/{test_guid}/matches/list"

    response = session.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return

    data = response.json()

    # Print top-level keys (looking for pagination tokens)
    print("\nTop-level keys in response:")
    for key in data.keys():
        val = data[key]
        if isinstance(val, (str, int, float, bool)) or val is None:
            print(f"  {key}: {val}")
        elif isinstance(val, list):
            print(f"  {key}: list[{len(val)}]")
        elif isinstance(val, dict):
            print(f"  {key}: dict{list(val.keys())}")

    # Look for pagination-related fields
    pagination_hints = ['cursor', 'token', 'next', 'continuation', 'offset', 'bookmark', 'after', 'before']
    print("\nSearching for pagination tokens...")
    found_hints = []
    for key in data.keys():
        if any(hint in key.lower() for hint in pagination_hints):
            found_hints.append((key, data[key]))

    if found_hints:
        print("  Found potential pagination fields:")
        for k, v in found_hints:
            print(f"    {k}: {v}")
    else:
        print("  No obvious pagination tokens found in top-level keys")

    # Check matchGroups structure
    if "matchGroups" in data:
        print(f"\nMatch groups found: {len(data['matchGroups'])}")
        for group in data["matchGroups"]:
            name = group.get("name", {})
            matches = group.get("matches", [])
            group_id = name.get("id") if isinstance(name, dict) else name
            group_key = name.get("key") if isinstance(name, dict) else "?"
            print(f"  Group {group_id} ({group_key}): {len(matches)} matches")

            # Check for group-level pagination
            for key in group.keys():
                if key not in ["name", "matches"]:
                    print(f"    Extra field: {key} = {group[key]}")

    # Try fetching with different parameters
    print("\n" + "-" * 40)
    print("Testing different API parameters...")

    # Test 1: bucketId parameter (Ancestry often uses relationship "buckets")
    buckets = [1, 2, 3, 4, 5, 6, 7]  # Different relationship categories
    print("\nTesting bucketId parameter:")
    for bucket in buckets:
        resp = session.get(url, params={"bucketid": bucket})
        if resp.status_code == 200:
            d = resp.json()
            count = d.get("matchCount", 0)
            total = d.get("totalMatches", 0)
            groups = len(d.get("matchGroups", []))
            if count > 0:
                print(f"  bucketid={bucket}: {count} matches (total: {total}, groups: {groups})")

    # Test 2: cM ranges
    print("\nTesting cM range filtering:")
    cm_ranges = [(400, None), (200, 400), (100, 200), (50, 100), (20, 50), (8, 20)]
    for min_cm, max_cm in cm_ranges:
        params = {"sortby": "RELATIONSHIP"}
        if min_cm:
            params["mincm"] = min_cm
        if max_cm:
            params["maxcm"] = max_cm
        resp = session.get(url, params=params)
        if resp.status_code == 200:
            d = resp.json()
            count = d.get("matchCount", 0)
            total = d.get("totalMatches", 0)
            range_str = f"{min_cm}+" if max_cm is None else f"{min_cm}-{max_cm}"
            if count > 0 or total > 0:
                print(f"  cM {range_str}: returned {count}, total {total}")

    # Test 3: Check for a "v2" or alternate endpoint
    print("\nTesting alternate endpoints:")
    alt_endpoints = [
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matches",
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matchlist",
        f"/dna/secure/tests/{test_guid}/matches",
        f"/api/dna/matches/{test_guid}",
    ]
    for endpoint in alt_endpoints:
        try:
            resp = session.get(f"https://www.ancestry.co.uk{endpoint}")
            print(f"  {endpoint}: {resp.status_code}")
            if resp.status_code == 200:
                try:
                    d = resp.json()
                    print(f"    Keys: {list(d.keys())[:5]}")
                except:
                    print(f"    (not JSON)")
        except Exception as e:
            print(f"  {endpoint}: error - {e}")

    # Test 4: Different pagination parameters (GET)
    print("\nTesting pagination parameters (GET):")
    test_params = [
        {"page": 2},
        {"pageIdx": 2},
        {"offset": 200},
        {"lastMatchesServicePageIdx": 2},
    ]
    for params in test_params:
        resp = session.get(url, params=params)
        if resp.status_code == 200:
            d = resp.json()
            count = d.get("matchCount", 0)
            bookmark = d.get("bookmarkData", {})
            page_idx = bookmark.get("lastMatchesServicePageIdx")
            print(f"  {params}: count={count}, pageIdx={page_idx}")

    # Test 5: Try POST with bookmark data
    print("\nTesting POST requests:")
    post_payloads = [
        {"bookmarkData": {"lastMatchesServicePageIdx": 2}},
        {"page": 2},
        {"pageIdx": 2},
        {"lastMatchesServicePageIdx": 2},
    ]
    for payload in post_payloads:
        try:
            resp = session.post(url, json=payload)
            print(f"  POST {payload}: status={resp.status_code}")
            if resp.status_code == 200:
                d = resp.json()
                count = d.get("matchCount", 0)
                print(f"    count={count}")
        except Exception as e:
            print(f"  POST {payload}: error - {e}")

    # Test 6: Check for paged vs list endpoint variations
    print("\nTesting endpoint variations:")
    endpoint_vars = [
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matches/list?page=2",
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matches/paged?page=2",
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matchespaged",
        f"/discoveryui-matchesservice/api/samples/{test_guid}/matches/all",
    ]
    for endpoint in endpoint_vars:
        try:
            resp = session.get(f"https://www.ancestry.co.uk{endpoint}")
            print(f"  {endpoint.split('/')[-1]}: {resp.status_code}")
        except Exception as e:
            print(f"  error: {e}")

    return data


def fetch_matches_with_bookmark(session, test_guid, bookmark_page=None):
    """Fetch DNA matches using bookmark-based pagination."""
    url = f"https://www.ancestry.co.uk/discoveryui-matchesservice/api/samples/{test_guid}/matches/list"

    params = {"sortby": "RELATIONSHIP"}
    if bookmark_page is not None:
        params["bookmarkpage"] = bookmark_page

    try:
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  Error: Status {response.status_code}", flush=True)
            return None
    except Exception as e:
        print(f"  Error: {e}", flush=True)
        return None


def fetch_matches_secure_api(session, test_guid, page=1, base_url="https://www.ancestry.com"):
    """Fetch DNA matches using the /dna/secure endpoint (alternate API)."""
    # This is the older API used by some tools
    url = f"{base_url}/dna/secure/tests/{test_guid}/matches"

    params = {"page": page}

    try:
        response = session.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif page == 1:
            # Only print error on first page
            print(f"    Secure API ({base_url}) returned: {response.status_code}", flush=True)
        return None
    except Exception as e:
        if page == 1:
            print(f"    Secure API error: {e}", flush=True)
        return None


def fetch_all_matches(session, test_guid):
    """Fetch all DNA matches using multiple strategies."""
    print("\nFetching all DNA matches...")

    all_matches = []
    seen_guids = set()

    # Strategy 1: Try the secure API with simple page numbers (used by getmydnamatches)
    print("\n  Strategy 1: /dna/secure API with page numbers...")

    # Try both .com and .co.uk domains
    working_base = None
    for base_url in ["https://www.ancestry.com", "https://www.ancestry.co.uk"]:
        data = fetch_matches_secure_api(session, test_guid, 1, base_url)
        if data:
            working_base = base_url
            print(f"    Using {base_url}", flush=True)
            break

    if not working_base:
        print("    Secure API not available on any domain", flush=True)
    else:
        page = 1
        consecutive_empty = 0
        while consecutive_empty < 3:  # Allow some empty pages
            data = fetch_matches_secure_api(session, test_guid, page, working_base)

            if not data:
                break

            match_groups = data.get("matchGroups", [])
            if not match_groups:
                consecutive_empty += 1
                page += 1
                continue

            consecutive_empty = 0
            new_count = 0
            for group in match_groups:
                for match in group.get("matches", []):
                    guid = match.get("testGuid")
                    if guid and guid not in seen_guids:
                        seen_guids.add(guid)
                        all_matches.append(match)
                        new_count += 1

            print(f"    Page {page}: +{new_count} (total: {len(all_matches)})", flush=True)

            if new_count == 0:
                consecutive_empty += 1

            page += 1
            if page > 200:  # Safety limit
                break

    # Strategy 2: Try discoveryui API if secure didn't work well
    if len(all_matches) < 200:
        print("\n  Strategy 2: discoveryui API...")
        data = fetch_matches_with_bookmark(session, test_guid, None)
        if data:
            for group in data.get("matchGroups", []):
                for match in group.get("matches", []):
                    guid = match.get("testGuid")
                    if guid and guid not in seen_guids:
                        seen_guids.add(guid)
                        all_matches.append(match)
            print(f"    Added matches, total now: {len(all_matches)}", flush=True)

    print(f"\nTotal unique matches fetched: {len(all_matches)}")
    return all_matches


def fetch_all_matches_secure(session, test_guid, seen_guids):
    """Fetch matches using the /dna/secure endpoint as fallback."""
    all_matches = []
    page = 1

    while True:
        data = fetch_matches_secure_api(session, test_guid, page)

        if not data:
            break

        match_groups = data.get("matchGroups", [])
        if not match_groups:
            break

        new_count = 0
        for group in match_groups:
            for match in group.get("matches", []):
                guid = match.get("testGuid")
                if guid and guid not in seen_guids:
                    seen_guids.add(guid)
                    all_matches.append(match)
                    new_count += 1

        if new_count == 0:
            break

        print(f"    Secure API page {page}: +{new_count}")
        page += 1

        if page > 100:
            break

    return all_matches


def parse_match_side(match):
    """Parse the maternal/paternal side from match data."""
    maternal = match.get("maternal", False) or match.get("mothersSide", False)
    paternal = match.get("paternal", False) or match.get("fathersSide", False)

    if maternal and paternal:
        return "both"
    elif paternal:
        return "paternal"
    elif maternal:
        return "maternal"
    return "unknown"


def import_to_database(matches, db_path):
    """Import matches into SQLite database."""
    print(f"\nImporting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    imported = 0
    skipped = 0

    for match in matches:
        try:
            # Extract fields from Ancestry API structure
            ancestry_id = match.get("testGuid")
            name = match.get("displayName") or match.get("publicDisplayName") or "Unknown"

            # Relationship data is nested
            rel_data = match.get("relationship", {})
            shared_cm = rel_data.get("sharedCentimorgans", 0)
            shared_segments = rel_data.get("sharedSegments")

            # Relationship label
            predicted_rel = match.get("relationshipLabel")

            # Side
            side = parse_match_side(match)

            # Tree info (may be in different location or not present)
            tree_info = match.get("treeInfo") or match.get("linkedTree") or {}
            has_tree = bool(tree_info) or match.get("hasLinkedTree", False)
            tree_size = tree_info.get("treeSize") or tree_info.get("personCount")

            # Check if exists
            cursor.execute(
                "SELECT id FROM dna_match WHERE ancestry_id = ?",
                (ancestry_id,)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            # Check by name + cM (in case ancestry_id is different)
            cursor.execute(
                "SELECT id FROM dna_match WHERE name = ? AND shared_cm = ?",
                (name, shared_cm)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            # Insert
            cursor.execute("""
                INSERT INTO dna_match
                (ancestry_id, name, shared_cm, shared_segments, predicted_relationship,
                 match_side, has_tree, tree_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ancestry_id,
                name,
                shared_cm,
                shared_segments,
                predicted_rel,
                side,
                has_tree,
                tree_size,
                datetime.now().isoformat()
            ))
            imported += 1

            if imported % 100 == 0:
                conn.commit()
                print(f"  Imported {imported}...")

        except Exception as e:
            print(f"  Error importing {match.get('matchTestDisplayName', 'unknown')}: {e}")
            continue

    conn.commit()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM dna_match")
    total = cursor.fetchone()[0]

    conn.close()

    print(f"\nImport complete:")
    print(f"  New imports:  {imported}")
    print(f"  Skipped:      {skipped}")
    print(f"  Total in DB:  {total}")

    return imported


def import_browser_matches(matches, db_path):
    """Import matches scraped from browser into SQLite database."""
    print(f"\nImporting browser-scraped matches to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    imported = 0
    skipped = 0

    for match in matches:
        try:
            # Browser-scraped matches have simpler structure
            ancestry_id = match.get("ancestry_id")
            name = match.get("name", "Unknown")
            shared_cm = match.get("shared_cm", 0)
            predicted_rel = match.get("predicted_relationship")

            if not name or name == "Unknown":
                continue

            # Check if exists by ancestry_id
            if ancestry_id:
                cursor.execute(
                    "SELECT id FROM dna_match WHERE ancestry_id = ?",
                    (ancestry_id,)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

            # Check by name + cM
            cursor.execute(
                "SELECT id FROM dna_match WHERE name = ? AND ABS(shared_cm - ?) < 0.1",
                (name, shared_cm or 0)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            # Get side info if available - map parent1/parent2 to unknown
            match_side = match.get("match_side", "unknown")
            if match_side in ("parent1", "parent2"):
                match_side = "unknown"  # Ancestry hasn't determined which parent yet

            # Insert
            cursor.execute("""
                INSERT INTO dna_match
                (ancestry_id, name, shared_cm, predicted_relationship, match_side, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ancestry_id,
                name,
                shared_cm,
                predicted_rel,
                match_side,
                datetime.now().isoformat()
            ))
            imported += 1

            if imported % 100 == 0:
                conn.commit()
                print(f"  Imported {imported}...", flush=True)

        except Exception as e:
            print(f"  Error importing {match.get('name', 'unknown')}: {e}")
            continue

    conn.commit()

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM dna_match")
    total = cursor.fetchone()[0]

    conn.close()

    print(f"\nImport complete:")
    print(f"  New imports:  {imported}")
    print(f"  Skipped:      {skipped}")
    print(f"  Total in DB:  {total}")

    return imported


def scan_trees(test_guid=None, headless=True, limit=None, min_cm=None):
    """
    Scan DNA matches for tree information (size, public/private).
    Updates the database with tree_size and has_public_tree for each match.

    Args:
        test_guid: Optional test GUID (will be auto-detected if not provided)
        headless: Run browser in headless mode
        limit: Maximum number of matches to scan (None = all)
        min_cm: Only scan matches with at least this many cM
    """
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("SCANNING MATCHES FOR TREE INFORMATION")
    print("=" * 60)

    # Get matches from database that need scanning
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT id, ancestry_id, name, shared_cm
        FROM dna_match
        WHERE ancestry_id IS NOT NULL
    """
    params = []

    if min_cm:
        query += " AND shared_cm >= ?"
        params.append(min_cm)

    query += " ORDER BY shared_cm DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    matches = cursor.fetchall()
    conn.close()

    print(f"Found {len(matches)} matches to scan")

    if not matches:
        return

    # Get cookies
    print("Extracting cookies from Chrome...", flush=True)
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": bool(cookie.secure),
                })
        except:
            pass

    if not cookie_list:
        print("No cookies found - log into Ancestry in Chrome first")
        return

    updated = 0
    with_public_tree = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        try:
            # Get our test GUID if not provided
            if not test_guid:
                page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="networkidle", timeout=60000)
                time.sleep(2)
                guid_match = re.search(r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
                                       page.url, re.IGNORECASE)
                if guid_match:
                    test_guid = guid_match.group(1).upper()
                    print(f"Test GUID: {test_guid}")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for i, (match_id, match_guid, name, cm) in enumerate(matches):
                print(f"\n[{i+1}/{len(matches)}] {name} ({cm:.0f} cM)...", flush=True)

                try:
                    # Navigate to the trees tab for this match
                    trees_url = f"{ANCESTRY_BASE_URL}/discoveryui-matches/compare/{test_guid}/with/{match_guid}/trees"
                    page.goto(trees_url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)

                    # Extract tree info from the page
                    tree_info = page.evaluate("""
                        () => {
                            const result = {
                                has_tree: false,
                                is_public: false,
                                tree_size: null,
                                tree_id: null
                            };

                            // Look for linked tree card
                            const treeCard = document.querySelector('.linkedTreeCard, .treeCard, [class*="TreeCard"]');
                            if (treeCard) {
                                result.has_tree = true;

                                // Check for "Public" text
                                const text = treeCard.textContent.toLowerCase();
                                result.is_public = text.includes('public');

                                // Get person count - look for patterns like "241 people" or "50 people"
                                const countMatch = text.match(/(\\d+)\\s*(?:people|person)/i);
                                if (countMatch) {
                                    result.tree_size = parseInt(countMatch[1]);
                                }

                                // Also try to find it in a specific element
                                const countEl = treeCard.querySelector('[class*="personCount"], [class*="treeSize"], [class*="count"]');
                                if (countEl && !result.tree_size) {
                                    const countText = countEl.textContent;
                                    const m = countText.match(/(\\d+)/);
                                    if (m) result.tree_size = parseInt(m[1]);
                                }

                                // Get tree link/ID
                                const link = treeCard.querySelector('a[href*="/tree/"]');
                                if (link) {
                                    const href = link.getAttribute('href');
                                    const treeMatch = href.match(/\\/tree\\/(\\d+)/);
                                    if (treeMatch) result.tree_id = treeMatch[1];
                                }
                            }

                            // Also check for "No linked tree" message
                            const noTree = document.querySelector('[class*="noTree"], [class*="no-tree"]');
                            if (noTree && noTree.textContent.toLowerCase().includes('no')) {
                                result.has_tree = false;
                            }

                            return result;
                        }
                    """)

                    # Update database
                    cursor.execute("""
                        UPDATE dna_match
                        SET has_tree = ?,
                            tree_size = ?,
                            has_public_tree = ?
                        WHERE id = ?
                    """, (
                        tree_info['has_tree'],
                        tree_info['tree_size'],
                        tree_info['is_public'],
                        match_id
                    ))
                    conn.commit()
                    updated += 1

                    if tree_info['is_public'] and tree_info['tree_size']:
                        with_public_tree += 1
                        print(f"  ✓ PUBLIC tree: {tree_info['tree_size']} people", flush=True)
                    elif tree_info['has_tree']:
                        size_str = f"{tree_info['tree_size']} people" if tree_info['tree_size'] else "size unknown"
                        print(f"  - Private tree ({size_str})", flush=True)
                    else:
                        print(f"  - No linked tree", flush=True)

                except Exception as e:
                    print(f"  Error: {e}", flush=True)
                    continue

            conn.close()

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

        finally:
            context.close()
            browser.close()

    print(f"\n" + "=" * 60)
    print(f"SCAN COMPLETE")
    print(f"=" * 60)
    print(f"  Updated:          {updated} matches")
    print(f"  With public tree: {with_public_tree}")

    # Show top public trees
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, shared_cm, tree_size
        FROM dna_match
        WHERE has_public_tree = 1 AND tree_size IS NOT NULL
        ORDER BY tree_size DESC
        LIMIT 10
    """)
    top_trees = cursor.fetchall()
    conn.close()

    if top_trees:
        print(f"\nTop 10 largest public trees:")
        print("-" * 50)
        for name, cm, size in top_trees:
            print(f"  {name:<30} {cm:>6.0f} cM  {size:>4} people")


def scan_shared_matches(test_guid=None, headless=True, limit=None, min_cm=None):
    """
    Batch scan shared matches for top DNA matches and store in database.

    Args:
        test_guid: Optional test GUID (will be auto-detected if not provided)
        headless: Run browser in headless mode
        limit: Maximum number of matches to scan
        min_cm: Only scan matches with at least this many cM
    """
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("SCANNING SHARED MATCHES")
    print("=" * 60)

    # Get matches to scan
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT id, ancestry_id, name, shared_cm
        FROM dna_match
        WHERE ancestry_id IS NOT NULL
    """
    params = []

    if min_cm:
        query += " AND shared_cm >= ?"
        params.append(min_cm)

    query += " ORDER BY shared_cm DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    matches = cursor.fetchall()
    conn.close()

    print(f"Found {len(matches)} matches to scan")

    if not matches:
        return

    # Get cookies
    print("Extracting cookies from Chrome...", flush=True)
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": bool(cookie.secure),
                })
        except:
            pass

    if not cookie_list:
        print("No cookies found - log into Ancestry in Chrome first")
        return

    total_imported = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        try:
            # Get test GUID
            if not test_guid:
                page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="networkidle", timeout=60000)
                time.sleep(2)
                guid_match = re.search(r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
                                       page.url, re.IGNORECASE)
                if guid_match:
                    test_guid = guid_match.group(1).upper()
                    print(f"Test GUID: {test_guid}")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            for i, (match_id, match_guid, name, cm) in enumerate(matches):
                print(f"\n[{i+1}/{len(matches)}] {name} ({cm:.0f} cM)...", flush=True)

                try:
                    # Navigate to shared matches page
                    shared_url = f"{ANCESTRY_BASE_URL}/discoveryui-matches/compare/{test_guid}/with/{match_guid}/sharedmatches"
                    page.goto(shared_url, wait_until="networkidle", timeout=30000)
                    time.sleep(2)

                    # Scroll to load all shared matches
                    prev_count = 0
                    for _ in range(5):
                        elements = page.query_selector_all('.matchOfMatchEntry')
                        if len(elements) == prev_count:
                            break
                        prev_count = len(elements)
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1)

                    # Extract shared matches
                    shared_data = page.evaluate("""
                        () => {
                            const matches = [];
                            document.querySelectorAll('.matchOfMatchEntry').forEach((entry) => {
                                try {
                                    const nameEl = entry.querySelector('a.matchInfoName');
                                    const name = nameEl ? nameEl.textContent.trim() : null;

                                    const yourDnaEl = entry.querySelector('.yourSharedDNA');
                                    let yourCm = null;
                                    if (yourDnaEl) {
                                        const cmMatch = yourDnaEl.textContent.match(/([\\d,]+)\\s*cM/i);
                                        if (cmMatch) yourCm = parseFloat(cmMatch[1].replace(/,/g, ''));
                                    }

                                    const matchDnaEl = entry.querySelector('.matchSharedDNA');
                                    let matchCm = null;
                                    if (matchDnaEl) {
                                        const cmMatch = matchDnaEl.textContent.match(/([\\d,]+)\\s*cM/i);
                                        if (cmMatch) matchCm = parseFloat(cmMatch[1].replace(/,/g, ''));
                                    }

                                    if (name) {
                                        matches.push({name, your_cm: yourCm, match_cm: matchCm});
                                    }
                                } catch(e) {}
                            });
                            return matches;
                        }
                    """)

                    # Store in database
                    imported = 0
                    for shared in shared_data:
                        # Try to find match2 in database
                        cursor.execute("SELECT id FROM dna_match WHERE name = ?", (shared['name'],))
                        row = cursor.fetchone()
                        match2_id = row[0] if row else None

                        try:
                            cursor.execute("""
                                INSERT OR REPLACE INTO shared_match
                                (match1_id, match2_id, match2_name, match1_to_match2_cm, you_to_match2_cm)
                                VALUES (?, ?, ?, ?, ?)
                            """, (match_id, match2_id, shared['name'], shared['match_cm'], shared['your_cm']))
                            imported += 1
                        except:
                            pass

                    conn.commit()
                    total_imported += imported
                    print(f"  Found {len(shared_data)} shared matches, stored {imported}", flush=True)

                except Exception as e:
                    print(f"  Error: {e}", flush=True)
                    continue

            conn.close()

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

        finally:
            context.close()
            browser.close()

    print(f"\n" + "=" * 60)
    print(f"SCAN COMPLETE")
    print(f"=" * 60)
    print(f"  Total relationships stored: {total_imported}")

    # Show summary
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM shared_match")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT match1_id) FROM shared_match")
    matches_with_data = cursor.fetchone()[0]
    print(f"  Total in database: {total} relationships from {matches_with_data} matches")

    # Show interesting findings
    print(f"\nPeople who appear in multiple shared match lists (clusters):")
    cursor.execute("""
        SELECT match2_name, COUNT(*) as appearances, MAX(you_to_match2_cm) as your_cm
        FROM shared_match
        GROUP BY match2_name
        HAVING appearances >= 3
        ORDER BY appearances DESC
        LIMIT 15
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:<30} appears {row[1]}x (you: {row[2]:.0f} cM)")

    conn.close()


def fetch_shared_matches(match_name, test_guid=None, headless=False):
    """
    Fetch shared matches for a specific DNA match.
    """
    from playwright.sync_api import sync_playwright

    print(f"\nFetching shared matches for: {match_name}")

    # First, look up the match in the database to get their GUID
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ancestry_id, name, shared_cm FROM dna_match WHERE name LIKE ?",
        (f"%{match_name}%",)
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"No match found for '{match_name}'")
        return []

    if len(results) > 1:
        print(f"Multiple matches found:")
        for i, (guid, name, cm) in enumerate(results):
            print(f"  {i+1}. {name} ({cm} cM)")
        print("Please be more specific.")
        return []

    match_guid, match_full_name, match_cm = results[0]
    print(f"Found: {match_full_name} ({match_cm} cM)")

    if not match_guid:
        print("No Ancestry GUID stored for this match - can't fetch shared matches")
        return []

    # Get cookies
    print("Extracting cookies from Chrome...", flush=True)
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": bool(cookie.secure),
                })
        except:
            pass

    if not cookie_list:
        print("No cookies found - log into Ancestry in Chrome first")
        return []

    shared_matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        try:
            # Get our test GUID if not provided
            if not test_guid:
                page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="networkidle", timeout=60000)
                time.sleep(2)
                guid_match = re.search(r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
                                       page.url, re.IGNORECASE)
                if guid_match:
                    test_guid = guid_match.group(1).upper()

            # Navigate to compare page first
            compare_url = f"{ANCESTRY_BASE_URL}/discoveryui-matches/compare/{test_guid}/with/{match_guid}"
            print(f"Navigating to compare page...", flush=True)
            page.goto(compare_url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            print(f"URL: {page.url}", flush=True)

            # Look for and click "Shared Matches" tab
            try:
                shared_tab = page.query_selector('text=Shared matches, text=Shared Matches, [href*="shared"]')
                if shared_tab:
                    shared_tab.click()
                    time.sleep(2)
                else:
                    # Try clicking by text
                    page.click('text=Shared matches', timeout=5000)
                    time.sleep(2)
            except Exception as e:
                print(f"Could not find shared matches tab: {e}", flush=True)

            print(f"After click URL: {page.url}", flush=True)

            # Wait for shared matches to load
            time.sleep(3)

            # Scroll to load all shared matches (if infinite scroll is used)
            prev_count = 0
            for scroll_attempt in range(10):  # Max 10 scroll attempts
                match_elements = page.query_selector_all('.matchOfMatchEntry')
                count = len(match_elements)
                print(f"  Loaded {count} shared matches...", flush=True)
                if count == prev_count:
                    break  # No more loading
                prev_count = count
                # Scroll to bottom
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)

            print(f"Found {len(match_elements)} shared matches total", flush=True)

            # Extract shared match data using JavaScript
            shared_matches = page.evaluate("""
                () => {
                    const matches = [];
                    const entries = document.querySelectorAll('.matchOfMatchEntry');
                    entries.forEach((entry) => {
                        try {
                            // Get name from the link
                            const nameEl = entry.querySelector('a.matchInfoName');
                            const name = nameEl ? nameEl.textContent.trim() : null;

                            // Get YOUR shared cM from .yourSharedDNA
                            const yourDnaEl = entry.querySelector('.yourSharedDNA');
                            let yourCm = null;
                            let yourRelationship = null;
                            let side = null;
                            if (yourDnaEl) {
                                const yourText = yourDnaEl.textContent;
                                const cmMatch = yourText.match(/([\\d,]+)\\s*cM/i);
                                if (cmMatch) {
                                    yourCm = parseFloat(cmMatch[1].replace(/,/g, ''));
                                }
                                const relEl = yourDnaEl.querySelector('.relationshipLabel');
                                yourRelationship = relEl ? relEl.textContent.trim() : null;
                                const sideEl = yourDnaEl.querySelector('.familySideInfo');
                                if (sideEl) {
                                    const sideText = sideEl.textContent.toLowerCase();
                                    if (sideText.includes('both')) side = 'both';
                                    else if (sideText.includes('paternal')) side = 'paternal';
                                    else if (sideText.includes('maternal')) side = 'maternal';
                                    else if (sideText.includes('parent 1')) side = 'unknown';
                                    else if (sideText.includes('parent 2')) side = 'unknown';
                                }
                            }

                            // Get MATCH's shared cM from .matchSharedDNA
                            const matchDnaEl = entry.querySelector('.matchSharedDNA');
                            let matchCm = null;
                            let matchRelationship = null;
                            if (matchDnaEl) {
                                const matchText = matchDnaEl.textContent;
                                const cmMatch = matchText.match(/([\\d,]+)\\s*cM/i);
                                if (cmMatch) {
                                    matchCm = parseFloat(cmMatch[1].replace(/,/g, ''));
                                }
                                const relEl = matchDnaEl.querySelector('.relationshipLabel');
                                matchRelationship = relEl ? relEl.textContent.trim() : null;
                            }

                            // Extract GUID from link
                            let guid = null;
                            if (nameEl && nameEl.href) {
                                const guidMatch = nameEl.href.match(/with\\/([A-F0-9-]{36})/i);
                                if (guidMatch) guid = guidMatch[1].toUpperCase();
                            }

                            if (name) {
                                matches.push({
                                    name: name,
                                    your_cm: yourCm,
                                    your_relationship: yourRelationship,
                                    match_cm: matchCm,
                                    match_relationship: matchRelationship,
                                    side: side,
                                    guid: guid
                                });
                            }
                        } catch (e) {}
                    });
                    return matches;
                }
            """)

            print(f"\nShared matches with {match_full_name} ({match_cm} cM):")
            print("-" * 70)
            print(f"{'Name':<25} {'You':<12} {'Them':<12} {'Side':<10}")
            print("-" * 70)
            for m in shared_matches:
                you_cm = f"{m['your_cm']:.0f} cM" if m.get('your_cm') else "?"
                them_cm = f"{m['match_cm']:.0f} cM" if m.get('match_cm') else "?"
                side = m.get('side') or 'unknown'
                print(f"  {m['name']:<23} {you_cm:<12} {them_cm:<12} {side:<10}")
            print("-" * 70)
            print(f"Total: {len(shared_matches)} shared matches")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            context.close()
            browser.close()

    return shared_matches


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ancestry DNA Match Importer")
    parser.add_argument("--explore", action="store_true", help="Explore API to find pagination methods")
    parser.add_argument("--browser", action="store_true", help="Use Playwright browser automation (gets ALL matches)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (with --browser)")
    parser.add_argument("--shared", metavar="NAME", help="Get shared matches for a specific match")
    parser.add_argument("--scan-trees", action="store_true", help="Scan matches for tree info (size, public/private)")
    parser.add_argument("--scan-shared", action="store_true", help="Scan shared matches and store relationships in DB")
    parser.add_argument("--limit", type=int, help="Limit number of matches to process")
    parser.add_argument("--min-cm", type=float, help="Only process matches with at least this many cM")
    parser.add_argument("--test-guid", help="Use specific test GUID instead of auto-detecting")
    args = parser.parse_args()

    print("=" * 60)
    print("ANCESTRY DNA MATCH IMPORTER")
    print("=" * 60)

    # Check database
    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        sys.exit(1)

    # Shared matches mode
    if args.shared:
        fetch_shared_matches(args.shared, test_guid=args.test_guid, headless=args.headless)
        return

    # Scan trees mode
    if args.scan_trees:
        scan_trees(
            test_guid=args.test_guid,
            headless=args.headless,
            limit=args.limit,
            min_cm=args.min_cm
        )
        return

    # Scan shared matches mode
    if args.scan_shared:
        scan_shared_matches(
            test_guid=args.test_guid,
            headless=args.headless,
            limit=args.limit,
            min_cm=args.min_cm
        )
        return

    # Browser automation mode
    if args.browser:
        matches = fetch_matches_with_browser(test_guid=args.test_guid, headless=args.headless)

        if not matches:
            print("\nNo matches extracted. Check the saved HTML for debugging.")
            sys.exit(1)

        import_browser_matches(matches, DB_PATH)
        print("\nDone!")
        return

    # API mode (limited to 200 matches)
    # Create session
    session = create_session()
    if not session:
        sys.exit(1)

    # Get test GUID
    if args.test_guid:
        test_guid = args.test_guid
        print(f"\nUsing provided test GUID: {test_guid}")
    else:
        test_guid = get_test_guid(session)
        if not test_guid:
            print("\nERROR: Could not get your DNA test GUID.")
            print("Make sure you have a completed DNA test on Ancestry.")
            sys.exit(1)

    # Exploration mode
    if args.explore:
        explore_api_response(session, test_guid)
        print("\nExploration complete. Run without --explore to import matches.")
        return

    # Fetch all matches
    matches = fetch_all_matches(session, test_guid)

    if not matches:
        print("\nNo matches found. This might mean:")
        print("  - Your login session expired (log in again and close browser)")
        print("  - The API format has changed")
        sys.exit(1)

    # Import to database
    import_to_database(matches, DB_PATH)

    print("\nDone!")


if __name__ == "__main__":
    main()
