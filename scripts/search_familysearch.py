#!/usr/bin/env python3
"""
Search FamilySearch (familysearch.org) for UK census records.

FamilySearch is free (requires account for some features) and has the largest
collection of free genealogy records including UK censuses 1841-1911.

Usage:
    python scripts/search_familysearch.py --surname Wrathall
    python scripts/search_familysearch.py --surname Wrathall --forename Henry --birth-year 1863
    python scripts/search_familysearch.py --surname Virgo --year 1881 --store
"""

import argparse
import csv
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

# UK Census collection IDs on FamilySearch
UK_CENSUS_COLLECTIONS = {
    1841: "1493745",  # England and Wales Census, 1841
    1851: "1493747",  # England and Wales Census, 1851
    1861: "1493749",  # England and Wales Census, 1861
    1871: "1538354",  # England and Wales Census, 1871
    1881: "1416598",  # England and Wales Census, 1881
    1891: "1865747",  # England and Wales Census, 1891
    1901: "1888129",  # England and Wales Census, 1901
    1911: "1921547",  # England and Wales Census, 1911
}


def search_familysearch(surname, forename=None, birth_year=None, census_year=None,
                        birth_place=None, headless=True, max_results=50):
    """
    Search FamilySearch for census records using Selenium.
    Returns list of census record dictionaries.
    """
    results = []

    # Configure Chrome
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # FamilySearch works better with a realistic user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)

    try:
        # Build search URL
        # FamilySearch search URL format for historical records
        base_url = "https://www.familysearch.org/search/record/results"

        params = []
        params.append(f"q.surname={surname}")

        if forename:
            params.append(f"q.givenName={forename}")

        if birth_year:
            params.append(f"q.birthLikeDate.from={birth_year - 5}")
            params.append(f"q.birthLikeDate.to={birth_year + 5}")

        if birth_place:
            params.append(f"q.birthLikePlace={birth_place}")

        # Restrict to UK census collections
        if census_year and census_year in UK_CENSUS_COLLECTIONS:
            params.append(f"f.collectionId={UK_CENSUS_COLLECTIONS[census_year]}")
        else:
            # Search all UK census collections
            for year, coll_id in UK_CENSUS_COLLECTIONS.items():
                params.append(f"f.collectionId={coll_id}")

        # Add count parameter
        params.append(f"count={max_results}")

        url = base_url + "?" + "&".join(params)

        print(f"Searching FamilySearch...")
        print(f"URL: {url[:100]}...")
        driver.get(url)

        # Wait for results to load
        time.sleep(3)

        # Handle cookie consent if present
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
            cookie_btn.click()
            time.sleep(1)
        except:
            pass

        # Wait for search results
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='searchResult']"))
            )
        except:
            # Try alternative selectors
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "search-result"))
                )
            except:
                pass

        # Save screenshot for debugging
        driver.save_screenshot("/tmp/familysearch_results.png")

        # Save HTML for debugging
        with open('/tmp/familysearch_results.html', 'w') as f:
            f.write(driver.page_source)

        # Check for result count
        try:
            count_elem = driver.find_element(By.CSS_SELECTOR, "[data-testid='resultsCount']")
            print(f"Results: {count_elem.text}")
        except:
            # Try to find count in page
            match = re.search(r'(\d[\d,]*)\s*results?', driver.page_source, re.IGNORECASE)
            if match:
                print(f"Found {match.group(1)} results")

        # Parse results - FamilySearch uses various result formats
        results = parse_familysearch_results(driver)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot("/tmp/familysearch_error.png")

    finally:
        driver.quit()

    return results


def parse_familysearch_results(driver):
    """Parse FamilySearch search results."""
    results = []

    try:
        # FamilySearch uses data-testid or class-based selectors
        # Try multiple approaches

        # Method 1: Look for result rows with data-testid
        result_rows = driver.find_elements(By.CSS_SELECTOR, "[data-testid='searchResult']")

        if not result_rows:
            # Method 2: Look for result table rows
            result_rows = driver.find_elements(By.CSS_SELECTOR, "tr.search-result, .result-item")

        if not result_rows:
            # Method 3: Look for any result containers
            result_rows = driver.find_elements(By.CSS_SELECTOR, "[class*='result']")

        print(f"Found {len(result_rows)} result elements")

        for row in result_rows[:50]:  # Limit to first 50
            try:
                record = {}

                # Try to extract name
                name_elem = None
                for selector in ["[data-testid='name']", ".name", "a.result-name", "td:first-child a"]:
                    try:
                        name_elem = row.find_element(By.CSS_SELECTOR, selector)
                        break
                    except:
                        continue

                if name_elem:
                    record['name'] = name_elem.text.strip()
                else:
                    # Try getting text content
                    text = row.text.strip()
                    if text:
                        lines = text.split('\n')
                        if lines:
                            record['name'] = lines[0]

                if not record.get('name'):
                    continue

                # Try to extract other fields from row text or data attributes
                row_text = row.text.lower()

                # Look for year patterns
                year_match = re.search(r'\b(18[4-9]\d|19[01]\d)\b', row.text)
                if year_match:
                    record['year'] = year_match.group(1)

                # Look for age
                age_match = re.search(r'\bage[:\s]*(\d+)', row_text)
                if age_match:
                    record['age'] = age_match.group(1)

                # Look for birth year
                birth_match = re.search(r'birth[:\s]*(\d{4})', row_text)
                if birth_match:
                    record['birth_year'] = birth_match.group(1)

                # Look for place/location
                place_patterns = [
                    r'(england|wales|scotland|lancashire|yorkshire|london|westmorland|cumberland)',
                    r'birthplace[:\s]*([^,\n]+)',
                    r'residence[:\s]*([^,\n]+)'
                ]
                for pattern in place_patterns:
                    place_match = re.search(pattern, row_text, re.IGNORECASE)
                    if place_match:
                        record['place'] = place_match.group(1).strip()
                        break

                # Try to get link to full record
                try:
                    link = row.find_element(By.TAG_NAME, 'a')
                    record['url'] = link.get_attribute('href')
                except:
                    pass

                if record.get('name'):
                    results.append(record)

            except Exception as e:
                continue

        print(f"Parsed {len(results)} records")

    except Exception as e:
        print(f"Parse error: {e}")
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
        if r.get('year'):
            try:
                year = int(r['year'])
            except:
                pass

        age = None
        if r.get('age'):
            try:
                age = int(r['age'])
            except:
                pass

        name = r.get('name', '')

        # Check for existing record
        cursor.execute("""
            SELECT id FROM census_record
            WHERE year = ? AND name_as_recorded = ? AND source_url LIKE '%familysearch%'
        """, (year, name))

        existing = cursor.fetchone()
        if existing:
            census_id = existing[0]
        else:
            cursor.execute("""
                INSERT INTO census_record (
                    year, name_as_recorded, age_as_recorded,
                    registration_district, source_url
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                year,
                name,
                age,
                r.get('place', ''),
                r.get('url', 'https://familysearch.org')
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


def write_csv(results, surname=None, output_dir=None, append=False):
    """Write results to CSV file. Uses fixed filename, appends if file exists."""
    if not results:
        return None

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "output"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    filename = output_dir / "familysearch_results.csv"
    file_exists = filename.exists()
    mode = 'a' if append or file_exists else 'w'

    with open(filename, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header only if new file
        if mode == 'w' or not file_exists:
            writer.writerow(['census_year', 'name', 'age', 'relationship', 'occupation'])

        for r in results:
            writer.writerow([
                r.get('year', ''),
                r.get('name', ''),
                r.get('age', ''),
                r.get('relationship', ''),
                r.get('occupation', '')
            ])

    print(f"CSV written to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description='Search FamilySearch for UK census records')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--forename', help='Forename/given name to search')
    parser.add_argument('--birth-year', type=int, help='Birth year (±5 year range)')
    parser.add_argument('--birth-place', help='Birth place')
    parser.add_argument('--year', type=int, choices=[1841, 1851, 1861, 1871, 1881, 1891, 1901, 1911],
                       help='Census year (searches all UK censuses if not specified)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run headless (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show browser')
    parser.add_argument('--store', action='store_true', help='Store results in database')
    parser.add_argument('--person-id', type=int, help='Person ID to link results to')
    parser.add_argument('--max-results', type=int, default=50, help='Max results to return')
    parser.add_argument('--output-dir', help='Directory for CSV output')
    args = parser.parse_args()

    headless = not args.no_headless

    print(f"Searching FamilySearch for: {args.forename or ''} {args.surname}")
    print(f"Census year: {args.year or 'All UK censuses (1841-1911)'}")
    print(f"Mode: {'headless' if headless else 'visible'}\n")

    results = search_familysearch(
        surname=args.surname,
        forename=args.forename,
        birth_year=args.birth_year,
        census_year=args.year,
        birth_place=args.birth_place,
        headless=headless,
        max_results=args.max_results
    )

    if results:
        print(f"\n{'='*60}")
        print(f"Found {len(results)} results:")
        print('='*60)

        for i, r in enumerate(results, 1):
            print(f"\n[{i}]")
            for k, v in r.items():
                if v:
                    print(f"  {k}: {v}")

        # Always write CSV
        write_csv(results, args.surname, args.output_dir)

        if args.store:
            stored = store_results(results, args.person_id)
            print(f"\nStored {stored} new records in database.")
    else:
        print("\nNo results found.")
        print("Note: FamilySearch may require login for some searches.")
        print("Screenshot saved to /tmp/familysearch_results.png")


if __name__ == '__main__':
    main()
