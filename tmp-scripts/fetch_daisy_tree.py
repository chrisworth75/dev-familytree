#!/usr/bin/env python3
"""Find and import Daisy Morphet's tree."""

import time
import re
import browser_cookie3
from playwright.sync_api import sync_playwright

MATCH_GUID = "07b9b403-0006-0000-0000-000000000000"
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
    
    # URL to see trees
    trees_url = f"https://www.ancestry.co.uk/discoveryui-matches/compare/{MY_GUID}/with/{MATCH_GUID}/trees"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()
        
        print(f"Fetching trees: {trees_url}")
        page.goto(trees_url, wait_until='networkidle', timeout=60000)
        time.sleep(2)
        
        content = page.content()
        
        # Find tree IDs
        tree_ids = list(set(re.findall(r'/family-tree/tree/(\d+)', content)))
        print(f"\nTree IDs found: {tree_ids}")
        
        body_text = page.inner_text('body')
        print("\n--- PAGE TEXT ---")
        print(body_text[:2000])
        
        browser.close()
        
        return tree_ids

if __name__ == "__main__":
    tree_ids = main()
    if tree_ids:
        print(f"\n\nTo import: python import_ancestry_tree.py {tree_ids[0]}")
