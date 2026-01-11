#!/usr/bin/env python3
"""
Import census records from Ancestry for people in a tree.

This script:
1. Gets all people from a specified tree with ancestry_person_id
2. Fetches their Ancestry profile to find census source citations
3. Fetches full census record details
4. Stores in census_record table and links via person_census table

Usage:
    python scripts/import_census_from_tree.py [--tree-id TREE_ID] [--delay SECONDS] [--limit N]
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

import browser_cookie3
import requests

# Default tree ID (user's own tree)
DEFAULT_ANCESTRY_TREE_ID = "193991232"

# UK Census source IDs on Ancestry
UK_CENSUS_SOURCES = {
    "1841": ["8978"],
    "1851": ["8860"],
    "1861": ["8767"],
    "1871": ["7619"],
    "1881": ["7572"],
    "1891": ["6598"],
    "1901": ["7814"],
    "1911": ["2352"],
    "1939": ["61596"],  # 1939 Register
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
    })
    return session


def init_database(conn):
    """Create person_census link table if it doesn't exist."""
    cursor = conn.cursor()

    # Table to link persons to census records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person_census (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL REFERENCES person(id),
            census_record_id INTEGER NOT NULL REFERENCES census_record(id),
            ancestry_record_id TEXT,
            ancestry_source_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(person_id, census_record_id)
        )
    """)

    # Track which people we've already processed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS census_import_progress (
            ancestry_person_id TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            census_count INTEGER DEFAULT 0
        )
    """)

    # Add ancestry_record_id to census_record if not exists
    cursor.execute("PRAGMA table_info(census_record)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'ancestry_record_id' not in columns:
        cursor.execute("ALTER TABLE census_record ADD COLUMN ancestry_record_id TEXT")
    if 'ancestry_source_id' not in columns:
        cursor.execute("ALTER TABLE census_record ADD COLUMN ancestry_source_id TEXT")

    conn.commit()


def extract_census_sources(session, tree_id, person_id):
    """Extract census sources from a person's profile page."""
    profile_url = f"https://www.ancestry.co.uk/family-tree/person/tree/{tree_id}/person/{person_id}/facts"

    try:
        resp = session.get(profile_url, timeout=30)
        if resp.status_code != 200:
            return []
    except Exception as e:
        print(f"    Error fetching profile: {e}")
        return []

    # Extract window.researchData
    match = re.search(r'window\.researchData\s*=\s*(\{.*?\});\s*</script>', resp.text, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    # Extract census sources
    sources = data.get('PersonSources', [])
    census_sources = []

    for src in sources:
        title = src.get('Title', '').lower()
        source_id = src.get('SourceId', '')

        # Check if it's a UK census
        is_census = False
        census_year = None

        for year, source_ids in UK_CENSUS_SOURCES.items():
            if source_id in source_ids:
                is_census = True
                census_year = int(year)
                break

        # Also check by title if source_id not matched
        if not is_census:
            if 'census' in title or '1939' in title:
                for year in ['1841', '1851', '1861', '1871', '1881', '1891', '1901', '1911', '1939']:
                    if year in title:
                        is_census = True
                        census_year = int(year)
                        break

        if is_census and census_year:
            census_sources.append({
                'title': src.get('Title'),
                'record_id': src.get('RecordId'),
                'source_id': source_id,
                'year': census_year,
                'url': src.get('ViewRecordUrl'),
            })

    return census_sources


def extract_census_record(session, source_id, record_id, tree_id, person_id):
    """Extract full census record details from record page."""
    url = f"https://www.ancestry.co.uk/search/collections/{source_id}/records/{record_id}?tid={tree_id}&pid={person_id}&ssrc=pt"

    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return None
    except Exception as e:
        print(f"    Error fetching record: {e}")
        return None

    # Find originalValues JSON
    match = re.search(r'originalValues:\s*(\{[^}]+\})', resp.text)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        return data
    except json.JSONDecodeError:
        return None


def parse_census_data(raw_data, year, source_id, record_id):
    """Parse raw census data into standardized format."""
    # Field mappings vary by census year
    record = {
        'year': year,
        'ancestry_record_id': record_id,
        'ancestry_source_id': source_id,
    }

    # Name
    record['name_as_recorded'] = raw_data.get('SelfName', '')

    # Age
    age_str = raw_data.get('SelfResidenceAge', raw_data.get('SelfAge', ''))
    if age_str:
        try:
            record['age_as_recorded'] = int(re.sub(r'[^\d]', '', str(age_str)))
        except ValueError:
            pass

    # Gender
    gender = raw_data.get('SelfGender', '')
    if gender:
        record['sex'] = 'M' if gender.lower().startswith('m') else 'F'

    # Relationship to head
    record['relationship_to_head'] = raw_data.get('SelfRelationToHead', '')

    # Birth place
    record['birth_place_as_recorded'] = raw_data.get('SelfBirthPlace', '')

    # Occupation
    record['occupation'] = raw_data.get('SelfOccupation', '')

    # Marital status
    record['marital_status'] = raw_data.get('SelfMaritalStatus', '')

    # Address/Location
    address_parts = []
    for field in ['SelfResidenceStreet', 'SelfResidenceCity', 'SelfResidencePlace']:
        val = raw_data.get(field, '')
        if val and not val.startswith('/'):  # Skip URL-like values
            address_parts.append(val)
    record['address'] = ', '.join(filter(None, address_parts))

    # Parish/District
    record['parish'] = raw_data.get('F0005DFB', raw_data.get('SelfResidenceParish', ''))
    record['registration_district'] = raw_data.get('F0007AD6', raw_data.get('SelfResidenceDistrict', ''))
    record['sub_district'] = raw_data.get('F00079A7', '')

    # County
    county = raw_data.get('SelfResidenceCounty', '')
    if county and not record['registration_district']:
        record['registration_district'] = county

    # Household ID
    record['household_id'] = raw_data.get('HouseholdId', '')

    # Schedule number
    schedule = raw_data.get('F0005DFC', '')
    if schedule:
        try:
            record['schedule_number'] = int(schedule)
        except ValueError:
            pass

    # Store raw data
    record['raw_text'] = json.dumps(raw_data)

    return record


def store_census_record(conn, record, person_id, ancestry_record_id, ancestry_source_id):
    """Store census record and link to person."""
    cursor = conn.cursor()

    # Check if this record already exists
    cursor.execute("""
        SELECT id FROM census_record
        WHERE ancestry_record_id = ? AND ancestry_source_id = ?
    """, (ancestry_record_id, ancestry_source_id))
    existing = cursor.fetchone()

    if existing:
        census_record_id = existing[0]
    else:
        # Insert new census record
        cursor.execute("""
            INSERT INTO census_record (
                year, name_as_recorded, age_as_recorded, sex,
                relationship_to_head, birth_place_as_recorded, occupation,
                marital_status, address, parish, registration_district,
                sub_district, household_id, schedule_number, raw_text,
                ancestry_record_id, ancestry_source_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get('year'),
            record.get('name_as_recorded'),
            record.get('age_as_recorded'),
            record.get('sex'),
            record.get('relationship_to_head'),
            record.get('birth_place_as_recorded'),
            record.get('occupation'),
            record.get('marital_status'),
            record.get('address'),
            record.get('parish'),
            record.get('registration_district'),
            record.get('sub_district'),
            record.get('household_id'),
            record.get('schedule_number'),
            record.get('raw_text'),
            ancestry_record_id,
            ancestry_source_id,
        ))
        census_record_id = cursor.lastrowid

    # Link to person (ignore if already linked)
    cursor.execute("""
        INSERT OR IGNORE INTO person_census (
            person_id, census_record_id, ancestry_record_id, ancestry_source_id
        ) VALUES (?, ?, ?, ?)
    """, (person_id, census_record_id, ancestry_record_id, ancestry_source_id))

    conn.commit()
    return census_record_id


def main():
    parser = argparse.ArgumentParser(description='Import census records from Ancestry tree')
    parser.add_argument('--tree-id', default=DEFAULT_ANCESTRY_TREE_ID,
                        help=f'Ancestry tree ID (default: {DEFAULT_ANCESTRY_TREE_ID})')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of people to process (0 = all)')
    parser.add_argument('--skip-processed', action='store_true', default=True,
                        help='Skip already processed people (default: True)')
    parser.add_argument('--min-year', type=int, default=1750,
                        help='Minimum birth year to process (default: 1750)')
    parser.add_argument('--max-year', type=int, default=1910,
                        help='Maximum birth year to process (default: 1910)')
    parser.add_argument('--db', default='/Users/chris/dev-familytree/genealogy.db',
                        help='Database path')
    args = parser.parse_args()

    # Connect to database
    conn = sqlite3.connect(args.db)
    init_database(conn)
    cursor = conn.cursor()

    # Get tree's internal ID
    cursor.execute("SELECT id FROM tree WHERE ancestry_tree_id = ?", (args.tree_id,))
    tree_row = cursor.fetchone()
    if not tree_row:
        print(f"Tree {args.tree_id} not found in database")
        sys.exit(1)
    tree_db_id = tree_row[0]

    # Get people to process (filter by birth year for census era)
    query = """
        SELECT p.id, p.forename || ' ' || p.surname, p.ancestry_person_id, p.birth_year_estimate
        FROM person p
        WHERE p.tree_id = ?
        AND p.ancestry_person_id IS NOT NULL
        AND p.birth_year_estimate BETWEEN ? AND ?
    """
    if args.skip_processed:
        query += """
        AND p.ancestry_person_id NOT IN (
            SELECT ancestry_person_id FROM census_import_progress
        )
        """
    query += " ORDER BY p.birth_year_estimate ASC NULLS LAST"

    if args.limit > 0:
        query += f" LIMIT {args.limit}"

    cursor.execute(query, (tree_db_id, args.min_year, args.max_year))
    people = cursor.fetchall()

    print(f"Found {len(people)} people to process from tree {args.tree_id}")

    if not people:
        print("No people to process. Use --skip-processed=False to reprocess.")
        return

    # Create session
    session = make_session()

    # Stats
    total_census_records = 0
    people_with_census = 0

    for i, (person_id, name, ancestry_person_id, birth_year) in enumerate(people, 1):
        print(f"\n[{i}/{len(people)}] {name} (b. {birth_year or '?'})")

        # Get census sources from profile
        census_sources = extract_census_sources(session, args.tree_id, ancestry_person_id)

        if not census_sources:
            print(f"  No census sources found")
            # Mark as processed
            cursor.execute("""
                INSERT OR REPLACE INTO census_import_progress
                (ancestry_person_id, census_count) VALUES (?, 0)
            """, (ancestry_person_id,))
            conn.commit()
            time.sleep(args.delay)
            continue

        print(f"  Found {len(census_sources)} census sources")
        person_census_count = 0

        for cs in census_sources:
            print(f"    - {cs['year']}: {cs['title']}")

            # Fetch full record
            raw_data = extract_census_record(
                session, cs['source_id'], cs['record_id'],
                args.tree_id, ancestry_person_id
            )

            if raw_data:
                # Parse and store
                record = parse_census_data(
                    raw_data, cs['year'], cs['source_id'], cs['record_id']
                )
                store_census_record(
                    conn, record, person_id, cs['record_id'], cs['source_id']
                )
                person_census_count += 1
                total_census_records += 1

                # Show extracted info
                age = record.get('age_as_recorded', '?')
                place = record.get('birth_place_as_recorded', record.get('address', '?'))
                print(f"      Stored: age {age}, {place[:50]}")
            else:
                print(f"      Could not extract record details")

            time.sleep(args.delay / 2)  # Shorter delay between records for same person

        if person_census_count > 0:
            people_with_census += 1

        # Mark as processed
        cursor.execute("""
            INSERT OR REPLACE INTO census_import_progress
            (ancestry_person_id, census_count) VALUES (?, ?)
        """, (ancestry_person_id, person_census_count))
        conn.commit()

        time.sleep(args.delay)

    print(f"\n{'='*60}")
    print(f"COMPLETE")
    print(f"  People processed: {len(people)}")
    print(f"  People with census: {people_with_census}")
    print(f"  Census records stored: {total_census_records}")
    print(f"{'='*60}")

    conn.close()


if __name__ == '__main__':
    main()
