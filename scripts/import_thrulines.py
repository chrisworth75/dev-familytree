#!/usr/bin/env python3
"""
Ancestry ThruLines Importer
Scrapes ThruLines page and imports ancestor paths and DNA match connections.

Usage:
    1. Log into Ancestry.com in Chrome (then close the browser)
    2. Activate venv: source venv/bin/activate
    3. Run: python import_thrulines.py [--headless]

This will:
- Navigate to your ThruLines page
- Extract all ancestor paths shown
- Import people into your tree (tree_id=1)
- Link DNA matches to their MRCAs
"""

import sqlite3
import json
import sys
import time
import re
import os
from datetime import datetime
from pathlib import Path

import browser_cookie3

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
ANCESTRY_BASE_URL = "https://www.ancestry.co.uk"


def get_cookies():
    """Extract Ancestry cookies from Chrome."""
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
        except Exception as e:
            print(f"  Warning: {domain}: {e}")

    print(f"  Found {len(cookie_list)} Ancestry cookies", flush=True)
    return cookie_list


def get_test_guid_and_tree(page):
    """Extract test GUID and tree ID from current URL or by navigating to DNA/ThruLines page."""
    guid = None
    tree_id = None

    # Check if already on a DNA page with GUID
    guid_match = re.search(
        r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
        page.url, re.IGNORECASE
    )
    if guid_match:
        guid = guid_match.group(1).upper()

    # Check for tree ID in URL (format: tree/123456789:1234:56)
    tree_match = re.search(r'/tree/(\d+:\d+:\d+)', page.url)
    if tree_match:
        tree_id = tree_match.group(1)

    if guid and tree_id:
        return guid, tree_id

    # Navigate to DNA page to get GUID
    print("  Navigating to DNA page to get credentials...", flush=True)
    page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="networkidle", timeout=60000)
    time.sleep(2)

    guid_match = re.search(
        r'/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})',
        page.url, re.IGNORECASE
    )
    if guid_match:
        guid = guid_match.group(1).upper()

    # Try to get tree ID from ThruLines page
    if guid:
        print("  Navigating to ThruLines to get tree ID...", flush=True)
        page.goto(f"{ANCESTRY_BASE_URL}/discoveryui-matches/thrulines/{guid}", wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Check if redirected to new URL format
        tree_match = re.search(r'/tree/(\d+:\d+:\d+)', page.url)
        if tree_match:
            tree_id = tree_match.group(1)
        else:
            # Try to find tree ID in page content
            tree_match = re.search(r'tree["\s:/]+(\d+:\d+:\d+)', page.content())
            if tree_match:
                tree_id = tree_match.group(1)

    return guid, tree_id


def extract_thrulines_data(page):
    """Extract ThruLines data from the page using JavaScript."""
    return page.evaluate("""
        () => {
            const results = {
                ancestors: [],
                dnaMatches: [],
                paths: []
            };

            // Find all ancestor cards - they have aria-label="ancestor" and data-ahnentafel
            const ancestorCards = document.querySelectorAll('.card[aria-label="ancestor"], div[aria-label="ancestor"]');

            ancestorCards.forEach((card) => {
                try {
                    // Get ahnentafel from the link inside the card
                    const link = card.querySelector('a[data-ahnentafel]');
                    const ahnentafel = link ? parseInt(link.getAttribute('data-ahnentafel')) : null;
                    const ancestryPersonId = link ? link.id : null;
                    const href = link ? link.getAttribute('href') : null;

                    // Extract name - look for the name inside cardContent
                    const nameEl = card.querySelector('.cardName, .name, h3, h4, .sampleName');
                    let name = nameEl ? nameEl.textContent.trim() : null;

                    // If no name element, try getting from any text content that looks like a name
                    if (!name) {
                        const allText = card.textContent;
                        // Look for patterns like "Jonathan P Worthington" or "Father"
                        const cardTextLines = allText.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
                        // First non-empty line that's not a relationship label is usually the name
                        for (const line of cardTextLines) {
                            if (line && !line.includes('Father') && !line.includes('Mother') &&
                                !line.includes('Grandfather') && !line.includes('Grandmother') &&
                                !line.includes('DNA') && !line.includes('matches') &&
                                !line.match(/^\\d{4}/) && line.length > 2) {
                                name = line;
                                break;
                            }
                        }
                    }

                    // Extract years/dates
                    let birthYear = null;
                    let deathYear = null;
                    const cardText = card.textContent;
                    const yearsMatch = cardText.match(/(\\d{4})\\s*[-–]\\s*(\\d{4})?/);
                    if (yearsMatch) {
                        birthYear = parseInt(yearsMatch[1]);
                        if (yearsMatch[2]) deathYear = parseInt(yearsMatch[2]);
                    }

                    // Extract relationship (Father, Mother, Grandfather, etc.)
                    let relationship = null;
                    const relPatterns = ['Father', 'Mother', 'Grandfather', 'Grandmother',
                                        'Great-grandfather', 'Great-grandmother', '2nd great',
                                        '3rd great', '4th great', '5th great'];
                    for (const pattern of relPatterns) {
                        if (cardText.includes(pattern)) {
                            const relMatch = cardText.match(new RegExp(pattern + '[^\\n]*', 'i'));
                            if (relMatch) {
                                relationship = relMatch[0].trim();
                                break;
                            }
                        }
                    }

                    // Check for DNA match count
                    let dnaMatchCount = 0;
                    const dnaMatch = cardText.match(/(\\d+)\\s*DNA\\s*match/i);
                    if (dnaMatch) {
                        dnaMatchCount = parseInt(dnaMatch[1]);
                    }

                    // Check for EVALUATE badge or "newancestor" badge
                    const evaluateBadge = card.querySelector('.newancestor, [class*="evaluate"]');
                    const needsEvaluation = !!evaluateBadge;

                    // Check if paternal or maternal
                    const isPaternal = card.classList.contains('paternal');
                    const isMaternal = card.classList.contains('maternal');
                    const side = isPaternal ? 'paternal' : (isMaternal ? 'maternal' : 'unknown');

                    if (ahnentafel) {
                        results.ancestors.push({
                            ahnentafel: ahnentafel,
                            ancestryPersonId: ancestryPersonId,
                            name: name,
                            birthYear: birthYear,
                            deathYear: deathYear,
                            relationship: relationship,
                            dnaMatchCount: dnaMatchCount,
                            needsEvaluation: needsEvaluation,
                            side: side,
                            href: href
                        });
                    }
                } catch (e) {
                    console.error('Error parsing card:', e);
                }
            });

            // Sort by ahnentafel
            results.ancestors.sort((a, b) => a.ahnentafel - b.ahnentafel);

            return results;
        }
    """)


def extract_ancestor_detail(page, ancestor_href, test_guid):
    """Navigate to an ancestor's detail page and extract descendant tree with DNA matches."""
    full_url = f"https://www.ancestry.co.uk{ancestor_href}"

    try:
        page.goto(full_url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Extract the descendant tree and DNA matches from the detail page
        data = page.evaluate("""
            () => {
                const results = {
                    ancestor: null,
                    descendants: [],
                    dnaMatches: [],
                    paths: []
                };

                // Get the main ancestor info
                const ancestorCard = document.querySelector('.ancestorHeader, .ancestor-header, [class*="ancestor"]');
                if (ancestorCard) {
                    const nameEl = ancestorCard.querySelector('.name, h1, h2');
                    results.ancestor = nameEl ? nameEl.textContent.trim() : null;
                }

                // Find all person nodes in the tree view
                const personNodes = document.querySelectorAll('.personNode, .person-node, [class*="person"], .node');

                personNodes.forEach((node) => {
                    try {
                        const nameEl = node.querySelector('.name, .personName, [class*="name"]');
                        const name = nameEl ? nameEl.textContent.trim() : null;

                        // Check for DNA match indicator
                        const cmEl = node.querySelector('[class*="cM"], [class*="shared"], .matchBadge');
                        let sharedCm = null;
                        let segments = null;
                        if (cmEl) {
                            const cmText = cmEl.textContent;
                            const cmMatch = cmText.match(/(\\d+)\\s*cM/i);
                            if (cmMatch) sharedCm = parseInt(cmMatch[1]);
                            const segMatch = cmText.match(/(\\d+)\\s*segment/i);
                            if (segMatch) segments = parseInt(segMatch[1]);
                        }

                        // Get birth/death years
                        let birthYear = null;
                        let deathYear = null;
                        const nodeText = node.textContent;
                        const yearsMatch = nodeText.match(/(\\d{4})\\s*[-–]\\s*(\\d{4})?/);
                        if (yearsMatch) {
                            birthYear = parseInt(yearsMatch[1]);
                            if (yearsMatch[2]) deathYear = parseInt(yearsMatch[2]);
                        }

                        // Get relationship text
                        const relEl = node.querySelector('.relationship, [class*="relation"]');
                        const relationship = relEl ? relEl.textContent.trim() : null;

                        if (name && name !== 'Unknown' && name !== 'Private') {
                            const person = {
                                name: name,
                                birthYear: birthYear,
                                deathYear: deathYear,
                                relationship: relationship,
                                sharedCm: sharedCm,
                                segments: segments,
                                isDnaMatch: sharedCm !== null
                            };

                            if (sharedCm !== null) {
                                results.dnaMatches.push(person);
                            } else {
                                results.descendants.push(person);
                            }
                        }
                    } catch (e) {}
                });

                // Also look for the tree structure/paths
                const treeContainer = document.querySelector('.thruLineTree, .tree-container, [class*="tree"]');
                if (treeContainer) {
                    // Extract any structured path data
                    const pathNodes = treeContainer.querySelectorAll('.pathNode, .path-node');
                    pathNodes.forEach((pn) => {
                        results.paths.push(pn.textContent.trim());
                    });
                }

                return results;
            }
        """)

        return data

    except Exception as e:
        print(f"    Error loading ancestor detail: {e}")
        return None


def scrape_ancestor_details(page, ancestors, test_guid, limit=10):
    """Scrape detailed info for ancestors with DNA matches."""
    detailed_ancestors = []

    # Filter to ancestors that have DNA matches
    with_matches = [a for a in ancestors if a.get('dnaMatchCount', 0) > 0]

    print(f"\nFound {len(with_matches)} ancestors with DNA matches")

    for i, ancestor in enumerate(with_matches[:limit]):
        href = ancestor.get('href')
        if not href:
            continue

        print(f"\n[{i+1}/{min(limit, len(with_matches))}] {ancestor.get('name')} (Ahn {ancestor.get('ahnentafel')}, {ancestor.get('dnaMatchCount')} matches)")

        detail = extract_ancestor_detail(page, href, test_guid)
        if detail:
            ancestor['detail'] = detail
            detailed_ancestors.append(ancestor)
            print(f"    Found {len(detail.get('descendants', []))} descendants, {len(detail.get('dnaMatches', []))} DNA matches")

        time.sleep(1)  # Be gentle on the server

    return detailed_ancestors


def import_person_to_tree(cursor, name, birth_year=None, death_year=None, relationship=None, tree_id=1):
    """Import a person into the tree if they don't exist."""
    # Parse name into forename/surname
    parts = name.split()
    if len(parts) >= 2:
        forename = ' '.join(parts[:-1])
        surname = parts[-1]
    else:
        forename = name
        surname = ''

    # Check if exists
    cursor.execute("""
        SELECT id FROM person
        WHERE tree_id = ? AND forename = ? AND surname = ?
        AND (birth_year_estimate = ? OR birth_year_estimate IS NULL OR ? IS NULL)
    """, (tree_id, forename, surname, birth_year, birth_year))

    existing = cursor.fetchone()
    if existing:
        return existing[0], False  # id, was_created

    # Insert
    cursor.execute("""
        INSERT INTO person (tree_id, forename, surname, birth_year_estimate, death_year_estimate, notes, source)
        VALUES (?, ?, ?, ?, ?, ?, 'thrulines')
    """, (tree_id, forename, surname, birth_year, death_year, relationship))

    return cursor.lastrowid, True


def update_dna_match_mrca(cursor, match_name, mrca_text, confidence='confirmed'):
    """Update a DNA match's MRCA field."""
    cursor.execute("""
        UPDATE dna_match
        SET mrca = ?, mrca_confidence = ?, confirmed = 1
        WHERE name LIKE ?
    """, (mrca_text, confidence, f"%{match_name}%"))
    return cursor.rowcount


def scrape_thrulines(headless=False, ancestor_filter=None):
    """Main function to scrape ThruLines."""
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("ANCESTRY THRULINES IMPORTER")
    print("=" * 60)

    cookie_list = get_cookies()
    if not cookie_list:
        print("\nNo cookies found. Please:")
        print("  1. Open Chrome and log into Ancestry")
        print("  2. Close Chrome completely")
        print("  3. Run this script again")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with sync_playwright() as p:
        print("\nLaunching browser...", flush=True)
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        try:
            # Get test GUID and tree ID
            print("Getting test GUID and tree ID...", flush=True)
            test_guid, tree_id = get_test_guid_and_tree(page)
            if not test_guid:
                print("Could not get test GUID. Are you logged in?")
                return

            print(f"Test GUID: {test_guid}", flush=True)
            print(f"Tree ID: {tree_id}", flush=True)

            # Navigate to ThruLines - try multiple URL patterns
            thrulines_urls = [
                f"{ANCESTRY_BASE_URL}/discoveryui-geneticfamily/thrulines/tree/{tree_id}/for/{test_guid}" if tree_id else None,
                f"{ANCESTRY_BASE_URL}/dna/insights/{test_guid}/thrulines",
                f"{ANCESTRY_BASE_URL}/discoveryui-matches/thrulines/{test_guid}",
                f"{ANCESTRY_BASE_URL}/dna/insights/{test_guid}/matches/thrulines",
            ]
            thrulines_urls = [u for u in thrulines_urls if u]  # Remove None

            thrulines_loaded = False
            for thrulines_url in thrulines_urls:
                print(f"\nTrying: {thrulines_url}", flush=True)
                page.goto(thrulines_url, wait_until="networkidle", timeout=60000)
                time.sleep(3)

                # Check if we got an error page
                if "sorry" not in page.content().lower() and "no longer available" not in page.content().lower():
                    thrulines_loaded = True
                    break

            if not thrulines_loaded:
                # Try navigating from DNA home and clicking ThruLines
                print("\nDirect URLs failed. Navigating via DNA home...", flush=True)
                page.goto(f"{ANCESTRY_BASE_URL}/dna/insights/{test_guid}", wait_until="networkidle", timeout=60000)
                time.sleep(3)

                # Look for ThruLines link/tab
                try:
                    thrulines_link = page.query_selector('a[href*="thrulines"], a:has-text("ThruLines"), [data-testid*="thrulines"]')
                    if thrulines_link:
                        thrulines_link.click()
                        time.sleep(3)
                        thrulines_loaded = True
                        print(f"Clicked ThruLines link, now at: {page.url}", flush=True)
                except Exception as e:
                    print(f"Could not find ThruLines link: {e}")

            print(f"Final URL: {page.url}", flush=True)

            # Check if we're on the right page
            if "sign-in" in page.url.lower():
                print("\nNot logged in! Please log into Ancestry in Chrome first.")
                return

            # Save screenshot for debugging
            page.screenshot(path="/tmp/thrulines_debug.png")
            print("Saved screenshot to /tmp/thrulines_debug.png", flush=True)

            # Save HTML for analysis
            html = page.content()
            with open("/tmp/thrulines.html", "w") as f:
                f.write(html)
            print("Saved HTML to /tmp/thrulines.html", flush=True)

            # Wait for content to load
            print("\nWaiting for ThruLines to load...", flush=True)
            time.sleep(5)

            # Scroll to load more ancestors
            print("Scrolling to load all ancestors...", flush=True)
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            # Extract data
            print("\nExtracting ThruLines data...", flush=True)
            data = extract_thrulines_data(page)

            print(f"\nFound:")
            print(f"  Ancestors: {len(data.get('ancestors', []))}")
            print(f"  DNA matches: {len(data.get('dnaMatches', []))}")

            if data.get('rawData'):
                print("  Raw JSON data found (will parse separately)")

            # Import ancestors
            imported_people = 0
            imported_matches = 0

            print("\n" + "-" * 40)
            print("IMPORTING ANCESTORS")
            print("-" * 40)

            for ancestor in data.get('ancestors', []):
                name = ancestor.get('name')
                if not name or name == 'Unknown' or name == 'Private':
                    continue

                if ancestor_filter and ancestor_filter.lower() not in name.lower():
                    continue

                person_id, was_created = import_person_to_tree(
                    cursor,
                    name,
                    birth_year=ancestor.get('birthYear'),
                    death_year=ancestor.get('deathYear'),
                    relationship=ancestor.get('relationship')
                )

                if was_created:
                    imported_people += 1
                    status = "NEW"
                else:
                    status = "exists"

                eval_mark = " [EVALUATE]" if ancestor.get('needsEvaluation') else ""
                print(f"  {name} ({ancestor.get('birthYear', '?')}-{ancestor.get('deathYear', '?')}) - {status}{eval_mark}")

            conn.commit()

            # Update DNA matches with MRCA info
            print("\n" + "-" * 40)
            print("UPDATING DNA MATCHES")
            print("-" * 40)

            for match in data.get('dnaMatches', []):
                name = match.get('name')
                if not name:
                    continue

                # The relationship field often contains the MRCA info
                relationship = match.get('relationship', '')

                # Try to update in database
                updated = cursor.execute("""
                    UPDATE dna_match
                    SET mrca_confidence = 'confirmed', confirmed = 1
                    WHERE name LIKE ? AND mrca IS NULL
                """, (f"%{name}%",)).rowcount

                cm_str = f"{match.get('sharedCm')} cM" if match.get('sharedCm') else "? cM"
                if updated:
                    imported_matches += 1
                    print(f"  {name} ({cm_str}) - {relationship} - UPDATED")
                else:
                    print(f"  {name} ({cm_str}) - {relationship}")

            conn.commit()

            # Now drill into ancestors to get descendant details
            # Focus on earlier generations (higher ahnentafel numbers) that are more likely to have matches
            priority_ancestors = [a for a in data.get('ancestors', []) if a.get('ahnentafel', 0) >= 16]
            priority_ancestors.sort(key=lambda x: x.get('ahnentafel', 0))

            if priority_ancestors:
                print(f"\n" + "-" * 40)
                print(f"DRILLING INTO ANCESTOR DETAILS")
                print("-" * 40)

                for ancestor in priority_ancestors[:20]:  # Limit to 20 ancestors
                    href = ancestor.get('href')
                    ahnentafel = ancestor.get('ahnentafel')
                    name = ancestor.get('name', 'Unknown')

                    if not href:
                        continue

                    print(f"\n[Ahn {ahnentafel}] {name}")

                    try:
                        page.goto(f"https://www.ancestry.co.uk{href}", wait_until="networkidle", timeout=60000)
                        time.sleep(2)

                        # Save screenshot for debugging
                        page.screenshot(path=f"/tmp/thrulines_ahn{ahnentafel}.png")

                        # Extract people from this ancestor's ThruLine view
                        detail_data = page.evaluate("""
                            () => {
                                const results = {
                                    descendants: [],
                                    dnaMatches: []
                                };

                                // Find DNA matches - they have cM values displayed
                                // Look for elements containing "cM" which indicate DNA matches
                                const allElements = document.querySelectorAll('*');
                                allElements.forEach(el => {
                                    const text = el.textContent;
                                    // Match pattern like "48 cM | 3 segments" or just "48 cM"
                                    if (text.match(/\\d+\\s*cM/) && el.children.length === 0) {
                                        // This is likely a cM display element
                                        // Look for the match name in nearby/parent elements
                                        let parent = el.parentElement;
                                        for (let i = 0; i < 5 && parent; i++) {
                                            const parentText = parent.textContent;
                                            // Look for name pattern (not containing common relationship words as the start)
                                            const lines = parentText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                                            for (const line of lines) {
                                                // Skip relationship labels and common words
                                                if (line.match(/^(\\d|Half|cousin|removed|great|Grand|uncle|aunt|Private|EVALUATE)/i)) continue;
                                                if (line.match(/cM|segment/i)) continue;
                                                // This might be a name
                                                if (line.length > 2 && line.length < 50 && !line.includes('ThruLines')) {
                                                    const cmMatch = parentText.match(/(\\d+)\\s*cM/);
                                                    const segMatch = parentText.match(/(\\d+)\\s*segment/i);
                                                    if (cmMatch) {
                                                        results.dnaMatches.push({
                                                            name: line,
                                                            sharedCm: parseInt(cmMatch[1]),
                                                            segments: segMatch ? parseInt(segMatch[1]) : null
                                                        });
                                                        return; // Found this match, move on
                                                    }
                                                }
                                            }
                                            parent = parent.parentElement;
                                        }
                                    }
                                });

                                // Also look for match avatars/cards with names
                                const matchCards = document.querySelectorAll('[class*="match"], [class*="dna"], [class*="leaf"]');
                                matchCards.forEach(card => {
                                    const text = card.textContent;
                                    const cmMatch = text.match(/(\\d+)\\s*cM/);
                                    if (cmMatch) {
                                        // Extract name - first line that's not a relationship
                                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 2);
                                        for (const line of lines) {
                                            if (!line.match(/^(\\d|Half|cousin|removed|great|Grand|cM|segment)/i)) {
                                                results.dnaMatches.push({
                                                    name: line.substring(0, 40),
                                                    sharedCm: parseInt(cmMatch[1]),
                                                    segments: null
                                                });
                                                break;
                                            }
                                        }
                                    }
                                });

                                // Deduplicate matches by name
                                const seen = new Set();
                                results.dnaMatches = results.dnaMatches.filter(m => {
                                    if (seen.has(m.name)) return false;
                                    seen.add(m.name);
                                    return true;
                                });

                                // Count descendants (people with birth years)
                                const personCards = document.querySelectorAll('[class*="person"], [class*="node"]');
                                personCards.forEach(card => {
                                    const text = card.textContent;
                                    if (text.match(/\\d{4}\\s*[-–]/)) {
                                        results.descendants.push({text: text.substring(0, 100)});
                                    }
                                });

                                return results;
                            }
                        """)

                        if detail_data.get('dnaMatches'):
                            print(f"    DNA Matches found: {len(detail_data['dnaMatches'])}")
                            for match in detail_data['dnaMatches'][:5]:
                                print(f"      - {match.get('name')} ({match.get('sharedCm')} cM)")

                                # Update DNA match in database with this MRCA
                                mrca_text = f"{ahnentafel} ({name})"
                                cursor.execute('''
                                    UPDATE dna_match
                                    SET mrca = ?, mrca_confidence = 'thrulines'
                                    WHERE name LIKE ? AND mrca IS NULL
                                ''', (mrca_text, f"%{match.get('name', '')}%"))
                                if cursor.rowcount > 0:
                                    imported_matches += 1

                        if detail_data.get('descendants'):
                            print(f"    Descendants found: {len(detail_data['descendants'])}")

                        conn.commit()

                    except Exception as e:
                        print(f"    Error: {e}")

                    time.sleep(1)

            # Summary
            print("\n" + "=" * 60)
            print("IMPORT COMPLETE")
            print("=" * 60)
            print(f"  New people imported: {imported_people}")
            print(f"  DNA matches updated: {imported_matches}")

            # Show tree stats
            cursor.execute("SELECT COUNT(*) FROM person WHERE tree_id = 1")
            total = cursor.fetchone()[0]
            print(f"  Total people in tree: {total}")

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()

        finally:
            print("\nClosing browser...", flush=True)
            context.close()
            browser.close()

    conn.close()


def list_thrulines_ancestors(headless=True):
    """List all ancestors shown in ThruLines without importing."""
    from playwright.sync_api import sync_playwright

    print("\n" + "=" * 60)
    print("LISTING THRULINES ANCESTORS")
    print("=" * 60)

    cookie_list = get_cookies()
    if not cookie_list:
        print("No cookies found.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookie_list)
        page = context.new_page()

        try:
            test_guid, tree_id = get_test_guid_and_tree(page)
            if not test_guid:
                return

            # Try new URL format first, then old
            if tree_id:
                thrulines_url = f"{ANCESTRY_BASE_URL}/discoveryui-geneticfamily/thrulines/tree/{tree_id}/for/{test_guid}"
            else:
                thrulines_url = f"{ANCESTRY_BASE_URL}/discoveryui-matches/thrulines/{test_guid}"

            print(f"Navigating to: {thrulines_url}", flush=True)
            page.goto(thrulines_url, wait_until="networkidle", timeout=60000)
            time.sleep(5)

            # Scroll to load
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)

            data = extract_thrulines_data(page)

            print("\nANCESTORS:")
            print("-" * 50)
            for a in data.get('ancestors', []):
                years = f"{a.get('birthYear', '?')}-{a.get('deathYear', '?')}"
                eval_mark = " [EVALUATE]" if a.get('needsEvaluation') else ""
                print(f"  {a.get('name'):<30} {years:<15} {a.get('relationship', '')}{eval_mark}")

            print("\nDNA MATCHES:")
            print("-" * 50)
            for m in data.get('dnaMatches', []):
                cm = f"{m.get('sharedCm')} cM" if m.get('sharedCm') else "? cM"
                print(f"  {m.get('name'):<30} {cm:<10} {m.get('relationship', '')}")

        finally:
            context.close()
            browser.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import ThruLines data from Ancestry")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--list", action="store_true", help="List ancestors without importing")
    parser.add_argument("--filter", type=str, help="Only import ancestors matching this name")
    args = parser.parse_args()

    if args.list:
        list_thrulines_ancestors(headless=args.headless)
    else:
        scrape_thrulines(headless=args.headless, ancestor_filter=args.filter)


if __name__ == "__main__":
    main()
