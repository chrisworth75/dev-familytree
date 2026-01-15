#!/usr/bin/env python3
"""
Batch search UK Census Online for multiple family members.

This script queries the database for family members and searches for their
census records on ukcensusonline.com.

Usage:
    # Search for all Wrathalls born 1850-1920
    python scripts/batch_census_search.py --surname Wrathall --min-birth 1850 --max-birth 1920

    # Search specific people by ID
    python scripts/batch_census_search.py --person-ids 511093,519062

    # Dry run (show who would be searched)
    python scripts/batch_census_search.py --surname Wrathall --dry-run

    # Automated mode (requires CAPSOLVER_API_KEY)
    CAPSOLVER_API_KEY=xxx python scripts/batch_census_search.py --surname Wrathall --headless

Requirements:
    - Set CAPSOLVER_API_KEY for headless automation (~$0.002 per CAPTCHA)
    - Without API key, uses visible browser (manual CAPTCHA solving)
"""

import argparse
import sqlite3
import time
from pathlib import Path

# Import from the single-search script
from search_ukcensus_online import search_census, store_results, CAPSOLVER_API_KEY

DB_PATH = Path(__file__).parent.parent / "genealogy.db"


def get_persons_to_search(surname=None, person_ids=None, min_birth=None, max_birth=None,
                          skip_with_census=True, limit=50):
    """Get list of persons to search from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if person_ids:
        # Search specific person IDs
        placeholders = ','.join('?' * len(person_ids))
        sql = f"""
            SELECT id, forename, surname, birth_year_estimate
            FROM person
            WHERE id IN ({placeholders})
            ORDER BY surname, forename
        """
        cursor.execute(sql, person_ids)
    else:
        # Build query based on criteria
        conditions = []
        params = []

        if surname:
            conditions.append("surname LIKE ?")
            params.append(f"%{surname}%")

        if min_birth:
            conditions.append("birth_year_estimate >= ?")
            params.append(min_birth)

        if max_birth:
            conditions.append("birth_year_estimate <= ?")
            params.append(max_birth)

        # Require at least forename or surname
        conditions.append("(forename IS NOT NULL OR surname IS NOT NULL)")

        if skip_with_census:
            # Skip people who already have census records linked
            conditions.append("""
                id NOT IN (
                    SELECT DISTINCT person_id FROM person_census
                    UNION
                    SELECT DISTINCT person_id FROM person_census_link
                )
            """)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT id, forename, surname, birth_year_estimate
            FROM person
            WHERE {where_clause}
            ORDER BY surname, forename
            LIMIT ?
        """
        params.append(limit)
        cursor.execute(sql, params)

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def match_census_to_person(census_result, person):
    """Check if census result matches the person we searched for."""
    census_name = census_result.get('name', '').lower()
    person_forename = (person.get('forename') or '').lower()
    person_surname = (person.get('surname') or '').lower()

    # Check name match
    name_match = False
    if person_forename and person_surname:
        # Check if both names appear in census name
        if person_forename in census_name and person_surname in census_name:
            name_match = True
        # Also check first initial match (e.g., "Leslie G" matches "Leslie Gordon")
        elif person_forename.split()[0] in census_name and person_surname in census_name:
            name_match = True
    elif person_surname:
        name_match = person_surname in census_name

    # Check birth year if available
    birth_match = True
    if person.get('birth_year_estimate') and census_result.get('born_approx'):
        try:
            person_birth = int(person['birth_year_estimate'])
            census_birth = int(census_result['born_approx'])
            # Allow ±3 year tolerance
            birth_match = abs(person_birth - census_birth) <= 3
        except ValueError:
            pass

    return name_match and birth_match


def run_batch_search(persons, headless=True, store=False, delay=5):
    """Run census search for multiple persons."""
    total = len(persons)
    results_summary = []

    for i, person in enumerate(persons, 1):
        person_id = person['id']
        forename = person.get('forename') or ''
        surname = person.get('surname') or ''
        birth_year = person.get('birth_year_estimate')

        print(f"\n{'='*60}")
        print(f"[{i}/{total}] Searching for: {forename} {surname}")
        if birth_year:
            print(f"         Birth year: ~{birth_year}")
        print('='*60)

        # Search census
        try:
            results = search_census(
                surname=surname,
                forename=forename,
                birth_year=birth_year,
                headless=headless
            )

            # Filter to matching results
            matching_results = [r for r in results if match_census_to_person(r, person)]

            print(f"\nFound {len(results)} total results, {len(matching_results)} matching")

            if matching_results:
                for j, r in enumerate(matching_results, 1):
                    print(f"  [{j}] {r.get('year')} - {r.get('name')} (age {r.get('age', '?')})")

                if store:
                    # Only store matching results
                    stored = store_matching_results(matching_results, person_id)
                    print(f"  Stored {stored} records for person ID {person_id}")

            results_summary.append({
                'person_id': person_id,
                'name': f"{forename} {surname}".strip(),
                'total_results': len(results),
                'matching_results': len(matching_results)
            })

        except Exception as e:
            print(f"  Error searching: {e}")
            results_summary.append({
                'person_id': person_id,
                'name': f"{forename} {surname}".strip(),
                'error': str(e)
            })

        # Delay between searches to be respectful
        if i < total:
            print(f"\nWaiting {delay} seconds before next search...")
            time.sleep(delay)

    return results_summary


def store_matching_results(results, person_id):
    """Store census results linked to a specific person."""
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

        # Check if this record already exists
        cursor.execute("""
            SELECT id FROM census_record
            WHERE year = ? AND name_as_recorded = ? AND source_url = 'ukcensusonline.com'
        """, (year, r.get('name', '')))

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
                r.get('name', ''),
                age_int,
                r.get('county', ''),
                'ukcensusonline.com'
            ))
            census_id = cursor.lastrowid

        # Link to person (if not already linked)
        cursor.execute("""
            INSERT OR IGNORE INTO person_census (person_id, census_record_id)
            VALUES (?, ?)
        """, (person_id, census_id))

        if cursor.rowcount > 0:
            stored += 1

    conn.commit()
    conn.close()
    return stored


def main():
    parser = argparse.ArgumentParser(description='Batch search UK Census Online')
    parser.add_argument('--surname', help='Surname to search')
    parser.add_argument('--person-ids', help='Comma-separated person IDs')
    parser.add_argument('--min-birth', type=int, help='Minimum birth year')
    parser.add_argument('--max-birth', type=int, help='Maximum birth year')
    parser.add_argument('--limit', type=int, default=50, help='Max persons to search')
    parser.add_argument('--include-with-census', action='store_true',
                       help='Include people who already have census records')
    parser.add_argument('--headless', action='store_true',
                       help='Run headless (requires CAPSOLVER_API_KEY)')
    parser.add_argument('--store', action='store_true', help='Store results in database')
    parser.add_argument('--delay', type=int, default=5, help='Seconds between searches')
    parser.add_argument('--dry-run', action='store_true', help='Show who would be searched')
    args = parser.parse_args()

    # Parse person IDs
    person_ids = None
    if args.person_ids:
        person_ids = [int(x.strip()) for x in args.person_ids.split(',')]

    # Get persons to search
    persons = get_persons_to_search(
        surname=args.surname,
        person_ids=person_ids,
        min_birth=args.min_birth,
        max_birth=args.max_birth,
        skip_with_census=not args.include_with_census,
        limit=args.limit
    )

    if not persons:
        print("No persons found matching criteria.")
        return

    print(f"Found {len(persons)} persons to search:\n")
    for i, p in enumerate(persons, 1):
        birth = f" (b. ~{p['birth_year_estimate']})" if p.get('birth_year_estimate') else ""
        print(f"  {i}. [{p['id']}] {p.get('forename', '')} {p.get('surname', '')}{birth}")

    if args.dry_run:
        print("\n[DRY RUN] Would search for the above persons.")
        return

    # Check for API key if headless
    if args.headless and not CAPSOLVER_API_KEY:
        print("\nWARNING: Headless mode requires CAPSOLVER_API_KEY")
        print("Set the environment variable or run without --headless")
        return

    print(f"\nMode: {'headless' if args.headless else 'visible browser'}")
    if CAPSOLVER_API_KEY:
        print("CAPTCHA solver: CapSolver API enabled")
    print(f"Store results: {args.store}")
    print(f"Delay between searches: {args.delay}s")

    # Confirm
    input("\nPress Enter to start batch search...")

    # Run batch search
    summary = run_batch_search(
        persons,
        headless=args.headless,
        store=args.store,
        delay=args.delay
    )

    # Print summary
    print("\n" + "="*60)
    print("BATCH SEARCH SUMMARY")
    print("="*60)

    for s in summary:
        if 'error' in s:
            print(f"  [{s['person_id']}] {s['name']}: ERROR - {s['error']}")
        else:
            print(f"  [{s['person_id']}] {s['name']}: {s['matching_results']} matches (of {s['total_results']} results)")


if __name__ == '__main__':
    main()
