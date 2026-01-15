#!/usr/bin/env python3
"""
Interactive script to help add people to your Ancestry tree.

This script opens a browser where you're already logged in,
navigates to specific people, and helps you add children.

Usage:
    python scripts/add_to_ancestry_tree.py

The script will:
1. Open Ancestry in a browser using your Chrome cookies
2. Navigate to the 7th Earl of Lonsdale
3. Wait for you to manually add children
4. Provide guidance on what to add

Press Ctrl+C to stop at any time.
"""

import asyncio
import sys
from playwright.async_api import async_playwright
import browser_cookie3

TREE_ID = '208052350'

# People to add (children of James, 7th Earl)
PEOPLE_TO_ADD = [
    {
        'name': 'Lady Jane Helen Harbord Lowther',
        'birth_date': '13 Nov 1947',
        'sex': 'F',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Tuppina Cecily Bennet',
        'notes': 'First child of 7th Earl'
    },
    {
        'name': 'Lady Miranda Lowther',
        'birth_date': '1 Jul 1955',
        'sex': 'F',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Jennifer Lowther',
        'notes': 'Daughter from 2nd marriage'
    },
    {
        'name': 'Hon. William James Lowther',
        'birth_date': '9 Jul 1957',
        'sex': 'M',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Jennifer Lowther',
        'notes': 'CURRENT 9th EARL OF LONSDALE'
    },
    {
        'name': 'Lady Caroline Lowther',
        'birth_date': '11 Mar 1959',
        'sex': 'F',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Jennifer Lowther',
        'notes': 'Daughter from 2nd marriage'
    },
    {
        'name': 'Hon. James Nicholas Lowther',
        'birth_date': '4 Dec 1964',
        'sex': 'M',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Nancy Ruth Cobbs',
        'notes': 'Son from 3rd marriage'
    },
    {
        'name': 'Charles Alexander James Lowther',
        'birth_date': 'After 1975',
        'sex': 'M',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Caroline Sheila Ley',
        'notes': 'Son from 4th marriage'
    },
    {
        'name': 'Lady Marie-Louisa Kate Lowther',
        'birth_date': 'After 1975',
        'sex': 'F',
        'parent': 'James Hugh William Lowther, 7th Earl',
        'mother': 'Caroline Sheila Ley',
        'notes': 'Daughter from 4th marriage'
    },
]

RODNEY_TO_ADD = [
    {
        'name': 'Régine Elisabeth d\'Opdorp',
        'sex': 'F',
        'notes': 'Wife of John, 9th Baron Rodney (married 3 Nov 1951)'
    },
    {
        'name': 'George Brydges Rodney, 10th Baron',
        'birth_date': '3 Jan 1953',
        'death_date': '13 Feb 2011',
        'sex': 'M',
        'parent': 'John Francis Rodney, 9th Baron',
        'notes': '10th Baron Rodney'
    },
    {
        'name': 'Anne Rodney',
        'birth_date': '1955',
        'sex': 'F',
        'parent': 'John Francis Rodney, 9th Baron',
        'notes': 'Daughter of 9th Baron'
    },
    {
        'name': 'Jane Blakeney',
        'sex': 'F',
        'notes': 'Wife of George, 10th Baron Rodney (married 20 Aug 1996)'
    },
    {
        'name': 'John George Brydges Rodney, 11th Baron',
        'birth_date': '1999',
        'sex': 'M',
        'parent': 'George Brydges Rodney, 10th Baron',
        'notes': 'CURRENT 11th BARON RODNEY'
    },
]


def get_cookies():
    """Get Ancestry cookies from Chrome."""
    cookie_list = []
    for domain in ['.ancestry.co.uk', '.ancestry.com']:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for c in cookies:
                cookie_list.append({
                    'name': c.name,
                    'value': c.value,
                    'domain': c.domain,
                    'path': c.path or '/',
                })
        except Exception as e:
            print(f"Warning: Could not get cookies for {domain}: {e}")
    return cookie_list


async def main():
    print("=" * 60)
    print("ANCESTRY TREE HELPER")
    print("=" * 60)
    print(f"\nTree ID: {TREE_ID}")
    print("\nThis script will help you add missing descendants to your Lowther tree.")
    print("A browser window will open - please make sure Chrome is CLOSED first.\n")

    input("Press Enter to continue (or Ctrl+C to cancel)...")

    cookies = get_cookies()
    print(f"\nLoaded {len(cookies)} cookies from Chrome")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1400, 'height': 900}
        )

        await context.add_cookies(cookies)

        # Mask automation
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        # First, go to the tree
        print("\n=== Opening your Lowther tree ===")
        tree_url = f'https://www.ancestry.co.uk/family-tree/tree/{TREE_ID}'

        try:
            await page.goto(tree_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)

            title = await page.title()
            print(f"Page: {title}")

            if 'denied' in title.lower():
                print("\n⚠️  Access denied - try closing Chrome completely and running again")
                input("Press Enter to close...")
                await browser.close()
                return

            print("\n" + "=" * 60)
            print("PEOPLE TO ADD")
            print("=" * 60)

            print("\n📋 Children of James, 7th Earl of Lonsdale:")
            for i, person in enumerate(PEOPLE_TO_ADD, 1):
                print(f"\n  {i}. {person['name']}")
                print(f"     Birth: {person.get('birth_date', 'Unknown')}")
                print(f"     Mother: {person.get('mother', 'Unknown')}")
                if person.get('notes'):
                    print(f"     ⭐ {person['notes']}")

            print("\n📋 Rodney descendants to add:")
            for i, person in enumerate(RODNEY_TO_ADD, 1):
                print(f"\n  {i}. {person['name']}")
                if person.get('birth_date'):
                    print(f"     Birth: {person['birth_date']}")
                if person.get('notes'):
                    print(f"     ⭐ {person['notes']}")

            print("\n" + "=" * 60)
            print("INSTRUCTIONS")
            print("=" * 60)
            print("""
1. In the browser, search for 'James Hugh William Lowther'
2. Click on him to open his profile
3. Click 'Add' -> 'Add Child'
4. Enter the details from the list above
5. Repeat for each missing child

For Rodneys:
1. Search for 'John Francis Rodney'
2. Add his wife and children

The browser will stay open until you press Enter here.
            """)

            input("\nPress Enter when done to close the browser...")

        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to close...")

        await browser.close()

    print("\nDone! Remember to verify the additions in your tree.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
