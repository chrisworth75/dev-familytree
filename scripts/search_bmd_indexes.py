#!/usr/bin/env python3
"""
Search UK BMD indexes for birth, marriage, and death records.

Supports:
- Lancashire BMD (lancashirebmd.org.uk)
- Cumbria BMD (cumbriabmd.org.uk)

Usage:
    python scripts/search_bmd_indexes.py --surname Wrathall --type births --years 1940-1960
    python scripts/search_bmd_indexes.py --mmn Phillips --type births --years 1939-1954 --region cumbria
"""

import argparse
import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
import json

DB_PATH = 'genealogy.db'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

BMD_SITES = {
    'lancashire': {
        'births': 'https://www.lancashirebmd.org.uk/birthsearch.php',
        'marriages': 'https://www.lancashirebmd.org.uk/marriagesearch.php',
        'deaths': 'https://www.lancashirebmd.org.uk/deathsearch.php',
        'county': 'lancs'
    },
    'cumbria': {
        'births': 'https://cumbriabmd.org.uk/birthsearch.php',
        'marriages': 'https://cumbriabmd.org.uk/marriagesearch.php',
        'deaths': 'https://cumbriabmd.org.uk/deathsearch.php',
        'county': 'cumbria'
    }
}

def get_db():
    return sqlite3.connect(DB_PATH)

def search_lancashire_births(surname, mmn=None, start_year=1900, end_year=1970, match_type='soundex'):
    """Search Lancashire BMD for births."""
    url = BMD_SITES['lancashire']['births']

    # Lancashire BMD allows max 25 years at a time
    all_results = []

    for year in range(start_year, end_year, 20):
        center_year = year + 10

        data = {
            'county': 'lancs',
            'lang': '',
            'year_date[]': str(center_year),
            'year_plus_minus_val': '10',
            'search_region[]': 'All',
            'sort_by': 'alpha',
            'search_district': 'all',
            'surname': surname or '',
            'initial': '',
            'maiden_surname': mmn or '',
            'ignore_blank_mmn': 'no' if mmn else 'yes',
            'ignore_flag': '1',
            'match': match_type,
            'csv_or_list': 'screen',
            'submit': 'Display Results'
        }

        try:
            response = requests.post(url, data=data, headers=HEADERS, timeout=60)
            if response.status_code == 200:
                results = parse_bmd_results(response.text, 'births')
                all_results.extend(results)
        except Exception as e:
            print(f"Error searching {center_year}: {e}")

        time.sleep(0.5)

    return all_results

def search_cumbria_births(surname, mmn=None, start_year=1900, end_year=1970, match_type='soundex'):
    """Search Cumbria BMD for births."""
    url = BMD_SITES['cumbria']['births']

    all_results = []

    for year in range(start_year, end_year, 20):
        center_year = year + 10

        data = {
            'county': 'cumbria',
            'lang': '',
            'year_date[]': str(center_year),
            'year_plus_minus_val': '10',
            'search_region[]': 'All',
            'sort_by': 'alpha',
            'search_district': 'all',
            'surname': surname or '',
            'initial': '',
            'maiden_surname': mmn or '',
            'ignore_blank_mmn': 'no' if mmn else 'yes',
            'ignore_flag': '1',
            'match': match_type,
            'csv_or_list': 'screen',
            'submit': 'Display Results'
        }

        try:
            response = requests.post(url, data=data, headers=HEADERS, timeout=60)
            if response.status_code == 200:
                results = parse_bmd_results(response.text, 'births')
                all_results.extend(results)
        except Exception as e:
            print(f"Error searching {center_year}: {e}")

        time.sleep(0.5)

    return all_results

def search_lancashire_marriages(surname, start_year=1900, end_year=1970, match_type='soundex'):
    """Search Lancashire BMD for marriages."""
    url = BMD_SITES['lancashire']['marriages']

    all_results = []

    for year in range(start_year, end_year, 20):
        center_year = year + 10

        data = {
            'county': 'lancs',
            'lang': '',
            'year_date[]': str(center_year),
            'year_plus_minus_val': '10',
            'search_region[]': 'All',
            'sort_by': 'alpha',
            'search_district': 'all',
            'surname': surname,
            'initial': '',
            'spouse_surname': '',
            'spouse_initial': '',
            'match': match_type,
            'csv_or_list': 'screen',
            'submit': 'Display Results'
        }

        try:
            response = requests.post(url, data=data, headers=HEADERS, timeout=60)
            if response.status_code == 200:
                results = parse_bmd_results(response.text, 'marriages')
                all_results.extend(results)
        except Exception as e:
            print(f"Error searching {center_year}: {e}")

        time.sleep(0.5)

    return all_results

def parse_bmd_results(html, record_type):
    """Parse BMD search results HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator='\n', strip=True)
    lines = text.split('\n')

    results = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Look for surname in ALL CAPS (indicates a result row)
        if line.isupper() and len(line) > 2 and not any(x in line for x in ['ADD', 'TOTAL', 'SEARCH', 'BMD']):
            result = {'surname': line, 'type': record_type}

            # Next lines contain: forename, (mmn/spouse for births/marriages), year, district
            if i + 1 < len(lines):
                result['forename'] = lines[i + 1].strip()

            # Check if next field is a year or name (MMN/spouse)
            if i + 2 < len(lines):
                next_field = lines[i + 2].strip()
                if next_field.isdigit() and len(next_field) == 4:
                    result['year'] = int(next_field)
                    if i + 3 < len(lines):
                        result['district'] = lines[i + 3].strip()
                    i += 4
                else:
                    if record_type == 'births':
                        result['mmn'] = next_field
                    elif record_type == 'marriages':
                        result['spouse'] = next_field

                    if i + 3 < len(lines) and lines[i + 3].strip().isdigit():
                        result['year'] = int(lines[i + 3].strip())
                    if i + 4 < len(lines):
                        result['district'] = lines[i + 4].strip()
                    i += 5
            else:
                i += 1

            # Only add if we have meaningful data
            if result.get('forename') and result.get('year'):
                results.append(result)
        else:
            i += 1

    return results

def save_results(results, output_file=None):
    """Save results to JSON file."""
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Saved {len(results)} results to {output_file}")

def import_to_db(results):
    """Import BMD results to database."""
    conn = get_db()
    cursor = conn.cursor()

    added = 0
    for r in results:
        # Check if person already exists
        cursor.execute("""
            SELECT id FROM person
            WHERE forename = ? AND surname = ? AND birth_year_estimate = ?
        """, (r.get('forename'), r.get('surname'), r.get('year')))

        if cursor.fetchone():
            continue

        notes = f"BMD Index: {r.get('district', 'Unknown district')}"
        if r.get('mmn'):
            notes += f"\nMother maiden name: {r['mmn']}"

        cursor.execute("""
            INSERT INTO person (forename, surname, birth_year_estimate, birth_place, notes, source)
            VALUES (?, ?, ?, ?, ?, 'BMD Index')
        """, (r.get('forename'), r.get('surname'), r.get('year'),
              r.get('district'), notes))
        added += 1

    conn.commit()
    conn.close()
    return added

def main():
    parser = argparse.ArgumentParser(description='Search UK BMD indexes')
    parser.add_argument('--surname', help='Surname to search')
    parser.add_argument('--mmn', help='Mother maiden name (for births)')
    parser.add_argument('--type', choices=['births', 'marriages', 'deaths'], default='births')
    parser.add_argument('--years', default='1900-1970', help='Year range (e.g., 1940-1960)')
    parser.add_argument('--region', choices=['lancashire', 'cumbria', 'both'], default='both')
    parser.add_argument('--match', choices=['exact', 'soundex', 'near'], default='soundex')
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--import-db', action='store_true', help='Import results to database')
    args = parser.parse_args()

    # Parse year range
    years = args.years.split('-')
    start_year = int(years[0])
    end_year = int(years[1]) if len(years) > 1 else start_year + 50

    print(f"BMD Index Search - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print(f"Surname: {args.surname or '(any)'}")
    print(f"Mother maiden name: {args.mmn or '(any)'}")
    print(f"Type: {args.type}")
    print(f"Years: {start_year}-{end_year}")
    print(f"Region: {args.region}")
    print("=" * 60)

    all_results = []

    if args.type == 'births':
        if args.region in ['lancashire', 'both']:
            print("\nSearching Lancashire BMD...")
            results = search_lancashire_births(args.surname, args.mmn, start_year, end_year, args.match)
            print(f"  Found {len(results)} results")
            all_results.extend(results)

        if args.region in ['cumbria', 'both']:
            print("\nSearching Cumbria BMD...")
            results = search_cumbria_births(args.surname, args.mmn, start_year, end_year, args.match)
            print(f"  Found {len(results)} results")
            all_results.extend(results)

    elif args.type == 'marriages':
        if args.region in ['lancashire', 'both']:
            print("\nSearching Lancashire BMD marriages...")
            results = search_lancashire_marriages(args.surname, start_year, end_year, args.match)
            print(f"  Found {len(results)} results")
            all_results.extend(results)

    # Display results
    print(f"\n{'=' * 60}")
    print(f"TOTAL RESULTS: {len(all_results)}")
    print(f"{'=' * 60}\n")

    for r in all_results[:50]:  # Show first 50
        mmn_str = f" (MMN: {r['mmn']})" if r.get('mmn') else ""
        spouse_str = f" m. {r['spouse']}" if r.get('spouse') else ""
        print(f"{r.get('forename', '?'):25} {r.get('surname', '?'):15} {r.get('year', '?'):6} {r.get('district', '?')}{mmn_str}{spouse_str}")

    if len(all_results) > 50:
        print(f"\n... and {len(all_results) - 50} more")

    # Save/import
    if args.output:
        save_results(all_results, args.output)

    if args.import_db:
        added = import_to_db(all_results)
        print(f"\nImported {added} new records to database")

if __name__ == '__main__':
    main()
