#!/usr/bin/env python3
"""Fetch shared matches between two DNA testers."""

import sys
import json
import time
import re
import browser_cookie3
from playwright.sync_api import sync_playwright

MATCH_GUID = "07b9b403-0006-0000-0000-000000000000"  # Daisy
MY_GUID = "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A"

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
    cookies = get_cookies()
    if not cookies:
        print("No cookies found")
        return
    
    # URL for shared matches
    shared_url = f"https://www.ancestry.co.uk/discoveryui-matches/compare/{MY_GUID}/with/{MATCH_GUID}/sharedmatches"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()
        
        print(f"Fetching shared matches: {shared_url}")
        page.goto(shared_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        content = page.content()
        
        # Save for analysis
        with open('/tmp/daisy_shared.html', 'w') as f:
            f.write(content)
        
        body_text = page.inner_text('body')
        print("\n--- SHARED MATCHES PAGE ---")
        print(body_text[:3000])
        
        # Look for match names and cM values
        matches = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+|[a-z_]+\d*)\s*\n?\s*(\d+\.?\d*)\s*cM', body_text)
        if matches:
            print("\n--- EXTRACTED MATCHES ---")
            for name, cm in matches[:20]:
                print(f"  {name}: {cm} cM")
        
        browser.close()

if __name__ == "__main__":
    main()
