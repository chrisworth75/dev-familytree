#!/usr/bin/env python3
"""
Search FreeBMD (freebmd.org.uk) for UK birth, marriage, and death index records.

FreeBMD is free and provides GRO index references for BMD records 1837-1983.
No images, but provides the volume/page references needed to order certificates.

Usage:
    python scripts/search_freebmd.py --surname Wrathall --type births
    python scripts/search_freebmd.py --surname Wrathall --forename Henry --type births --year 1863
    python scripts/search_freebmd.py --surname Wrathall --type deaths --year-from 1920 --year-to 1930
    python scripts/search_freebmd.py --surname Virgo --type marriages --store
"""

import argparse
import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

DB_PATH = Path(__file__).parent.parent / "genealogy.db"


def search_freebmd(surname, record_type='births', forename=None, year=None,
                   year_from=None, year_to=None, district=None, headless=True):
    """
    Search FreeBMD for BMD index records using Selenium.
    record_type: 'births', 'marriages', or 'deaths'
    Returns list of index record dictionaries.
    """
    results = []

    # Configure Chrome
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        print(f"Loading FreeBMD search page...")
        driver.get("https://www.freebmd.org.uk/cgi/search.pl")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "surname"))
        )
        time.sleep(2)

        # Handle cookie consent popup (Google/partner consent)
        try:
            # Look for AGREE button in consent popup
            agree_selectors = [
                "//button[contains(text(), 'AGREE')]",
                "//button[contains(@class, 'css') and contains(text(), 'AGREE')]",
                "//button[@mode='primary']",
            ]
            for selector in agree_selectors:
                try:
                    agree_btn = driver.find_element(By.XPATH, selector)
                    driver.execute_script("arguments[0].click();", agree_btn)
                    print("Clicked cookie consent AGREE")
                    time.sleep(2)
                    break
                except:
                    continue

            # Also try JavaScript approach
            driver.execute_script("""
                var buttons = document.querySelectorAll('button');
                for (var btn of buttons) {
                    if (btn.textContent.includes('AGREE')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)
            time.sleep(1)
        except Exception as e:
            print(f"Cookie consent handling: {e}")

        # Fill in surname - wait for it to be clickable
        surname_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.NAME, "surname"))
        )
        surname_field.clear()
        surname_field.send_keys(surname)

        # Fill in forename if provided
        if forename:
            forename_field = driver.find_element(By.NAME, "forename1")
            forename_field.clear()
            forename_field.send_keys(forename)

        # Select record type via checkboxes
        # FreeBMD uses checkboxes: All, Births, Deaths, Marriages
        try:
            if record_type == 'all':
                # Check the "All" checkbox
                all_checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and @value='All']")
                if not all_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", all_checkbox)
            else:
                # Uncheck "All" if checked, then check specific type
                type_value_map = {
                    'births': 'Births',
                    'marriages': 'Marriages',
                    'deaths': 'Deaths'
                }
                checkbox_value = type_value_map.get(record_type, 'Births')
                checkbox = driver.find_element(By.XPATH, f"//input[@type='checkbox' and @value='{checkbox_value}']")
                if not checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", checkbox)
                print(f"Selected type: {checkbox_value}")
        except Exception as e:
            print(f"Type selection: {e}")

        # Set year range
        if year:
            year_from = year
            year_to = year

        if year_from:
            try:
                start_field = driver.find_element(By.NAME, "start")
                start_field.clear()
                start_field.send_keys(str(year_from))
            except:
                pass

        if year_to:
            try:
                end_field = driver.find_element(By.NAME, "end")
                end_field.clear()
                end_field.send_keys(str(year_to))
            except:
                pass

        # Set district if provided
        if district:
            try:
                district_field = driver.find_element(By.NAME, "district")
                district_field.clear()
                district_field.send_keys(district)
            except:
                pass

        # Submit search - Find button is input type="image" name="find"
        submit_btn = None
        submit_selectors = [
            (By.CSS_SELECTOR, "input[type='image'][name='find']"),
            (By.CSS_SELECTOR, "input[name='find']"),
            (By.XPATH, "//input[@name='find']"),
            (By.XPATH, "//input[contains(@src, 'Find')]"),
            (By.XPATH, "//input[@value='Find']"),
        ]
        for by, selector in submit_selectors:
            try:
                submit_btn = driver.find_element(by, selector)
                print(f"Found submit button: {selector}")
                break
            except:
                continue

        if submit_btn:
            driver.execute_script("arguments[0].click();", submit_btn)
        else:
            # Try form submit as fallback
            form = driver.find_element(By.TAG_NAME, "form")
            form.submit()
            print("Submitted form directly")

        # Wait for results
        time.sleep(3)

        # Save screenshot
        driver.save_screenshot("/tmp/freebmd_results.png")

        # Save HTML for debugging
        with open('/tmp/freebmd_results.html', 'w') as f:
            f.write(driver.page_source)

        # Check for result count
        page_text = driver.page_source
        match = re.search(r'Found\s+(\d+)\s+match', page_text, re.IGNORECASE)
        if match:
            print(f"Found {match.group(1)} matches")

        # Parse results
        results = parse_freebmd_results(driver, record_type)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot("/tmp/freebmd_error.png")

    finally:
        driver.quit()

    return results


def parse_freebmd_results(driver, record_type):
    """Parse FreeBMD search results table."""
    results = []

    try:
        # FreeBMD results are grouped by quarter with headers like "Births Mar 1863"
        # Each data row has: Surname, First name(s), [optional columns], District, Vol, Page
        # Results are in the main page body, not always in a clean table

        page_source = driver.page_source

        # Look for result rows - FreeBMD uses specific class or structure
        # The surname is typically in bold/colored and links are present

        # Find all table rows that contain WRATHALL or similar surname patterns
        all_rows = driver.find_elements(By.TAG_NAME, 'tr')

        current_quarter = None
        current_year = None

        for row in all_rows:
            row_text = row.text.strip()

            # Check for quarter headers like "Births Mar 1863"
            quarter_match = re.search(r'(Births|Deaths|Marriages)\s+(Mar|Jun|Sep|Dec)\s+(\d{4})', row_text)
            if quarter_match:
                current_quarter = quarter_match.group(2)
                current_year = quarter_match.group(3)
                continue

            # Skip if no current quarter set
            if not current_year:
                continue

            # Try to parse data rows
            cells = row.find_elements(By.TAG_NAME, 'td')
            if len(cells) < 4:
                continue

            # Get cell texts
            cell_texts = [c.text.strip() for c in cells]

            # FreeBMD format: Surname | First name(s) | District | Vol | Page
            # But surname might be in a link/span, check for typical patterns
            surname = cell_texts[0] if cell_texts[0] else None
            forename = cell_texts[1] if len(cell_texts) > 1 else None
            district = None
            volume = None
            page = None

            # Find district (usually a link to a place)
            for i, cell in enumerate(cells):
                try:
                    link = cell.find_element(By.TAG_NAME, 'a')
                    link_text = link.text.strip()
                    # District links are place names
                    if link_text and not link_text.isdigit() and 'info' not in link_text.lower():
                        district = link_text
                        # Next cells should be vol and page
                        if i + 1 < len(cell_texts):
                            vol_page = cell_texts[i + 1]
                            # Format might be "10a 7" or separate cells
                            vol_match = re.search(r'(\d+[a-z]?)', vol_page)
                            if vol_match:
                                volume = vol_match.group(1)
                        if i + 2 < len(cell_texts):
                            page_text = cell_texts[i + 2]
                            if page_text.isdigit():
                                page = page_text
                        break
                except:
                    continue

            # Also try to extract vol/page from cell texts directly
            if not volume:
                for ct in cell_texts:
                    if re.match(r'^\d+[a-z]?$', ct) and not volume:
                        volume = ct
                    elif ct.isdigit() and volume and not page:
                        page = ct

            # Only add if we have a valid surname (all caps typically)
            if surname and surname.isupper() and len(surname) > 2:
                record = {
                    'type': record_type,
                    'surname': surname,
                    'forename': forename,
                    'district': district,
                    'volume': volume,
                    'page': page,
                    'quarter': current_quarter,
                    'year': current_year
                }

                if forename:
                    record['name'] = f"{forename} {surname}"
                else:
                    record['name'] = surname

                if current_quarter and current_year:
                    record['date'] = f"{current_quarter} {current_year}"

                if volume and page:
                    record['gro_reference'] = f"Vol {volume}, Page {page}"

                results.append(record)

        print(f"Parsed {len(results)} records")

    except Exception as e:
        print(f"Parse error: {e}")
        import traceback
        traceback.print_exc()

    return results


def store_results(results, person_id=None):
    """Store BMD results in the database."""
    if not results:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure bmd_record table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bmd_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            surname TEXT,
            forename TEXT,
            name TEXT,
            year TEXT,
            quarter TEXT,
            district TEXT,
            volume TEXT,
            page TEXT,
            gro_reference TEXT,
            mother_maiden TEXT,
            spouse TEXT,
            age TEXT,
            source_url TEXT DEFAULT 'https://freebmd.org.uk',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(type, name, year, quarter, district, volume, page)
        )
    """)

    # Ensure person_bmd link table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person_bmd (
            person_id INTEGER,
            bmd_record_id INTEGER,
            confidence REAL DEFAULT 0.5,
            PRIMARY KEY (person_id, bmd_record_id)
        )
    """)

    stored = 0

    for r in results:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO bmd_record (
                    type, surname, forename, name, year, quarter,
                    district, volume, page, gro_reference,
                    mother_maiden, spouse, age, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get('type'),
                r.get('surname'),
                r.get('forename'),
                r.get('name'),
                r.get('year'),
                r.get('quarter'),
                r.get('district'),
                r.get('volume'),
                r.get('page'),
                r.get('gro_reference'),
                r.get('mother_maiden'),
                r.get('spouse'),
                r.get('age'),
                'https://freebmd.org.uk'
            ))

            if cursor.rowcount > 0:
                stored += 1
                bmd_id = cursor.lastrowid

                if person_id:
                    cursor.execute("""
                        INSERT OR IGNORE INTO person_bmd (person_id, bmd_record_id)
                        VALUES (?, ?)
                    """, (person_id, bmd_id))

        except Exception as e:
            print(f"Error storing record: {e}")
            continue

    conn.commit()
    conn.close()
    return stored


def write_csv(results, surname=None, record_type='births', output_dir=None, append=False):
    """Write results to CSV file. Uses fixed filename, appends if file exists."""
    if not results:
        return None

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "output"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(exist_ok=True)

    filename = output_dir / f"freebmd_{record_type}_results.csv"
    file_exists = filename.exists()
    mode = 'a' if append or file_exists else 'w'

    with open(filename, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header only if new file
        if mode == 'w' or not file_exists:
            writer.writerow(['year', 'name', 'age', 'relationship', 'district'])

        for r in results:
            # relationship: mother_maiden for births, spouse for marriages
            relationship = r.get('mother_maiden', '') or r.get('spouse', '')
            writer.writerow([
                r.get('date', r.get('year', '')),
                r.get('name', ''),
                r.get('age', ''),
                relationship,
                r.get('district', '')
            ])

    print(f"CSV written to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description='Search FreeBMD for UK BMD index records')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--forename', help='Forename to search')
    parser.add_argument('--type', choices=['births', 'marriages', 'deaths', 'all'],
                       default='births', help='Record type (default: births)')
    parser.add_argument('--year', type=int, help='Specific year to search')
    parser.add_argument('--year-from', type=int, help='Start year for range search')
    parser.add_argument('--year-to', type=int, help='End year for range search')
    parser.add_argument('--district', help='Registration district')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run headless (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show browser')
    parser.add_argument('--store', action='store_true', help='Store results in database')
    parser.add_argument('--person-id', type=int, help='Person ID to link results to')
    parser.add_argument('--output-dir', help='Directory for CSV output')
    args = parser.parse_args()

    headless = not args.no_headless

    print(f"Searching FreeBMD for: {args.forename or ''} {args.surname}")
    print(f"Record type: {args.type}")
    if args.year:
        print(f"Year: {args.year}")
    elif args.year_from or args.year_to:
        print(f"Year range: {args.year_from or 'any'} - {args.year_to or 'any'}")
    print(f"Mode: {'headless' if headless else 'visible'}\n")

    results = search_freebmd(
        surname=args.surname,
        record_type=args.type,
        forename=args.forename,
        year=args.year,
        year_from=args.year_from,
        year_to=args.year_to,
        district=args.district,
        headless=headless
    )

    if results:
        print(f"\n{'='*60}")
        print(f"Found {len(results)} results:")
        print('='*60)

        for i, r in enumerate(results, 1):
            print(f"\n[{i}] {r.get('name', 'Unknown')}")
            print(f"    Type: {r.get('type', 'unknown')}")
            if r.get('date'):
                print(f"    Date: {r.get('date')}")
            if r.get('district'):
                print(f"    District: {r.get('district')}")
            if r.get('gro_reference'):
                print(f"    GRO Ref: {r.get('gro_reference')}")
            if r.get('mother_maiden'):
                print(f"    Mother's maiden name: {r.get('mother_maiden')}")
            if r.get('spouse'):
                print(f"    Spouse: {r.get('spouse')}")
            if r.get('age'):
                print(f"    Age at death: {r.get('age')}")

        # Always write CSV
        write_csv(results, args.surname, args.type, args.output_dir)

        if args.store:
            stored = store_results(results, args.person_id)
            print(f"\nStored {stored} new records in database.")
    else:
        print("\nNo results found.")
        print("Screenshot saved to /tmp/freebmd_results.png")


if __name__ == '__main__':
    main()
