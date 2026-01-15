#!/usr/bin/env python3
"""
Search UK Census Online (ukcensusonline.com) for census records.

Uses undetected-chromedriver with CAPTCHA solving service for automation.

Setup:
    pip install undetected-chromedriver requests

    Set CAPSOLVER_API_KEY environment variable for automated CAPTCHA solving.
    Get an API key from https://www.capsolver.com/ (costs ~$0.002 per solve)

Usage:
    # Manual mode (visible browser, solve CAPTCHA yourself)
    python scripts/search_ukcensus_online.py --surname Wrathall --forename Leslie --no-headless

    # Automated mode (requires CAPSOLVER_API_KEY)
    CAPSOLVER_API_KEY=xxx python scripts/search_ukcensus_online.py --surname Wrathall --forename Leslie

    # Store results in database
    python scripts/search_ukcensus_online.py --surname Wrathall --birth-year 1904 --store --person-id 123
"""

import argparse
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DB_PATH = Path(__file__).parent.parent / "genealogy.db"
CAPSOLVER_API_KEY = os.environ.get('CAPSOLVER_API_KEY')


def solve_turnstile(site_key, page_url):
    """
    Solve Cloudflare Turnstile CAPTCHA using CapSolver API.
    Returns the solution token or None if failed.
    """
    if not CAPSOLVER_API_KEY:
        return None

    print("Solving Turnstile CAPTCHA via CapSolver...")

    # Create task
    create_response = requests.post(
        'https://api.capsolver.com/createTask',
        json={
            'clientKey': CAPSOLVER_API_KEY,
            'task': {
                'type': 'AntiTurnstileTaskProxyLess',
                'websiteURL': page_url,
                'websiteKey': site_key,
            }
        }
    )
    create_data = create_response.json()

    if create_data.get('errorId', 0) != 0:
        print(f"CapSolver error: {create_data.get('errorDescription')}")
        return None

    task_id = create_data.get('taskId')
    print(f"Task created: {task_id}")

    # Poll for result
    for _ in range(60):  # Wait up to 60 seconds
        time.sleep(2)
        result_response = requests.post(
            'https://api.capsolver.com/getTaskResult',
            json={
                'clientKey': CAPSOLVER_API_KEY,
                'taskId': task_id
            }
        )
        result_data = result_response.json()

        status = result_data.get('status')
        if status == 'ready':
            token = result_data.get('solution', {}).get('token')
            print("CAPTCHA solved successfully!")
            return token
        elif status == 'failed':
            print(f"CAPTCHA solving failed: {result_data.get('errorDescription')}")
            return None
        # Still processing, continue polling

    print("CAPTCHA solving timed out")
    return None


def get_turnstile_sitekey(driver):
    """Extract Turnstile sitekey from the page."""
    try:
        # Look for cf-turnstile div with data-sitekey attribute
        turnstile_div = driver.find_element(By.CSS_SELECTOR, '[data-sitekey]')
        return turnstile_div.get_attribute('data-sitekey')
    except:
        pass

    # Try finding in page source via regex
    page_source = driver.page_source
    match = re.search(r'data-sitekey="([^"]+)"', page_source)
    if match:
        return match.group(1)

    # Try finding in script
    match = re.search(r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)', page_source)
    if match:
        return match.group(1)

    return None


def inject_turnstile_token(driver, token):
    """Inject solved CAPTCHA token and submit."""
    try:
        # Find the turnstile response input and set the token
        driver.execute_script(f'''
            // Try to find and set the turnstile response
            var inputs = document.querySelectorAll('input[name="cf-turnstile-response"]');
            for (var i = 0; i < inputs.length; i++) {{
                inputs[i].value = "{token}";
            }}

            // Also try setting via callback if available
            if (typeof turnstile !== 'undefined' && turnstile.execute) {{
                // Already executed
            }}

            // Try submitting any form on the page
            var forms = document.querySelectorAll('form');
            if (forms.length > 0) {{
                forms[0].submit();
            }}
        ''')
        return True
    except Exception as e:
        print(f"Error injecting token: {e}")
        return False


def build_search_url(surname, forename=None, birth_year=None, census_year=None):
    """Build the search URL with parameters."""
    params = {
        'layout': 'compact',
        'type': 'person',
        'source': '',
        'include_uk': '1',
        'include_ireland': '1',
        'include_elsewhere': '1',
        'master_event': '',
        'person_event': '',
        'fn': forename or '',
        'sn': surname,
        'yr': birth_year or '',
        'range': '5',
        'kw': '',
        'kw_mode': 'simple',
        'kw_simple_type': 'any',
        'search': 'Search',
    }
    return f"https://ukcensusonline.com/search/free/?{urlencode(params)}"


def search_census(surname, forename=None, birth_year=None, census_year=None, headless=True):
    """
    Search UK Census Online using undetected Chrome.
    """
    results = []
    search_url = build_search_url(surname, forename, birth_year, census_year)
    print(f"Search URL: {search_url}\n")

    # Configure Chrome options
    options = uc.ChromeOptions()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    # Use undetected Chrome driver
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        print("Loading search results...")
        driver.get(search_url)
        time.sleep(3)  # Initial wait

        # Check for Cloudflare challenge
        page_loaded = False
        for attempt in range(3):
            page_source = driver.page_source

            # Check if we're past the challenge - look for results indicator
            if re.search(r'Found \d+ Results', page_source) or 'Master Search' in page_source:
                print("Page loaded successfully!")
                page_loaded = True
                break

            # Check for Turnstile challenge
            page_lower = page_source.lower()
            if "verify you are human" in page_lower or "challenge" in page_lower:
                print(f"Cloudflare challenge detected (attempt {attempt + 1})")

                if CAPSOLVER_API_KEY:
                    # Try to solve automatically
                    site_key = get_turnstile_sitekey(driver)
                    if site_key:
                        print(f"Found sitekey: {site_key}")
                        token = solve_turnstile(site_key, search_url)
                        if token:
                            inject_turnstile_token(driver, token)
                            time.sleep(3)
                            continue
                    else:
                        print("Could not find Turnstile sitekey")

                if not headless:
                    # Manual mode - wait for user to solve
                    print("Please solve the CAPTCHA in the browser...")
                    for _ in range(120):  # Wait up to 2 minutes
                        time.sleep(1)
                        if re.search(r'Found \d+ Results', driver.page_source):
                            page_loaded = True
                            break
                    if page_loaded:
                        break
                else:
                    print("Cannot solve CAPTCHA in headless mode without API key")
                    print("Set CAPSOLVER_API_KEY or use --no-headless for manual mode")
                    break
            else:
                time.sleep(2)

        # Extra wait for page to stabilize
        time.sleep(2)

        # Save screenshot
        driver.save_screenshot("/tmp/ukcensus_results.png")
        print(f"Screenshot saved: /tmp/ukcensus_results.png")

        # Always save HTML for debugging and check for results
        page_source = driver.page_source
        with open("/tmp/ukcensus_results.html", "w") as f:
            f.write(page_source)
        print("HTML saved: /tmp/ukcensus_results.html")

        # Check if we have results
        if re.search(r'Found \d+ Results', page_source) or 'Census' in page_source:
            # Parse results
            results = parse_results(driver)
        else:
            print("Page may not have loaded correctly - check screenshot")

    finally:
        driver.quit()

    return results


def parse_results(driver):
    """Parse search results from the page."""
    results = []

    try:
        page_source = driver.page_source

        # Check for "Found X Results" to confirm we have data
        match = re.search(r'Found (\d+) Results', page_source)
        if match:
            print(f"Found {match.group(1)} total results on page")

        # Get body text for parsing
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        print(f"\nPage text length: {len(body_text)} chars")

        # Parse results - format is like (labels and values on SEPARATE lines):
        # "Lancashire 1911 Census"
        # "Name:"
        # "Leslie Gordon Wrathall"
        # "Age:"
        # "6"

        lines = body_text.split('\n')
        current_record = None
        pending_field = None  # Track which field we're expecting a value for

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for census header (e.g., "Lancashire 1911 Census")
            census_match = re.match(r'^(\w+(?:\s+\w+)*)\s+(\d{4})\s+Census$', line)
            if census_match:
                # Save previous record if exists and is census
                if current_record and current_record.get('name') and 'Census' in current_record.get('record_type', ''):
                    results.append(current_record)

                county = census_match.group(1)
                year = census_match.group(2)
                current_record = {
                    'record_type': f'{county} {year} Census',
                    'year': year,
                    'county': county
                }
                pending_field = None
                continue

            # Check for BMD header (skip these records)
            if re.match(r'^BMD Records', line):
                if current_record and current_record.get('name') and 'Census' in current_record.get('record_type', ''):
                    results.append(current_record)
                current_record = {'record_type': 'BMD'}  # Placeholder to skip BMD records
                pending_field = None
                continue

            # Parse field values if we're in a record
            if current_record:
                # Check if this is a field label (value comes on next line)
                if line == 'Name:':
                    pending_field = 'name'
                    continue
                elif line == 'Age:':
                    pending_field = 'age'
                    continue
                elif line == 'Born Approx:':
                    pending_field = 'born_approx'
                    continue
                elif line == 'County:':
                    pending_field = 'county_field'
                    continue
                elif line == 'Year:':
                    pending_field = 'year_field'
                    continue

                # If we're expecting a value, store it
                if pending_field:
                    if pending_field == 'name':
                        current_record['name'] = line
                    elif pending_field == 'age':
                        age_match = re.match(r'^(\d+)', line)
                        if age_match:
                            current_record['age'] = age_match.group(1)
                    elif pending_field == 'born_approx':
                        born_match = re.match(r'^(\d{4})', line)
                        if born_match:
                            current_record['born_approx'] = born_match.group(1)
                    elif pending_field == 'county_field':
                        current_record['county'] = line
                    elif pending_field == 'year_field':
                        year_match = re.match(r'^(\d{4})', line)
                        if year_match:
                            current_record['year'] = year_match.group(1)
                    pending_field = None

        # Don't forget the last record
        if current_record and current_record.get('name') and 'Census' in current_record.get('record_type', ''):
            results.append(current_record)

        print(f"\nParsed {len(results)} census records")

        # Debug output
        if results:
            print(f"First result: {results[0]}")

    except Exception as e:
        print(f"Error parsing results: {e}")
        import traceback
        traceback.print_exc()

    return results


def store_results(results, person_id=None):
    """Store census results in the database."""
    if not results:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    stored = 0

    for r in results:
        year = None
        year_str = r.get('year', '')
        if year_str:
            try:
                year = int(year_str)
            except:
                pass

        age_int = None
        age_str = r.get('age', '')
        if age_str:
            try:
                age_int = int(age_str)
            except:
                pass

        cursor.execute("""
            INSERT INTO census_record (
                year, name_as_recorded, age_as_recorded,
                registration_district, source_url
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            year,
            r.get('name', ''),
            age_int,
            r.get('county', ''),
            'ukcensusonline.com'
        ))
        census_id = cursor.lastrowid
        stored += 1

        if person_id:
            cursor.execute("""
                INSERT OR IGNORE INTO person_census (person_id, census_record_id)
                VALUES (?, ?)
            """, (person_id, census_id))

    conn.commit()
    conn.close()
    return stored


def main():
    parser = argparse.ArgumentParser(description='Search UK Census Online')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--forename', help='Forename to search')
    parser.add_argument('--birth-year', type=int, help='Birth year')
    parser.add_argument('--year', type=int, help='Census year (1841-1911)')
    parser.add_argument('--headless', action='store_true', default=True)
    parser.add_argument('--no-headless', action='store_true', help='Show browser for manual CAPTCHA')
    parser.add_argument('--store', action='store_true', help='Store in database')
    parser.add_argument('--person-id', type=int, help='Person ID to link')
    args = parser.parse_args()

    headless = not args.no_headless

    print(f"Searching UK Census Online for: {args.forename or ''} {args.surname}")
    print(f"Mode: {'headless' if headless else 'visible'}")
    if CAPSOLVER_API_KEY:
        print("CAPTCHA solver: CapSolver API enabled")
    else:
        print("CAPTCHA solver: None (set CAPSOLVER_API_KEY for automation)")
    print()

    results = search_census(
        surname=args.surname,
        forename=args.forename,
        birth_year=args.birth_year,
        census_year=args.year,
        headless=headless
    )

    if results:
        print(f"\n{'='*60}")
        print(f"Found {len(results)} census records:")
        print('='*60)

        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {r.get('record_type', 'Unknown')}")
            for k, v in r.items():
                if v and k != 'record_type':
                    print(f"    {k}: {v}")

        if args.store:
            stored = store_results(results, args.person_id)
            print(f"\nStored {stored} records in database.")
    else:
        print("\nNo results found.")


if __name__ == '__main__':
    main()
