#!/usr/bin/env python3
"""
Import Wrathall family data from WikiTree.

This script scrapes WikiTree profiles for the Wrathall surname and imports
family relationship data into our database.

Usage:
    python scripts/import_wikitree_wrathalls.py
    python scripts/import_wikitree_wrathalls.py --profile Wrathall-168
"""

import argparse
import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

DB_PATH = 'genealogy.db'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def get_db():
    return sqlite3.connect(DB_PATH)

def fetch_wikitree_profile(profile_id):
    """Fetch a WikiTree profile page."""
    url = f"https://www.wikitree.com/wiki/{profile_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching {profile_id}: {e}")
    return None

def parse_wikitree_profile(html, profile_id):
    """Parse WikiTree profile HTML to extract person and family data."""
    soup = BeautifulSoup(html, 'html.parser')

    data = {
        'wikitree_id': profile_id,
        'forename': None,
        'surname': None,
        'birth_date': None,
        'birth_place': None,
        'death_date': None,
        'death_place': None,
        'father_id': None,
        'mother_id': None,
        'spouse_ids': [],
        'children_ids': [],
    }

    # Try to find name from title or header
    title = soup.find('title')
    if title:
        # Title format: "FirstName LastName (1900-1980) | WikiTree FREE Family Tree"
        title_text = title.get_text()
        match = re.match(r'([^(|]+)', title_text)
        if match:
            name_parts = match.group(1).strip().split()
            if len(name_parts) >= 2:
                data['surname'] = name_parts[-1]
                data['forename'] = ' '.join(name_parts[:-1])

    # Look for birth/death dates in various formats
    text = soup.get_text()

    # Pattern: "Born 13 Dec 1914" or "b. 1914"
    birth_match = re.search(r'(?:Born|b\.)\s*(\d{1,2}\s+\w+\s+\d{4}|\d{4})', text)
    if birth_match:
        data['birth_date'] = birth_match.group(1)

    # Pattern: "Died 12 Feb 1954" or "d. 1954"
    death_match = re.search(r'(?:Died|d\.)\s*(\d{1,2}\s+\w+\s+\d{4}|\d{4})', text)
    if death_match:
        data['death_date'] = death_match.group(1)

    # Look for family links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if '/wiki/' in href and 'Wrathall-' in href or any(x in href for x in ['-', '_']):
            # Check context to determine relationship
            parent_text = link.find_parent().get_text() if link.find_parent() else ''
            link_id = href.split('/wiki/')[-1] if '/wiki/' in href else None

            if link_id:
                if 'father' in parent_text.lower():
                    data['father_id'] = link_id
                elif 'mother' in parent_text.lower():
                    data['mother_id'] = link_id
                elif 'spouse' in parent_text.lower() or 'married' in parent_text.lower():
                    data['spouse_ids'].append(link_id)
                elif 'child' in parent_text.lower() or 'son' in parent_text.lower() or 'daughter' in parent_text.lower():
                    data['children_ids'].append(link_id)

    return data

def get_wrathall_profiles():
    """Get list of Wrathall profile IDs from the genealogy page."""
    url = "https://www.wikitree.com/genealogy/WRATHALL"
    profiles = []

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all profile links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if '/wiki/Wrathall-' in href:
                    profile_id = href.split('/wiki/')[-1]
                    if profile_id not in profiles:
                        profiles.append(profile_id)
    except Exception as e:
        print(f"Error fetching profile list: {e}")

    return profiles

def save_to_db(data):
    """Save parsed WikiTree data to database."""
    conn = get_db()
    cursor = conn.cursor()

    # Check if person already exists with this WikiTree ID
    cursor.execute(
        "SELECT id FROM person WHERE notes LIKE ?",
        (f'%WikiTree: {data["wikitree_id"]}%',)
    )
    existing = cursor.fetchone()

    if existing:
        print(f"  Already in DB: {data['forename']} {data['surname']} (ID: {existing[0]})")
        return existing[0]

    # Parse birth year from date
    birth_year = None
    if data['birth_date']:
        year_match = re.search(r'\d{4}', data['birth_date'])
        if year_match:
            birth_year = int(year_match.group())

    death_year = None
    if data['death_date']:
        year_match = re.search(r'\d{4}', data['death_date'])
        if year_match:
            death_year = int(year_match.group())

    # Insert person
    notes = f"WikiTree: {data['wikitree_id']}"
    if data['father_id']:
        notes += f"\nFather WikiTree: {data['father_id']}"
    if data['mother_id']:
        notes += f"\nMother WikiTree: {data['mother_id']}"
    if data['children_ids']:
        notes += f"\nChildren WikiTree: {', '.join(data['children_ids'])}"

    cursor.execute("""
        INSERT INTO person (forename, surname, birth_year_estimate, death_year_estimate,
                           birth_place, notes, source)
        VALUES (?, ?, ?, ?, ?, ?, 'WikiTree')
    """, (data['forename'], data['surname'], birth_year, death_year,
          data['birth_place'], notes))

    person_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"  Added: {data['forename']} {data['surname']} ({birth_year}-{death_year}) ID: {person_id}")
    return person_id

def main():
    parser = argparse.ArgumentParser(description='Import Wrathall data from WikiTree')
    parser.add_argument('--profile', help='Specific profile ID to import (e.g., Wrathall-168)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests')
    parser.add_argument('--limit', type=int, default=50, help='Max profiles to process')
    args = parser.parse_args()

    print(f"WikiTree Wrathall Import - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    if args.profile:
        profiles = [args.profile]
    else:
        print("Fetching Wrathall profile list...")
        profiles = get_wrathall_profiles()
        print(f"Found {len(profiles)} profiles")

    profiles = profiles[:args.limit]

    for i, profile_id in enumerate(profiles, 1):
        print(f"\n[{i}/{len(profiles)}] Processing {profile_id}")

        html = fetch_wikitree_profile(profile_id)
        if html:
            data = parse_wikitree_profile(html, profile_id)
            if data['forename'] or data['surname']:
                save_to_db(data)
            else:
                print(f"  Could not parse name from profile")

        if i < len(profiles):
            time.sleep(args.delay)

    print("\n" + "=" * 60)
    print("Import complete")

if __name__ == '__main__':
    main()
