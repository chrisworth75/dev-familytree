#!/usr/bin/env python3
"""
Search UK Census Online by surname and match results to all family members.

More efficient than person-by-person search when doing manual CAPTCHA solving.

Usage:
    # Search for all Wrathalls in My Tree
    python scripts/census_by_surname.py --surname Wrathall --tree-id 1

    # Search and store results
    python scripts/census_by_surname.py --surname Virgo --tree-id 1 --store
"""

import argparse
import sqlite3
import re
from pathlib import Path

from search_ukcensus_online import search_census

DB_PATH = Path(__file__).parent.parent / "genealogy.db"


def get_persons_for_surname(surname, tree_id=None):
    """Get all persons with given surname who need census records."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = """
        SELECT id, forename, surname, birth_year_estimate
        FROM person
        WHERE LOWER(surname) = LOWER(?)
        AND birth_year_estimate IS NOT NULL
        AND birth_year_estimate BETWEEN 1841 AND 1911
        AND id NOT IN (SELECT person_id FROM person_census)
        AND id NOT IN (SELECT person_id FROM person_census_link)
    """
    params = [surname]

    if tree_id:
        sql += " AND tree_id = ?"
        params.append(tree_id)

    sql += " ORDER BY birth_year_estimate"
    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def match_census_to_person(census_result, person):
    """Check if census result matches the person."""
    census_name = (census_result.get('name') or '').lower()
    person_forename = (person.get('forename') or '').lower().split()[0]  # First name only
    person_surname = (person.get('surname') or '').lower()

    # Name must contain surname
    if person_surname not in census_name:
        return False, "surname mismatch"

    # Check forename match (first name or initial)
    forename_match = False
    if person_forename:
        # Full first name match
        if person_forename in census_name:
            forename_match = True
        # Initial match (e.g., "J" matches "James")
        elif len(person_forename) >= 1:
            # Look for initial pattern like "J Wrathall" or "J. Wrathall"
            initial_pattern = rf'\b{person_forename[0]}\.?\s'
            if re.search(initial_pattern, census_name):
                forename_match = True

    if not forename_match:
        return False, "forename mismatch"

    # Check birth year (from census age or born_approx)
    person_birth = person.get('birth_year_estimate')
    if person_birth:
        census_birth = None

        # Try born_approx field
        if census_result.get('born_approx'):
            try:
                census_birth = int(census_result['born_approx'])
            except:
                pass

        # Try calculating from age and census year
        if not census_birth and census_result.get('age') and census_result.get('year'):
            try:
                census_birth = int(census_result['year']) - int(census_result['age'])
            except:
                pass

        if census_birth:
            diff = abs(person_birth - census_birth)
            if diff > 5:  # Allow 5 year tolerance
                return False, f"birth year off by {diff} years"

    return True, "match"


def store_census_for_person(census_result, person_id):
    """Store a census record linked to a person."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    year = None
    if census_result.get('year'):
        try:
            year = int(census_result['year'])
        except:
            pass

    age = None
    if census_result.get('age'):
        try:
            age = int(census_result['age'])
        except:
            pass

    name = census_result.get('name', '')

    # Check if this exact record already exists
    cursor.execute("""
        SELECT id FROM census_record
        WHERE year = ? AND name_as_recorded = ? AND source_url = 'https://ukcensusonline.com'
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
            census_result.get('county', ''),
            'https://ukcensusonline.com'
        ))
        census_id = cursor.lastrowid

    # Link to person
    cursor.execute("""
        INSERT OR IGNORE INTO person_census (person_id, census_record_id)
        VALUES (?, ?)
    """, (person_id, census_id))

    was_new = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return census_id, was_new


def main():
    parser = argparse.ArgumentParser(description='Search census by surname')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--tree-id', type=int, help='Filter by tree ID')
    parser.add_argument('--store', action='store_true', help='Store matched results')
    parser.add_argument('--headless', action='store_true', help='Run headless (needs API key)')
    args = parser.parse_args()

    # Get persons needing census records
    persons = get_persons_for_surname(args.surname, args.tree_id)

    if not persons:
        print(f"No persons with surname '{args.surname}' need census records.")
        return

    print(f"Found {len(persons)} {args.surname} family members needing census records:\n")
    for p in persons:
        print(f"  [{p['id']}] {p['forename']} {p['surname']} (b. ~{p['birth_year_estimate']})")

    print(f"\nSearching UK Census Online for surname: {args.surname}")
    print("A browser window will open - solve the CAPTCHA if prompted.\n")

    # Search census
    results = search_census(
        surname=args.surname,
        headless=args.headless
    )

    if not results:
        print("No census results found.")
        return

    print(f"\nFound {len(results)} census results. Matching to family members...\n")

    # Match results to persons
    matches = []
    for census in results:
        for person in persons:
            is_match, reason = match_census_to_person(census, person)
            if is_match:
                matches.append({
                    'census': census,
                    'person': person,
                    'reason': reason
                })

    if not matches:
        print("No matches found between census results and family members.")
        print("\nCensus results found:")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r.get('year')} - {r.get('name')} (age {r.get('age', '?')})")
        return

    # Group by person
    by_person = {}
    for m in matches:
        pid = m['person']['id']
        if pid not in by_person:
            by_person[pid] = {
                'person': m['person'],
                'records': []
            }
        by_person[pid]['records'].append(m['census'])

    print(f"Found {len(matches)} matches for {len(by_person)} people:\n")

    stored_count = 0
    for pid, data in by_person.items():
        person = data['person']
        records = data['records']
        print(f"\n{person['forename']} {person['surname']} (b. ~{person['birth_year_estimate']}) - ID {pid}")

        for r in records:
            year = r.get('year', '?')
            name = r.get('name', '?')
            age = r.get('age', '?')
            county = r.get('county', '?')
            print(f"  • {year} Census: {name}, age {age}, {county}")

            if args.store:
                census_id, was_new = store_census_for_person(r, pid)
                if was_new:
                    stored_count += 1
                    print(f"    → Stored (census_record.id={census_id})")
                else:
                    print(f"    → Already linked")

    if args.store:
        print(f"\nStored {stored_count} new census links.")


if __name__ == '__main__':
    main()
