#!/usr/bin/env python3
"""Fetch shared matches between two DNA testers."""

import sys
import json
import time
import browser_cookie3
from playwright.sync_api import sync_playwright

PROFILE_URL = sys.argv[1] if len(sys.argv) > 1 else None

def get_cookies():
    cookie_list = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            for c in cookies:
                cookie_list.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path,
                    "secure": bool(c.secure),
                })
        except:
            pass
    return cookie_list

def main():
    if not PROFILE_URL:
        print("Usage: python fetch_shared_matches.py <profile_url>")
        return
    
    cookies = get_cookies()
    if not cookies:
        print("No cookies found")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()
        
        print(f"Fetching: {PROFILE_URL}")
        page.goto(PROFILE_URL, wait_until='networkidle', timeout=60000)
        time.sleep(2)
        
        # Get the page content
        content = page.content()
        
        # Try to find the person's name
        try:
            name_elem = page.query_selector('h1, .profile-name, [data-testid="profile-name"]')
            if name_elem:
                print(f"\nName: {name_elem.inner_text()}")
        except:
            pass
        
        # Look for shared cM info
        if 'cM' in content:
            import re
            cm_matches = re.findall(r'(\d+\.?\d*)\s*cM', content)
            if cm_matches:
                print(f"Shared cM found: {cm_matches}")
        
        # Look for relationship prediction
        if 'cousin' in content.lower() or 'sibling' in content.lower():
            import re
            rel_matches = re.findall(r'((?:\d+)?(?:st|nd|rd|th)?\s*cousin[^<]*|sibling[^<]*)', content, re.I)
            if rel_matches:
                print(f"Relationship: {rel_matches[:3]}")
        
        # Check for shared matches link/section
        shared_link = page.query_selector('a[href*="sharedmatches"], [data-testid*="shared"]')
        if shared_link:
            print(f"\nShared matches section found")
            try:
                shared_link.click()
                time.sleep(3)
                content = page.content()
            except:
                pass
        
        # Save full HTML for analysis
        with open('/tmp/daisy_profile.html', 'w') as f:
            f.write(content)
        print("\nSaved full HTML to /tmp/daisy_profile.html")
        
        # Extract any visible text about matches
        body_text = page.inner_text('body')
        print("\n--- PAGE TEXT (first 2000 chars) ---")
        print(body_text[:2000])
        
        browser.close()

if __name__ == "__main__":
    main()
