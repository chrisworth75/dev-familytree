#!/usr/bin/env python3
"""
Search FreeCEN (freecen.org.uk) for UK census records.

FreeCEN is a volunteer-run free census transcription project with NO CAPTCHA.
Coverage: 1841-1901 (partial transcriptions, ~52M records)

Usage:
    python scripts/search_freecen.py --surname Wrathall
    python scripts/search_freecen.py --surname Wrathall --forename Henry --birth-year 1863
    python scripts/search_freecen.py --surname Virgo --store
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

DB_PATH = Path(__file__).parent.parent / "genealogy.db"


def search_freecen(surname, forename=None, birth_year=None, census_year=None, headless=True, fetch_details=False):
    """
    Search FreeCEN for census records using Selenium.
    No CAPTCHA required - fully automated.
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
        print("Loading FreeCEN search page...")
        driver.get("https://www.freecen.org.uk/search_queries/new")

        # Wait for page to fully load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        time.sleep(2)

        # Handle Quantcast CMP cookie consent popup - MUST be dismissed before interacting with form
        try:
            # Wait for the Quantcast consent popup to appear
            time.sleep(3)  # Give popup time to fully render

            # Try multiple approaches to click AGREE
            consent_clicked = False

            # Method 1: Direct button click
            consent_selectors = [
                "//button[contains(text(), 'AGREE')]",
                "//button[@mode='primary']",
                "//button[contains(@class, 'css-')]//span[contains(text(), 'AGREE')]/parent::button",
            ]

            for selector in consent_selectors:
                try:
                    btn = driver.find_element(By.XPATH, selector)
                    driver.execute_script("arguments[0].click();", btn)  # Use JS click
                    print(f"Clicked consent using: {selector}")
                    consent_clicked = True
                    break
                except:
                    continue

            # Method 2: Use JavaScript to find and click the AGREE button
            if not consent_clicked:
                try:
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
                    print("Clicked AGREE via JS search")
                    consent_clicked = True
                except:
                    pass

            if consent_clicked:
                # Wait for overlay to disappear
                time.sleep(2)
                try:
                    WebDriverWait(driver, 5).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".qc-cmp-cleanslate"))
                    )
                    print("Consent overlay dismissed")
                except:
                    pass  # Overlay may have different class

        except Exception as e:
            print(f"Cookie consent handling: {e}")

        # Save screenshot for debugging
        driver.save_screenshot("/tmp/freecen_form.png")

        # Fill in search form
        print(f"Searching for: {forename or ''} {surname}")

        # Try multiple selectors for surname field
        # Actual field is id="last_name" name="search_query[last_name]"
        surname_field = None
        surname_selectors = [
            (By.ID, "last_name"),  # Actual ID on FreeCEN
            (By.NAME, "search_query[last_name]"),
            (By.ID, "search_query_surname"),
            (By.NAME, "search_query[surname]"),
            (By.CSS_SELECTOR, "input[placeholder*='urname']"),
            (By.XPATH, "//label[contains(text(), 'Surname')]/following::input[1]"),
        ]

        for selector_type, selector in surname_selectors:
            try:
                surname_field = driver.find_element(selector_type, selector)
                print(f"Found surname field using: {selector}")
                break
            except:
                continue

        if not surname_field:
            # Debug: print all input fields
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"Found {len(inputs)} input elements:")
            for inp in inputs[:10]:
                print(f"  id={inp.get_attribute('id')}, name={inp.get_attribute('name')}, type={inp.get_attribute('type')}")
            raise Exception("Could not find surname field")

        # Wait for the field to be interactable (popup may still be animating out)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(surname_field)
        )

        # Scroll to and click the field first
        driver.execute_script("arguments[0].scrollIntoView(true);", surname_field)
        time.sleep(0.5)
        surname_field.click()
        surname_field.clear()
        surname_field.send_keys(surname)

        # Forename field - likely id="first_name" or similar
        if forename:
            forename_selectors = [
                (By.ID, "first_name"),  # Likely actual ID
                (By.NAME, "search_query[first_name]"),
                (By.ID, "search_query_forenames"),
                (By.NAME, "search_query[forenames]"),
                (By.XPATH, "//label[contains(text(), 'Forename')]/following::input[1]"),
            ]
            for selector_type, selector in forename_selectors:
                try:
                    forename_field = driver.find_element(selector_type, selector)
                    forename_field.clear()
                    forename_field.send_keys(forename)
                    print(f"Found forename field using: {selector}")
                    break
                except:
                    continue

        # Birth year range
        if birth_year:
            try:
                # Try different selectors for birth year fields
                year_from_selectors = [
                    (By.ID, "search_query_start_year"),
                    (By.NAME, "search_query[start_year]"),
                    (By.XPATH, "//label[contains(text(), 'Birth year from')]/following::input[1]"),
                ]
                for selector_type, selector in year_from_selectors:
                    try:
                        start_year = driver.find_element(selector_type, selector)
                        start_year.clear()
                        start_year.send_keys(str(birth_year - 5))
                        break
                    except:
                        continue

                year_to_selectors = [
                    (By.ID, "search_query_end_year"),
                    (By.NAME, "search_query[end_year]"),
                    (By.XPATH, "//label[contains(text(), 'Birth year to')]/following::input[1]"),
                ]
                for selector_type, selector in year_to_selectors:
                    try:
                        end_year = driver.find_element(selector_type, selector)
                        end_year.clear()
                        end_year.send_keys(str(birth_year + 5))
                        break
                    except:
                        continue
            except:
                pass

        # Census year filter - select specific year from dropdown
        if census_year:
            try:
                from selenium.webdriver.support.ui import Select
                # The census year dropdown: id="search_query_record_type"
                census_year_selectors = [
                    (By.ID, "search_query_record_type"),
                    (By.NAME, "search_query[record_type]"),
                ]
                for selector_type, selector in census_year_selectors:
                    try:
                        census_select = driver.find_element(selector_type, selector)
                        select = Select(census_select)
                        select.select_by_value(str(census_year))
                        print(f"Selected census year: {census_year}")
                        break
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"Could not set census year: {e}")

        # Submit search - try multiple selectors
        submit_selectors = [
            (By.NAME, "commit"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "input.btn"),
        ]
        for selector_type, selector in submit_selectors:
            try:
                submit_btn = driver.find_element(selector_type, selector)
                submit_btn.click()
                print(f"Submitted using: {selector}")
                break
            except:
                continue

        # Wait for results
        time.sleep(3)

        # Save screenshot
        driver.save_screenshot("/tmp/freecen_results.png")
        print("Screenshot: /tmp/freecen_results.png")

        # Parse results
        results = parse_results(driver, fetch_details=fetch_details)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot("/tmp/freecen_error.png")

    finally:
        driver.quit()

    return results


def parse_results(driver, fetch_details=False):
    """Parse FreeCEN search results."""
    results = []
    detail_urls = []

    try:
        page_source = driver.page_source

        # Check for result count - FreeCEN uses "We found X Results"
        match = re.search(r'We found (\d+) Results', page_source, re.IGNORECASE)
        if match:
            print(f"Found {match.group(1)} results")
        else:
            match = re.search(r'(\d+)\s+results?\s+found', page_source, re.IGNORECASE)
            if match:
                print(f"Found {match.group(1)} results")

        # Save HTML for debugging
        with open('/tmp/freecen_results.html', 'w') as f:
            f.write(page_source)

        # FreeCEN results table structure:
        # Detail | Individual | Birth County | Birth Place | Birth | Census | Census County | Census District
        try:
            # Find the main results table (has thead with th elements)
            tables = driver.find_elements(By.TAG_NAME, 'table')
            table = None

            for t in tables:
                headers = t.find_elements(By.TAG_NAME, 'th')
                header_texts = [h.text.lower() for h in headers]
                if 'individual' in header_texts or 'birth county' in header_texts:
                    table = t
                    break

            if table:
                rows = table.find_elements(By.TAG_NAME, 'tr')

                # Get header mapping
                header_row = rows[0] if rows else None
                headers = []
                if header_row:
                    headers = [th.text.lower().strip() for th in header_row.find_elements(By.TAG_NAME, 'th')]
                print(f"Table headers: {headers}")

                # Find column indices
                col_map = {}
                for i, h in enumerate(headers):
                    if 'detail' in h:
                        col_map['detail'] = i
                    elif 'individual' in h:
                        col_map['name'] = i
                    elif 'birth county' in h:
                        col_map['birth_county'] = i
                    elif 'birth place' in h:
                        col_map['birth_place'] = i
                    elif h == 'birth':
                        col_map['birth_year'] = i
                    elif h == 'census':
                        col_map['census_year'] = i
                    elif 'census county' in h:
                        col_map['census_county'] = i
                    elif 'census district' in h:
                        col_map['district'] = i

                print(f"Column mapping: {col_map}")

                for row in rows[1:]:  # Skip header
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 4:
                        record = {}

                        # Get detail URL for later fetching
                        if 'detail' in col_map and col_map['detail'] < len(cells):
                            try:
                                link = cells[col_map['detail']].find_element(By.TAG_NAME, 'a')
                                record['detail_url'] = link.get_attribute('href')
                            except:
                                pass

                        if 'name' in col_map and col_map['name'] < len(cells):
                            record['name'] = cells[col_map['name']].text.strip()
                        if 'birth_county' in col_map and col_map['birth_county'] < len(cells):
                            record['birth_county'] = cells[col_map['birth_county']].text.strip()
                        if 'birth_place' in col_map and col_map['birth_place'] < len(cells):
                            record['birth_place'] = cells[col_map['birth_place']].text.strip()
                        if 'birth_year' in col_map and col_map['birth_year'] < len(cells):
                            birth_text = cells[col_map['birth_year']].text.strip()
                            if birth_text and birth_text.isdigit():
                                record['born_approx'] = birth_text
                        if 'census_year' in col_map and col_map['census_year'] < len(cells):
                            census_text = cells[col_map['census_year']].text.strip()
                            if census_text and census_text.isdigit():
                                record['year'] = census_text
                        if 'census_county' in col_map and col_map['census_county'] < len(cells):
                            record['county'] = cells[col_map['census_county']].text.strip()
                        if 'district' in col_map and col_map['district'] < len(cells):
                            record['district'] = cells[col_map['district']].text.strip()

                        # Calculate age from birth year and census year
                        if record.get('born_approx') and record.get('year'):
                            try:
                                record['age'] = str(int(record['year']) - int(record['born_approx']))
                            except:
                                pass

                        if record.get('name'):
                            results.append(record)
            else:
                print("Could not find results table")

        except Exception as e:
            print(f"Table parsing error: {e}")
            import traceback
            traceback.print_exc()

        print(f"Parsed {len(results)} census records")

        # Fetch details if requested
        if fetch_details and results:
            print(f"\nFetching details for {len(results)} records...")
            for i, record in enumerate(results):
                if record.get('detail_url'):
                    try:
                        detail = fetch_record_details(driver, record['detail_url'], record.get('name'))
                        record.update(detail)
                        if (i + 1) % 10 == 0:
                            print(f"  Fetched {i + 1}/{len(results)} details...")
                    except Exception as e:
                        print(f"  Error fetching detail {i + 1}: {e}")
                    time.sleep(0.5)  # Be nice to the server
            print(f"  Completed fetching details")

    except Exception as e:
        print(f"Parse error: {e}")
        import traceback
        traceback.print_exc()

    return results


def fetch_record_details(driver, url, target_name=None):
    """Fetch relationship, occupation, and address from detail page.

    The detail page has two tables:
    - Table 0: Location details (house/street name, civil parish, etc.)
    - Table 1: Household members (relationship, occupation, etc.)
    """
    details = {}

    try:
        driver.get(url)
        time.sleep(1)

        tables = driver.find_elements(By.TAG_NAME, 'table')

        for table in tables:
            headers = table.find_elements(By.TAG_NAME, 'th')
            header_texts = [h.text.lower().strip() for h in headers]

            # Table 0: Location details - extract house/street name
            if 'house or street name' in header_texts or 'house number' in header_texts:
                col_map = {}
                for i, h in enumerate(header_texts):
                    if 'house or street name' in h:
                        col_map['address'] = i
                    elif 'house number' in h:
                        col_map['house_number'] = i
                    elif 'civil parish' in h:
                        col_map['civil_parish'] = i

                rows = table.find_elements(By.TAG_NAME, 'tr')
                if len(rows) > 1:
                    cells = rows[1].find_elements(By.TAG_NAME, 'td')
                    if 'address' in col_map and col_map['address'] < len(cells):
                        details['address'] = cells[col_map['address']].text.strip()
                    if 'house_number' in col_map and col_map['house_number'] < len(cells):
                        house_num = cells[col_map['house_number']].text.strip()
                        if house_num and house_num != '-':
                            details['house_number'] = house_num
                    if 'civil_parish' in col_map and col_map['civil_parish'] < len(cells):
                        details['civil_parish'] = cells[col_map['civil_parish']].text.strip()

            # Table 1: Household - extract relationship and occupation for searched person
            elif 'relationship' in header_texts or 'occupation' in header_texts:
                col_map = {}
                for i, h in enumerate(header_texts):
                    if 'surname' in h:
                        col_map['surname'] = i
                    elif 'forename' in h:
                        col_map['forename'] = i
                    elif 'relationship' in h:
                        col_map['relationship'] = i
                    elif 'occupation' in h:
                        col_map['occupation'] = i
                    elif 'marital' in h:
                        col_map['marital_status'] = i

                rows = table.find_elements(By.TAG_NAME, 'tr')
                for row in rows[1:]:  # Skip header
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) < 3:
                        continue

                    # FreeCEN marks searched person with weight--semibold class
                    # or "the person found in your search" text
                    first_cell_class = cells[0].get_attribute('class') or ''
                    is_searched_person = 'weight--semibold' in first_cell_class

                    if not is_searched_person:
                        row_text = row.text
                        if 'the person found' in row_text.lower():
                            is_searched_person = True

                    if is_searched_person:
                        if 'relationship' in col_map and col_map['relationship'] < len(cells):
                            details['relationship'] = cells[col_map['relationship']].text.strip()
                        if 'occupation' in col_map and col_map['occupation'] < len(cells):
                            details['occupation'] = cells[col_map['occupation']].text.strip()
                        if 'marital_status' in col_map and col_map['marital_status'] < len(cells):
                            details['marital_status'] = cells[col_map['marital_status']].text.strip()
                        break

    except Exception as e:
        pass  # Silently fail for individual records

    return details


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

        cursor.execute("""
            SELECT id FROM census_record
            WHERE year = ? AND name_as_recorded = ? AND source_url = 'https://freecen.org.uk'
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
                r.get('county', ''),
                'https://freecen.org.uk'
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

    filename = output_dir / "freecen_results.csv"
    file_exists = filename.exists()
    mode = 'a' if append or file_exists else 'w'

    with open(filename, mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header only if new file
        if mode == 'w' or not file_exists:
            writer.writerow(['census_year', 'name', 'age', 'relationship', 'occupation', 'address', 'birth_place', 'county', 'district'])

        for r in results:
            # Combine house number and address if both present
            address = r.get('address', '')
            if r.get('house_number'):
                address = f"{r.get('house_number')} {address}".strip()

            writer.writerow([
                r.get('year', ''),
                r.get('name', ''),
                r.get('age', ''),
                r.get('relationship', ''),
                r.get('occupation', ''),
                address,
                r.get('birth_place', ''),
                r.get('county', ''),
                r.get('district', '')
            ])

    print(f"CSV written to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description='Search FreeCEN for UK census records')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--forename', help='Forename to search')
    parser.add_argument('--birth-year', type=int, help='Birth year (±5 year range)')
    parser.add_argument('--year', type=int, choices=[1841, 1851, 1861, 1871, 1881, 1891, 1901],
                       help='Census year')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run headless (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show browser')
    parser.add_argument('--store', action='store_true', help='Store results in database')
    parser.add_argument('--person-id', type=int, help='Person ID to link results to')
    parser.add_argument('--output-dir', help='Directory for CSV output')
    parser.add_argument('--details', action='store_true',
                       help='Fetch relationship and occupation from detail pages (slower)')
    args = parser.parse_args()

    headless = not args.no_headless

    print(f"Searching FreeCEN for: {args.forename or ''} {args.surname}")
    print("FreeCEN has NO CAPTCHA - fully automated search")
    print(f"Mode: {'headless' if headless else 'visible'}\n")

    results = search_freecen(
        surname=args.surname,
        forename=args.forename,
        birth_year=args.birth_year,
        census_year=args.year,
        headless=headless,
        fetch_details=args.details
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


if __name__ == '__main__':
    main()
