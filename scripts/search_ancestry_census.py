#!/usr/bin/env python3
"""
Search Ancestry UK census records directly by name.

This script:
1. Gets people from UNK-PAT match trees (or specified tree)
2. Searches Ancestry census collections by name and birth year
3. Extracts birthplace and residence data from results
4. Stores findings in census_search_results table

Usage:
    python scripts/search_ancestry_census.py --unkpat --limit 50
    python scripts/search_ancestry_census.py --tree-id 173434538 --limit 10
    python scripts/search_ancestry_census.py --person "Harriett Stemp" --birth-year 1854
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import browser_cookie3
import requests

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

# UK Census source IDs on Ancestry
UK_CENSUS_SOURCES = {
    1841: "8978",
    1851: "8860",
    1861: "8767",
    1871: "7619",
    1881: "7572",
    1891: "6598",
    1901: "7814",
    1911: "2352",
}


def get_cookies():
    """Get Ancestry cookies from Chrome."""
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append(cookie)
        except Exception:
            pass
    return cookie_list


def make_session():
    """Create requests session with Ancestry cookies."""
    session = requests.Session()
    cookies = get_cookies()
    for c in cookies:
        session.cookies.set(c.name, c.value, domain=c.domain)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def init_database(conn):
    """Create census search results table if it doesn't exist."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS census_search_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER REFERENCES person(id),
            search_name TEXT NOT NULL,
            search_birth_year INTEGER,
            census_year INTEGER NOT NULL,
            result_name TEXT,
            result_age INTEGER,
            result_birth_year INTEGER,
            result_birthplace TEXT,
            result_residence TEXT,
            result_county TEXT,
            result_occupation TEXT,
            result_relationship TEXT,
            ancestry_record_id TEXT,
            ancestry_source_id TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(person_id, census_year, ancestry_record_id)
        )
    """)

    # Track search progress
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS census_search_progress (
            person_id INTEGER PRIMARY KEY,
            last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            results_found INTEGER DEFAULT 0
        )
    """)

    conn.commit()


def search_census_year(session, forename, surname, birth_year, census_year):
    """Search a specific census year for a person."""
    source_id = UK_CENSUS_SOURCES.get(census_year)
    if not source_id:
        return []

    # Calculate expected age at census
    if birth_year:
        expected_age = census_year - birth_year
        if expected_age < 0 or expected_age > 100:
            return []  # Person not alive during this census

    # Build search URL
    # Ancestry search format: /search/collections/{source_id}/?name={first}_{last}&birth={year}&birth_x=2
    name_query = f"{forename}_{surname}".replace(" ", "_")

    url = f"https://www.ancestry.co.uk/search/collections/{source_id}/"
    params = {
        "name": name_query,
        "count": 20,
    }
    if birth_year:
        params["birth"] = birth_year
        params["birth_x"] = "5"  # +/- 5 years tolerance

    try:
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return []
    except Exception as e:
        print(f"      Error searching {census_year}: {e}")
        return []

    # Parse results from HTML
    results = parse_search_results(resp.text, census_year, source_id)
    return results


def parse_search_results(html, census_year, source_id):
    """Parse census search results from HTML."""
    results = []

    # Method 1: Look for __PRELOADED_STATE__ JSON (current Ancestry format)
    json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});\s*(?:</script>|window\.)', html, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            items = data.get('results', {}).get('results', {}).get('items', [])

            for item in items[:10]:  # Limit to top 10
                result = {
                    'census_year': census_year,
                    'source_id': source_id,
                    'record_id': item.get('recordId', ''),
                }

                # Extract fields - they're in a list with 'label' and 'text' keys
                fields = item.get('fields', [])
                for field in fields:
                    if not isinstance(field, dict):
                        continue
                    label = field.get('label', '').lower()
                    text = field.get('text', '')

                    if 'name' == label:
                        result['name'] = text
                    elif 'birth year' in label:
                        # Parse "abt 1849" -> 1849
                        year_match = re.search(r'(\d{4})', text)
                        if year_match:
                            result['birth_year'] = int(year_match.group(1))
                            result['age'] = census_year - result['birth_year']
                    elif 'birth place' in label:
                        result['birthplace'] = text
                    elif 'residence' in label:
                        result['residence'] = text
                        # Extract county from residence
                        for county in ['Lancashire', 'Yorkshire', 'Cumberland', 'Westmorland',
                                       'Durham', 'Hampshire', 'Sussex', 'Surrey', 'Kent',
                                       'London', 'Middlesex', 'Cheshire', 'Derbyshire']:
                            if county.lower() in text.lower():
                                result['county'] = county
                                break
                    elif 'relationship' in label:
                        result['relationship'] = text
                    elif 'occupation' in label:
                        result['occupation'] = text

                if result.get('name') or result.get('record_id'):
                    results.append(result)

            if results:
                return results
        except (json.JSONDecodeError, KeyError) as e:
            pass

    # Method 2: Fallback - look for __INITIAL_STATE__
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            records = data.get('search', {}).get('results', {}).get('records', [])
            for record in records[:10]:
                result = extract_record_from_json(record, census_year, source_id)
                if result:
                    results.append(result)
            if results:
                return results
        except (json.JSONDecodeError, KeyError):
            pass

    return results


def extract_record_from_json(record, census_year, source_id):
    """Extract census data from JSON record object."""
    try:
        result = {
            'census_year': census_year,
            'source_id': source_id,
            'record_id': record.get('recordId', record.get('id', '')),
        }

        # Extract fields from various possible structures
        fields = record.get('fields', record.get('data', {}))
        if isinstance(fields, list):
            fields = {f.get('label', ''): f.get('value', '') for f in fields}

        result['name'] = fields.get('Name', fields.get('name', ''))

        # Age
        age_str = fields.get('Age', fields.get('age', ''))
        if age_str:
            try:
                result['age'] = int(re.sub(r'[^\d]', '', str(age_str)))
            except ValueError:
                pass

        # Birthplace
        result['birthplace'] = fields.get('Birth Place', fields.get('birthPlace',
                               fields.get('Where born', '')))

        # Residence
        result['residence'] = fields.get('Residence', fields.get('residence',
                              fields.get('Address', '')))

        # County
        result['county'] = fields.get('County', fields.get('county', ''))

        # Occupation
        result['occupation'] = fields.get('Occupation', fields.get('occupation', ''))

        # Relationship to head
        result['relationship'] = fields.get('Relationship', fields.get('relationship',
                                 fields.get('Relation to Head', '')))

        return result if result.get('name') or result.get('record_id') else None

    except Exception:
        return None


def extract_record_from_html(row_html, census_year, source_id):
    """Extract census data from HTML table row."""
    result = {
        'census_year': census_year,
        'source_id': source_id,
    }

    # Extract record ID from link
    id_match = re.search(r'records/(\d+)', row_html)
    if id_match:
        result['record_id'] = id_match.group(1)

    # Extract name
    name_match = re.search(r'>([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)<', row_html)
    if name_match:
        result['name'] = name_match.group(1)

    # Extract age
    age_match = re.search(r'(?:age|Age)[^\d]*(\d+)', row_html)
    if age_match:
        result['age'] = int(age_match.group(1))

    # Extract birthplace
    birth_match = re.search(r'(?:born|Birth[^<]*)[^\w]*([A-Z][a-z]+(?:,?\s*[A-Z][a-z]+)*)', row_html)
    if birth_match:
        result['birthplace'] = birth_match.group(1)

    # Extract residence/county
    county_patterns = [
        'Lancashire', 'Yorkshire', 'Cumberland', 'Westmorland', 'Durham',
        'Hampshire', 'Sussex', 'Kent', 'London', 'Middlesex'
    ]
    for county in county_patterns:
        if county.lower() in row_html.lower():
            result['county'] = county
            break

    return result if result.get('name') or result.get('record_id') else None


def fetch_record_details(session, source_id, record_id):
    """Fetch full details for a specific census record."""
    url = f"https://www.ancestry.co.uk/search/collections/{source_id}/records/{record_id}"

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return None
    except Exception as e:
        return None

    details = {}

    # Try to extract from originalValues JSON
    orig_match = re.search(r'originalValues:\s*(\{[^}]+\})', resp.text)
    if orig_match:
        try:
            data = json.loads(orig_match.group(1))
            details['name'] = data.get('SelfName', '')
            details['age'] = data.get('SelfResidenceAge', data.get('SelfAge', ''))
            details['birthplace'] = data.get('SelfBirthPlace', '')
            details['residence'] = data.get('SelfResidencePlace', data.get('SelfResidenceCity', ''))
            details['county'] = data.get('SelfResidenceCounty', '')
            details['occupation'] = data.get('SelfOccupation', '')
            details['relationship'] = data.get('SelfRelationToHead', '')
        except json.JSONDecodeError:
            pass

    # Fallback: extract from HTML
    if not details.get('birthplace'):
        bp_match = re.search(r'(?:Where born|Birth ?place)[^<]*<[^>]*>([^<]+)', resp.text, re.IGNORECASE)
        if bp_match:
            details['birthplace'] = bp_match.group(1).strip()

    if not details.get('residence'):
        res_match = re.search(r'(?:Residence|Address)[^<]*<[^>]*>([^<]+)', resp.text, re.IGNORECASE)
        if res_match:
            details['residence'] = res_match.group(1).strip()

    return details if details else None


def calculate_confidence(result, search_name, search_birth_year):
    """Calculate confidence score for a match."""
    score = 0.5  # Base score

    result_name = result.get('name', '').lower()
    search_name_lower = search_name.lower()

    # Name matching
    search_parts = search_name_lower.split()
    result_parts = result_name.split()

    if search_name_lower == result_name:
        score += 0.3
    elif all(p in result_name for p in search_parts):
        score += 0.2
    elif any(p in result_name for p in search_parts):
        score += 0.1

    # Age matching
    if search_birth_year and result.get('age'):
        result_birth_year = result.get('census_year', 1881) - result['age']
        year_diff = abs(search_birth_year - result_birth_year)
        if year_diff == 0:
            score += 0.2
        elif year_diff <= 2:
            score += 0.15
        elif year_diff <= 5:
            score += 0.1
        else:
            score -= 0.1

    return min(max(score, 0.0), 1.0)


def store_result(conn, person_id, search_name, search_birth_year, result):
    """Store a census search result."""
    cursor = conn.cursor()

    # Calculate birth year from age
    result_birth_year = None
    if result.get('age') and result.get('census_year'):
        result_birth_year = result['census_year'] - result['age']

    confidence = calculate_confidence(result, search_name, search_birth_year)

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO census_search_result (
                person_id, search_name, search_birth_year, census_year,
                result_name, result_age, result_birth_year, result_birthplace,
                result_residence, result_county, result_occupation, result_relationship,
                ancestry_record_id, ancestry_source_id, confidence_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            person_id,
            search_name,
            search_birth_year,
            result.get('census_year'),
            result.get('name'),
            result.get('age'),
            result_birth_year,
            result.get('birthplace'),
            result.get('residence'),
            result.get('county'),
            result.get('occupation'),
            result.get('relationship'),
            result.get('record_id'),
            result.get('source_id'),
            confidence,
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"      Error storing result: {e}")
        return False


def search_person(session, conn, person_id, forename, surname, birth_year, fetch_details=False, delay=0.5):
    """Search all relevant census years for a person."""
    search_name = f"{forename} {surname}".strip()
    results_found = 0

    # Determine which census years to search based on birth year
    for census_year in sorted(UK_CENSUS_SOURCES.keys()):
        if birth_year:
            age_at_census = census_year - birth_year
            if age_at_census < 0 or age_at_census > 95:
                continue  # Skip if person wouldn't be alive/adult

        print(f"    {census_year}...", end=" ", flush=True)

        results = search_census_year(session, forename, surname, birth_year, census_year)

        if results:
            print(f"{len(results)} results", end="")

            # Optionally fetch full details for top result
            if fetch_details and results:
                top = results[0]
                if top.get('record_id'):
                    details = fetch_record_details(session, top['source_id'], top['record_id'])
                    if details:
                        top.update(details)
                        if top.get('birthplace'):
                            print(f" [{top['birthplace'][:30]}]", end="")

            # Store results
            for result in results[:3]:  # Store top 3 matches per census
                if store_result(conn, person_id, search_name, birth_year, result):
                    results_found += 1

            print()
        else:
            print("none")

        time.sleep(delay)

    # Update progress
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO census_search_progress (person_id, results_found)
        VALUES (?, ?)
    """, (person_id, results_found))
    conn.commit()

    return results_found


def get_unkpat_people(conn, limit=50):
    """Get people from UNK-PAT match trees to search."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT p.id, p.forename, p.surname, p.birth_year_estimate,
               dm.name as match_name, dm.shared_cm
        FROM person p
        JOIN tree t ON p.tree_id = t.id
        JOIN dna_match dm ON t.ancestry_tree_id = dm.linked_tree_id
        LEFT JOIN census_search_progress csp ON csp.person_id = p.id
        WHERE dm.mrca LIKE '%UNK-PAT%'
        AND p.forename IS NOT NULL
        AND p.surname IS NOT NULL
        AND length(p.forename) > 1
        AND length(p.surname) > 1
        AND p.birth_year_estimate BETWEEN 1780 AND 1900
        AND csp.person_id IS NULL
        ORDER BY dm.shared_cm DESC, p.birth_year_estimate
        LIMIT ?
    """, (limit,))

    return cursor.fetchall()


def get_tree_people(conn, ancestry_tree_id, limit=50):
    """Get people from a specific tree to search."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.forename, p.surname, p.birth_year_estimate,
               t.name as tree_name, 0 as shared_cm
        FROM person p
        JOIN tree t ON p.tree_id = t.id
        LEFT JOIN census_search_progress csp ON csp.person_id = p.id
        WHERE t.ancestry_tree_id = ?
        AND p.forename IS NOT NULL
        AND p.surname IS NOT NULL
        AND length(p.forename) > 1
        AND length(p.surname) > 1
        AND p.birth_year_estimate BETWEEN 1780 AND 1900
        AND csp.person_id IS NULL
        ORDER BY p.birth_year_estimate
        LIMIT ?
    """, (ancestry_tree_id, limit))

    return cursor.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Search Ancestry census records by name')
    parser.add_argument('--unkpat', action='store_true', help='Search people from UNK-PAT match trees')
    parser.add_argument('--tree-id', help='Search people from specific Ancestry tree ID')
    parser.add_argument('--person', help='Search for specific person (format: "Forename Surname")')
    parser.add_argument('--birth-year', type=int, help='Birth year for --person search')
    parser.add_argument('--limit', type=int, default=20, help='Max people to search (default: 20)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between searches (default: 1.0)')
    parser.add_argument('--details', action='store_true', help='Fetch full record details (slower)')
    parser.add_argument('--db', default=str(DB_PATH), help='Database path')
    args = parser.parse_args()

    if not any([args.unkpat, args.tree_id, args.person]):
        parser.error("Must specify --unkpat, --tree-id, or --person")

    # Connect to database
    conn = sqlite3.connect(args.db)
    init_database(conn)

    # Create session
    session = make_session()
    if not session.cookies:
        print("WARNING: No Ancestry cookies found. Log into Ancestry in Chrome first.")

    print(f"\n{'='*60}")
    print(f"ANCESTRY CENSUS SEARCH")
    print(f"{'='*60}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_people = 0
    total_results = 0

    if args.person:
        # Single person search
        parts = args.person.split()
        if len(parts) < 2:
            print("Error: Person name must include forename and surname")
            sys.exit(1)

        forename = parts[0]
        surname = " ".join(parts[1:])

        print(f"\nSearching: {forename} {surname} (b. {args.birth_year or '?'})")
        results = search_person(session, conn, None, forename, surname, args.birth_year,
                               args.details, args.delay)
        total_results = results
        total_people = 1

    elif args.tree_id:
        # Tree search
        people = get_tree_people(conn, args.tree_id, args.limit)
        print(f"\nSearching {len(people)} people from tree {args.tree_id}")

        for i, (person_id, forename, surname, birth_year, tree_name, _) in enumerate(people, 1):
            print(f"\n[{i}/{len(people)}] {forename} {surname} (b. {birth_year or '?'})")
            results = search_person(session, conn, person_id, forename, surname, birth_year,
                                   args.details, args.delay)
            total_results += results
            total_people += 1

    else:  # --unkpat
        # UNK-PAT search
        people = get_unkpat_people(conn, args.limit)
        print(f"\nSearching {len(people)} people from UNK-PAT match trees")

        current_match = None
        for i, (person_id, forename, surname, birth_year, match_name, shared_cm) in enumerate(people, 1):
            if match_name != current_match:
                current_match = match_name
                print(f"\n--- {match_name} ({shared_cm} cM) ---")

            print(f"  [{i}/{len(people)}] {forename} {surname} (b. {birth_year or '?'})")
            results = search_person(session, conn, person_id, forename, surname, birth_year,
                                   args.details, args.delay)
            total_results += results
            total_people += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"{'='*60}")
    print(f"  People searched: {total_people}")
    print(f"  Results stored: {total_results}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
