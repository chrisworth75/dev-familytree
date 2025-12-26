#!/usr/bin/env python3
"""
Explore Ancestry Tree API endpoints to find family relationship data.
"""

import requests
import browser_cookie3
import json
import re

TREE_ID = "18571258"  # The one with both Lowthers and Wrathalls
BASE_URL = "https://www.ancestry.co.uk"

def get_cookies():
    """Get ancestry cookies from Chrome."""
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for cookie in cookies:
                cookie_list.append(cookie)
        except:
            pass
    return cookie_list

def make_session():
    """Create authenticated session."""
    session = requests.Session()
    cookies = get_cookies()
    for c in cookies:
        session.cookies.set(c.name, c.value, domain=c.domain)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/html",
    })
    return session

def check_download_page(session, tree_id):
    """Check the settings/download page for GEDCOM export."""
    print("\n" + "=" * 60)
    print("Checking GEDCOM download page...")
    print("=" * 60)

    url = f"{BASE_URL}/family-tree/tree/{tree_id}/settings/download"
    resp = session.get(url, timeout=30)
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        html = resp.text

        # Look for download links
        gedcom_patterns = [
            r'href="([^"]*gedcom[^"]*)"',
            r'href="([^"]*download[^"]*)"',
            r'href="([^"]*export[^"]*)"',
            r'action="([^"]*)"',
            r'data-url="([^"]*)"',
        ]

        print("\nSearching for download links...")
        for pattern in gedcom_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for m in matches[:5]:
                print(f"  Found: {m}")

        # Save HTML for inspection
        with open("/tmp/ancestry_download_page.html", "w") as f:
            f.write(html)
        print("\nSaved HTML to /tmp/ancestry_download_page.html")

def try_person_page(session, tree_id):
    """Get a person page and look for family member IDs."""
    print("\n" + "=" * 60)
    print("Trying person page for family structure...")
    print("=" * 60)

    # Get a person
    persons = session.get(f"{BASE_URL}/api/treesui-list/trees/{tree_id}/persons").json()
    if not persons:
        return

    gid = persons[0].get('gid', {}).get('v', '').split(':')[0]
    name_data = persons[0].get('Names', [{}])[0]
    name = f"{name_data.get('g', '')} {name_data.get('s', '')}"
    print(f"Checking person: {name} (ID: {gid})")

    # Get the person page HTML
    person_url = f"{BASE_URL}/family-tree/person/tree/{tree_id}/person/{gid}"
    print(f"URL: {person_url}")
    resp = session.get(person_url, timeout=30)
    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        html = resp.text

        # Look for family member data
        patterns = [
            r'"father":\s*{[^}]+}',
            r'"mother":\s*{[^}]+}',
            r'"spouse":\s*{[^}]+}',
            r'"children":\s*\[[^\]]+\]',
            r'"parents":\s*\[[^\]]+\]',
            r'"familyMembers":\s*{[^}]+}',
            r'fatherId["\']:\s*["\']([^"\']+)',
            r'motherId["\']:\s*["\']([^"\']+)',
            r'spouseId["\']:\s*["\']([^"\']+)',
        ]

        print("\nSearching for family data in HTML...")
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for m in matches[:3]:
                print(f"  Found: {m[:100]}...")

        # Look for embedded JSON data
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.PT_INITIAL_DATA\s*=\s*({.+?});',
            r'data-person-json=["\']([^"\']+)',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for m in matches[:1]:
                try:
                    # Try to parse as JSON
                    if m.startswith('{'):
                        data = json.loads(m)
                        print(f"\n  Found embedded JSON with keys: {list(data.keys())[:10]}")
                        # Look for family data
                        def find_family_keys(obj, prefix=''):
                            if isinstance(obj, dict):
                                for k, v in obj.items():
                                    if any(x in k.lower() for x in ['parent', 'father', 'mother', 'spouse', 'child', 'family']):
                                        print(f"    {prefix}{k}: {str(v)[:100]}")
                                    if isinstance(v, (dict, list)):
                                        find_family_keys(v, prefix + k + '.')
                            elif isinstance(obj, list) and obj:
                                find_family_keys(obj[0], prefix + '[0].')
                        find_family_keys(data)
                except:
                    pass

        # Save for inspection
        with open("/tmp/ancestry_person_page.html", "w") as f:
            f.write(html)
        print("\nSaved HTML to /tmp/ancestry_person_page.html")

def try_pedigree_api(session, tree_id):
    """Try PT (Pedigree Tree) endpoints."""
    print("\n" + "=" * 60)
    print("Trying PT (Pedigree Tree) endpoints...")
    print("=" * 60)

    # Get a person
    persons = session.get(f"{BASE_URL}/api/treesui-list/trees/{tree_id}/persons").json()
    if not persons:
        return

    gid = persons[0].get('gid', {}).get('v', '')

    # PT endpoints often use full GID
    endpoints = [
        f"/pt/Api/Get/{tree_id}/null/{gid}",
        f"/pt/api/tree/{tree_id}/person/{gid}",
        f"/pt/proxy/tree/{tree_id}/family/{gid}",
        f"/pt/tree/{tree_id}/person/{gid}/family",
        f"/pt/api/FamilyView/{tree_id}?personId={gid}",
    ]

    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                print(f"\n✓ {ep}")
                try:
                    data = r.json()
                    print(f"  Keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    print(f"  Sample: {str(data)[:300]}")
                except:
                    print(f"  (not JSON, {len(r.text)} chars)")
                    # Check if HTML contains family data
                    if 'father' in r.text.lower() or 'mother' in r.text.lower():
                        print("  HTML contains family references!")
            elif r.status_code != 404:
                print(f"  {ep}: {r.status_code}")
        except Exception as e:
            pass

def try_gedcomx_endpoint(session, tree_id):
    """Try GEDCOM-X style endpoints."""
    print("\n" + "=" * 60)
    print("Trying GEDCOM-X style endpoints...")
    print("=" * 60)

    endpoints = [
        f"/api/trees/{tree_id}?format=gedcomx",
        f"/api/tree/{tree_id}/gedcomx",
        f"/gedcomx/tree/{tree_id}",
        f"/api/treesui-list/trees/{tree_id}/families",
        f"/api/treesui-list/trees/{tree_id}/relationships",
    ]

    session.headers['Accept'] = 'application/x-gedcomx-v1+json, application/json'

    for ep in endpoints:
        url = f"{BASE_URL}{ep}"
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                print(f"\n✓ {ep}")
                try:
                    data = r.json()
                    print(f"  Type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())}")
                except:
                    pass
            elif r.status_code != 404:
                print(f"  {ep}: {r.status_code}")
        except:
            pass

if __name__ == "__main__":
    print("Close Chrome if open, then press Enter...")
    input()

    session = make_session()
    try_person_page(session, TREE_ID)
    try_pedigree_api(session, TREE_ID)
    try_gedcomx_endpoint(session, TREE_ID)
    check_download_page(session, TREE_ID)
