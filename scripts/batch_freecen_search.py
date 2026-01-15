#!/usr/bin/env python3
"""
Batch search FreeCEN for census records by surname.

FreeCEN is fully automated (no CAPTCHA) - searches all census records for a surname
and matches them to family members in the database.

Usage:
    # Search for all Virgos in My Tree
    python scripts/batch_freecen_search.py --surname Virgo --tree-id 1

    # Search and store results
    python scripts/batch_freecen_search.py --surname Virgo --tree-id 1 --store

    # Headless mode (default)
    python scripts/batch_freecen_search.py --surname Virgo --tree-id 1 --store --headless
"""

import argparse
import sqlite3
import re
from pathlib import Path

from search_freecen import search_freecen

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
        AND birth_year_estimate BETWEEN 1835 AND 1905
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
    """
    Check if census result matches the person.
    Returns (match_score, reason) - score 0-100, higher is better.
    """
    score = 0
    reasons = []

    census_name = (census_result.get('name') or '').lower()
    person_forename = (person.get('forename') or '').lower()
    person_surname = (person.get('surname') or '').lower()

    # Name must contain surname
    if person_surname not in census_name:
        return 0, "surname mismatch"

    # Check forename match
    if person_forename:
        first_name = person_forename.split()[0]  # First name only

        # Full first name match
        if first_name in census_name:
            score += 40
            reasons.append("forename match")
        # Initial match (e.g., "J" matches "James")
        elif len(first_name) >= 1:
            # Check if census name starts with initial
            name_parts = census_name.replace(person_surname, '').strip().split()
            for part in name_parts:
                if part and part[0] == first_name[0]:
                    score += 20
                    reasons.append("initial match")
                    break

        if score == 0:
            return 0, "forename mismatch"
    else:
        score += 10  # Weak match if no forename to check

    # Check birth year
    person_birth = person.get('birth_year_estimate')
    census_birth = None

    if census_result.get('born_approx'):
        try:
            census_birth = int(census_result['born_approx'])
        except:
            pass

    if person_birth and census_birth:
        diff = abs(person_birth - census_birth)
        if diff == 0:
            score += 40
            reasons.append("exact birth year")
        elif diff <= 1:
            score += 35
            reasons.append(f"birth year ±1")
        elif diff <= 2:
            score += 30
            reasons.append(f"birth year ±2")
        elif diff <= 3:
            score += 20
            reasons.append(f"birth year ±3")
        elif diff <= 5:
            score += 10
            reasons.append(f"birth year ±5")
        else:
            return 0, f"birth year off by {diff} years"
    else:
        score += 10  # Small score if can't verify birth year

    # Bonus for birthplace matching person's known location (if we add that later)

    if score >= 50:
        return score, ", ".join(reasons)
    else:
        return 0, "score too low"


def search_per_person(persons, headless, store, min_score):
    """Search for each person individually - slower but handles common surnames."""
    import time

    total = len(persons)
    all_matches = []

    for i, person in enumerate(persons, 1):
        forename = person.get('forename') or ''
        surname = person.get('surname') or ''
        birth_year = person.get('birth_year_estimate')
        person_id = person['id']

        print(f"\n[{i}/{total}] Searching for: {forename} {surname} (b. ~{birth_year})")

        # Search with forename to narrow results
        results = search_freecen(
            surname=surname,
            forename=forename.split()[0] if forename else None,  # First name only
            birth_year=birth_year,
            headless=headless
        )

        if results:
            # Match results to this person
            matches = []
            for census in results:
                score, reason = match_census_to_person(census, person)
                if score >= min_score:
                    matches.append({
                        'census': census,
                        'score': score,
                        'reason': reason
                    })

            if matches:
                matches.sort(key=lambda x: -x['score'])
                print(f"  Found {len(matches)} matching census records:")

                for m in matches:
                    r = m['census']
                    print(f"    • {r.get('year')} - {r.get('name')}, age {r.get('age', '?')}, from {r.get('birth_place', '?')}")
                    print(f"      Score: {m['score']} ({m['reason']})")

                    if store:
                        census_id, was_new = store_census_for_person(r, person_id)
                        if was_new:
                            print(f"      → Stored (census_record.id={census_id})")
                        else:
                            print(f"      → Already linked")

                    all_matches.append({
                        'person': person,
                        'census': m['census'],
                        'score': m['score']
                    })
            else:
                print(f"  No matching records (found {len(results)} results but none matched)")
        else:
            print(f"  No results found")

        # Small delay between searches to be polite
        if i < total:
            time.sleep(1)

    print(f"\n{'='*60}")
    print(f"SUMMARY: Found {len(all_matches)} census matches for {len(persons)} people")
    return all_matches


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
    birth_place = census_result.get('birth_place', '')
    county = census_result.get('county', '')
    district = census_result.get('district', '')

    # Combine location info
    address = f"{district}, {county}" if district and county else (district or county)

    # Check if this exact record already exists
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
                birth_place_as_recorded, registration_district, source_url
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            year,
            name,
            age,
            birth_place,
            address,
            'https://freecen.org.uk'
        ))
        census_id = cursor.lastrowid

    # Link to person (if not already linked)
    cursor.execute("""
        INSERT OR IGNORE INTO person_census (person_id, census_record_id)
        VALUES (?, ?)
    """, (person_id, census_id))

    was_new = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return census_id, was_new


def main():
    parser = argparse.ArgumentParser(description='Batch search FreeCEN by surname')
    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--tree-id', type=int, help='Filter by tree ID')
    parser.add_argument('--store', action='store_true', help='Store matched results')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run headless (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show browser')
    parser.add_argument('--min-score', type=int, default=50,
                       help='Minimum match score (0-100, default 50)')
    parser.add_argument('--per-person', action='store_true',
                       help='Search for each person individually (slower but handles common surnames)')
    args = parser.parse_args()

    headless = not args.no_headless

    # Get persons needing census records
    persons = get_persons_for_surname(args.surname, args.tree_id)

    if not persons:
        print(f"No persons with surname '{args.surname}' need census records.")
        return

    print(f"Found {len(persons)} {args.surname} family members needing census records:\n")
    for p in persons:
        print(f"  [{p['id']}] {p['forename']} {p['surname']} (b. ~{p['birth_year_estimate']})")

    print(f"\nMode: {'headless' if headless else 'visible browser'}")
    print("FreeCEN has NO CAPTCHA - fully automated\n")

    # If per-person mode, search for each person individually
    if args.per_person:
        print("Searching per-person (handles common surnames)...")
        search_per_person(persons, headless, args.store, args.min_score)
        return

    # Otherwise, do bulk surname search
    print(f"Searching FreeCEN for surname: {args.surname}")

    # Search FreeCEN
    results = search_freecen(
        surname=args.surname,
        headless=headless
    )

    if not results:
        print("\nNo census results found. This may be because:")
        print("  - The surname has too many results (>1000)")
        print("  - Try running with --per-person flag to search each person individually")
        return

    print(f"\nFound {len(results)} census results. Matching to family members...\n")

    # Match results to persons
    matches = []
    for census in results:
        for person in persons:
            score, reason = match_census_to_person(census, person)
            if score >= args.min_score:
                matches.append({
                    'census': census,
                    'person': person,
                    'score': score,
                    'reason': reason
                })

    if not matches:
        print("No matches found between census results and family members.")
        print("\nSample census results found:")
        for i, r in enumerate(results[:10], 1):
            print(f"  {i}. {r.get('year')} - {r.get('name')} (b. ~{r.get('born_approx', '?')})")
        return

    # Group by person and sort by score
    by_person = {}
    for m in matches:
        pid = m['person']['id']
        if pid not in by_person:
            by_person[pid] = {
                'person': m['person'],
                'records': []
            }
        by_person[pid]['records'].append({
            'census': m['census'],
            'score': m['score'],
            'reason': m['reason']
        })

    # Sort records by score within each person
    for pid in by_person:
        by_person[pid]['records'].sort(key=lambda x: (-x['score'], x['census'].get('year', '')))

    print(f"Found {len(matches)} potential matches for {len(by_person)} people:\n")

    stored_count = 0
    for pid, data in by_person.items():
        person = data['person']
        records = data['records']
        print(f"\n{person['forename']} {person['surname']} (b. ~{person['birth_year_estimate']}) - ID {pid}")

        for rec in records:
            r = rec['census']
            year = r.get('year', '?')
            name = r.get('name', '?')
            age = r.get('age', '?')
            birth_place = r.get('birth_place', '?')
            district = r.get('district', '?')
            score = rec['score']
            reason = rec['reason']

            print(f"  • {year} Census: {name}, age {age}, from {birth_place}")
            print(f"    Location: {district} | Score: {score} ({reason})")

            if args.store:
                census_id, was_new = store_census_for_person(r, pid)
                if was_new:
                    stored_count += 1
                    print(f"    → Stored (census_record.id={census_id})")
                else:
                    print(f"    → Already linked")

    if args.store:
        print(f"\n{'='*60}")
        print(f"Stored {stored_count} new census links.")


if __name__ == '__main__':
    main()
