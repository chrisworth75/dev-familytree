#!/usr/bin/env python3
"""Import trees from Wrathall cluster matches."""

import sqlite3
import subprocess
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "genealogy.db"
VENV_PYTHON = "/Users/chris/dev-familytree/venv/bin/python"

SKIP_TREE_IDS = ['17813289']  # Trees known to be too large

def get_wrathall_cluster_matches():
    """Find matches in the Wrathall cluster with trees to import."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find matches who share DNA with known Wrathall-connected matches
    cursor.execute("""
        SELECT DISTINCT dm.id, dm.name, dm.shared_cm, dm.tree_size, dm.linked_tree_id, dm.ancestry_id
        FROM dna_match dm
        LEFT JOIN tree t ON t.ancestry_tree_id = dm.linked_tree_id
        WHERE dm.has_tree = 1
        AND t.id IS NULL
        AND dm.name IN (
            SELECT DISTINCT sm.match2_name
            FROM shared_match sm
            JOIN dna_match dm2 ON dm2.id = sm.match1_id
            WHERE dm2.name IN ('Rachel Wrathall', 'hugh copland', 'Bruce Lightfoot',
                              'Rebecca Hyndman', 'Toby Yates', 'Bruce Horrocks',
                              'Neil Farnworth', 'hazelhersant', 'Emily Hine')
        )
        ORDER BY dm.shared_cm DESC
    """)
    
    matches = cursor.fetchall()
    conn.close()
    return matches

def discover_tree_id(match_guid):
    """Discover tree ID for a match using Playwright."""
    import browser_cookie3
    from playwright.sync_api import sync_playwright
    import re
    
    MY_GUID = "E756DE6C-0C8D-443B-8793-ADDB6F35FD6A"
    
    cookies = []
    for domain in [".ancestry.co.uk", ".ancestry.com"]:
        try:
            for c in browser_cookie3.chrome(domain_name=domain):
                cookies.append({
                    "name": c.name, "value": c.value, "domain": c.domain,
                    "path": c.path, "secure": bool(c.secure)
                })
        except:
            pass
    
    if not cookies:
        return None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0")
        context.add_cookies(cookies)
        page = context.new_page()
        
        url = f"https://www.ancestry.co.uk/discoveryui-matches/compare/{MY_GUID}/with/{match_guid}/trees"
        try:
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(1)
            content = page.content()
            tree_ids = list(set(re.findall(r'/family-tree/tree/(\d+)', content)))
            browser.close()
            return tree_ids[0] if tree_ids else None
        except:
            browser.close()
            return None

def import_tree(tree_id, delay=0.5, max_size=3000):
    """Import a tree with size limit."""
    cmd = [VENV_PYTHON, "import_ancestry_tree.py", str(tree_id), "--delay", str(delay), "--max-size", str(max_size)]
    subprocess.run(cmd, cwd=str(Path(__file__).parent))

def update_linked_tree_id(match_id, tree_id):
    """Update match with discovered tree ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE dna_match SET linked_tree_id = ? WHERE id = ?", (tree_id, match_id))
    conn.commit()
    conn.close()

def main():
    print("=" * 60)
    print("IMPORTING WRATHALL CLUSTER TREES")
    print("=" * 60)
    
    matches = get_wrathall_cluster_matches()
    print(f"Found {len(matches)} Wrathall cluster matches with trees")
    
    imported = 0
    for match_id, name, cm, tree_size, tree_id, ancestry_id in matches:
        if tree_size and tree_size > 2000:
            print(f"\nSkipping {name} - tree too large ({tree_size})")
            continue
            
        print(f"\n>>> {name} ({cm:.1f} cM, tree size: {tree_size})")
        
        # Discover tree ID if needed
        if not tree_id and ancestry_id:
            print(f"  Discovering tree ID...", end='', flush=True)
            tree_id = discover_tree_id(ancestry_id)
            if tree_id:
                print(f" found: {tree_id}")
                update_linked_tree_id(match_id, tree_id)
            else:
                print(" not found")
                continue
        
        if tree_id:
            if str(tree_id) in SKIP_TREE_IDS:
                print(f"  Skipping tree {tree_id} (known to be too large)")
                continue
            print(f"  Importing tree {tree_id}...")
            import_tree(tree_id)
            imported += 1
        
        time.sleep(1)
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETE: Imported {imported} trees")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
