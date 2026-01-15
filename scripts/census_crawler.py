#!/usr/bin/env python3
"""
Master census crawler - search all free UK genealogy sites for a person's records.

Coordinates searches across:
- FreeCEN (census 1841-1901)
- FamilySearch (census 1841-1911)
- FreeBMD (birth/marriage/death indexes)

Usage:
    # Search all sites for a specific person
    python scripts/census_crawler.py --surname Wrathall --forename Henry --birth-year 1863

    # Search for all people with a surname in the database
    python scripts/census_crawler.py --surname Virgo --from-database --tree-id 1

    # Search and store all results
    python scripts/census_crawler.py --surname Wrathall --forename Henry --birth-year 1863 --store

    # Only search specific sites
    python scripts/census_crawler.py --surname Wrathall --sites freecen,freebmd
"""

import argparse
import sqlite3
import time
from pathlib import Path
from datetime import datetime

# Import search modules
try:
    from search_freecen import search_freecen, store_results as store_freecen
except ImportError:
    search_freecen = None

try:
    from search_familysearch import search_familysearch, store_results as store_familysearch
except ImportError:
    search_familysearch = None

try:
    from search_freebmd import search_freebmd, store_results as store_freebmd
except ImportError:
    search_freebmd = None

DB_PATH = Path(__file__).parent.parent / "genealogy.db"

# Census years a person could appear in based on birth year
def get_census_years(birth_year):
    """Get census years a person could realistically appear in."""
    if not birth_year:
        return [1841, 1851, 1861, 1871, 1881, 1891, 1901, 1911]

    years = []
    for census_year in [1841, 1851, 1861, 1871, 1881, 1891, 1901, 1911]:
        age_at_census = census_year - birth_year
        # Include if person would be 0-90 years old
        if 0 <= age_at_census <= 90:
            years.append(census_year)
    return years


def search_all_sites(surname, forename=None, birth_year=None, sites=None, headless=True):
    """
    Search all configured sites for records matching the person.
    Returns dict of results by site.
    """
    all_results = {
        'freecen': [],
        'familysearch': [],
        'freebmd_births': [],
        'freebmd_marriages': [],
        'freebmd_deaths': []
    }

    if sites is None:
        sites = ['freecen', 'familysearch', 'freebmd']

    print(f"\n{'='*60}")
    print(f"Searching for: {forename or ''} {surname}")
    if birth_year:
        print(f"Birth year: ~{birth_year}")
        print(f"Expected censuses: {get_census_years(birth_year)}")
    print(f"Sites: {', '.join(sites)}")
    print('='*60)

    # FreeCEN search
    if 'freecen' in sites and search_freecen:
        print(f"\n--- FreeCEN ---")
        try:
            results = search_freecen(
                surname=surname,
                forename=forename,
                birth_year=birth_year,
                headless=headless
            )
            all_results['freecen'] = results
            print(f"Found {len(results)} FreeCEN records")
        except Exception as e:
            print(f"FreeCEN error: {e}")
        time.sleep(2)  # Be nice to the servers

    # FamilySearch search
    if 'familysearch' in sites and search_familysearch:
        print(f"\n--- FamilySearch ---")
        try:
            results = search_familysearch(
                surname=surname,
                forename=forename,
                birth_year=birth_year,
                headless=headless
            )
            all_results['familysearch'] = results
            print(f"Found {len(results)} FamilySearch records")
        except Exception as e:
            print(f"FamilySearch error: {e}")
        time.sleep(2)

    # FreeBMD searches (births, marriages, deaths)
    if 'freebmd' in sites and search_freebmd:
        # Search births
        print(f"\n--- FreeBMD Births ---")
        try:
            year_from = birth_year - 2 if birth_year else None
            year_to = birth_year + 2 if birth_year else None
            results = search_freebmd(
                surname=surname,
                forename=forename,
                record_type='births',
                year_from=year_from,
                year_to=year_to,
                headless=headless
            )
            all_results['freebmd_births'] = results
            print(f"Found {len(results)} birth records")
        except Exception as e:
            print(f"FreeBMD births error: {e}")
        time.sleep(2)

        # Search marriages (if we have approximate dates)
        print(f"\n--- FreeBMD Marriages ---")
        try:
            # Assume marriage between ages 18-50
            year_from = birth_year + 18 if birth_year else None
            year_to = birth_year + 50 if birth_year else None
            results = search_freebmd(
                surname=surname,
                forename=forename,
                record_type='marriages',
                year_from=year_from,
                year_to=year_to,
                headless=headless
            )
            all_results['freebmd_marriages'] = results
            print(f"Found {len(results)} marriage records")
        except Exception as e:
            print(f"FreeBMD marriages error: {e}")
        time.sleep(2)

        # Search deaths
        print(f"\n--- FreeBMD Deaths ---")
        try:
            # Assume death between ages 0-100
            year_from = birth_year if birth_year else None
            year_to = birth_year + 100 if birth_year else None
            results = search_freebmd(
                surname=surname,
                forename=forename,
                record_type='deaths',
                year_from=year_from,
                year_to=year_to,
                headless=headless
            )
            all_results['freebmd_deaths'] = results
            print(f"Found {len(results)} death records")
        except Exception as e:
            print(f"FreeBMD deaths error: {e}")

    return all_results


def get_persons_to_search(surname=None, tree_id=None, person_id=None, limit=50):
    """Get list of people from database who need census records."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    conditions = []
    params = []

    if person_id:
        conditions.append("p.id = ?")
        params.append(person_id)
    else:
        if surname:
            conditions.append("LOWER(p.surname) = LOWER(?)")
            params.append(surname)

        if tree_id:
            conditions.append("p.tree_id = ?")
            params.append(tree_id)

        # Only people in census era (born 1835-1905)
        conditions.append("p.birth_year_estimate BETWEEN 1835 AND 1905")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    cursor.execute(f"""
        SELECT p.id, p.forename, p.surname, p.birth_year_estimate,
               COUNT(pcl.id) as census_count
        FROM person p
        LEFT JOIN person_census_link pcl ON p.id = pcl.person_id
        WHERE {where_clause}
        GROUP BY p.id
        HAVING census_count < 7  -- Missing some census records
        ORDER BY census_count ASC, p.birth_year_estimate
        LIMIT ?
    """, params + [limit])

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def store_all_results(all_results, person_id=None):
    """Store all results from all sites."""
    stored = {
        'freecen': 0,
        'familysearch': 0,
        'freebmd': 0
    }

    if all_results.get('freecen') and store_freecen:
        stored['freecen'] = store_freecen(all_results['freecen'], person_id)

    if all_results.get('familysearch') and store_familysearch:
        stored['familysearch'] = store_familysearch(all_results['familysearch'], person_id)

    if store_freebmd:
        for key in ['freebmd_births', 'freebmd_marriages', 'freebmd_deaths']:
            if all_results.get(key):
                stored['freebmd'] += store_freebmd(all_results[key], person_id)

    return stored


def print_summary(all_results):
    """Print summary of all results found."""
    print(f"\n{'='*60}")
    print("SEARCH SUMMARY")
    print('='*60)

    total = 0

    if all_results.get('freecen'):
        count = len(all_results['freecen'])
        total += count
        print(f"\nFreeCEN Census Records ({count}):")
        for r in all_results['freecen'][:5]:
            print(f"  - {r.get('name', 'Unknown')}, {r.get('year', '?')} census")
        if count > 5:
            print(f"  ... and {count - 5} more")

    if all_results.get('familysearch'):
        count = len(all_results['familysearch'])
        total += count
        print(f"\nFamilySearch Records ({count}):")
        for r in all_results['familysearch'][:5]:
            print(f"  - {r.get('name', 'Unknown')}, {r.get('year', '?')}")
        if count > 5:
            print(f"  ... and {count - 5} more")

    if all_results.get('freebmd_births'):
        count = len(all_results['freebmd_births'])
        total += count
        print(f"\nFreeBMD Birth Records ({count}):")
        for r in all_results['freebmd_births'][:5]:
            print(f"  - {r.get('name', 'Unknown')}, {r.get('date', '?')}, {r.get('district', '?')}")
        if count > 5:
            print(f"  ... and {count - 5} more")

    if all_results.get('freebmd_marriages'):
        count = len(all_results['freebmd_marriages'])
        total += count
        print(f"\nFreeBMD Marriage Records ({count}):")
        for r in all_results['freebmd_marriages'][:5]:
            spouse = r.get('spouse', '')
            print(f"  - {r.get('name', 'Unknown')} & {spouse}, {r.get('date', '?')}")
        if count > 5:
            print(f"  ... and {count - 5} more")

    if all_results.get('freebmd_deaths'):
        count = len(all_results['freebmd_deaths'])
        total += count
        print(f"\nFreeBMD Death Records ({count}):")
        for r in all_results['freebmd_deaths'][:5]:
            age = r.get('age', '?')
            print(f"  - {r.get('name', 'Unknown')}, age {age}, {r.get('date', '?')}")
        if count > 5:
            print(f"  ... and {count - 5} more")

    print(f"\n{'='*60}")
    print(f"TOTAL RECORDS FOUND: {total}")
    print('='*60)


def main():
    parser = argparse.ArgumentParser(
        description='Search all free UK genealogy sites for a person',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for a specific person
  python census_crawler.py --surname Wrathall --forename Henry --birth-year 1863

  # Search for all Virgos in database tree 1
  python census_crawler.py --surname Virgo --from-database --tree-id 1

  # Only search FreeCEN and FreeBMD
  python census_crawler.py --surname Wrathall --sites freecen,freebmd

  # Store results in database
  python census_crawler.py --surname Wrathall --forename Henry --birth-year 1863 --store
        """
    )

    parser.add_argument('--surname', required=True, help='Surname to search')
    parser.add_argument('--forename', help='Forename to search')
    parser.add_argument('--birth-year', type=int, help='Birth year (approx)')
    parser.add_argument('--sites', help='Comma-separated list of sites (freecen,familysearch,freebmd)')
    parser.add_argument('--from-database', action='store_true',
                       help='Search for all matching people in database')
    parser.add_argument('--tree-id', type=int, help='Tree ID to search (with --from-database)')
    parser.add_argument('--person-id', type=int, help='Specific person ID to search')
    parser.add_argument('--limit', type=int, default=10,
                       help='Max people to search (with --from-database)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browsers headless (default)')
    parser.add_argument('--no-headless', action='store_true', help='Show browsers')
    parser.add_argument('--store', action='store_true', help='Store results in database')

    args = parser.parse_args()

    headless = not args.no_headless

    # Parse sites list
    sites = None
    if args.sites:
        sites = [s.strip().lower() for s in args.sites.split(',')]

    # Check which search modules are available
    available = []
    if search_freecen:
        available.append('freecen')
    if search_familysearch:
        available.append('familysearch')
    if search_freebmd:
        available.append('freebmd')

    print(f"Available search modules: {', '.join(available)}")

    if args.from_database:
        # Search for multiple people from database
        persons = get_persons_to_search(
            surname=args.surname,
            tree_id=args.tree_id,
            person_id=args.person_id,
            limit=args.limit
        )

        print(f"\nFound {len(persons)} people to search")

        for person in persons:
            print(f"\n{'#'*60}")
            print(f"# Searching for: {person['forename']} {person['surname']} (b. {person['birth_year_estimate']})")
            print(f"# Person ID: {person['id']}, Current census records: {person['census_count']}")
            print('#'*60)

            all_results = search_all_sites(
                surname=person['surname'],
                forename=person['forename'],
                birth_year=person['birth_year_estimate'],
                sites=sites,
                headless=headless
            )

            print_summary(all_results)

            if args.store:
                stored = store_all_results(all_results, person['id'])
                print(f"\nStored: FreeCEN={stored['freecen']}, FamilySearch={stored['familysearch']}, FreeBMD={stored['freebmd']}")

            # Rate limiting between people
            time.sleep(5)

    else:
        # Search for single person
        all_results = search_all_sites(
            surname=args.surname,
            forename=args.forename,
            birth_year=args.birth_year,
            sites=sites,
            headless=headless
        )

        print_summary(all_results)

        if args.store:
            stored = store_all_results(all_results, args.person_id)
            print(f"\nStored: FreeCEN={stored['freecen']}, FamilySearch={stored['familysearch']}, FreeBMD={stored['freebmd']}")


if __name__ == '__main__':
    main()
