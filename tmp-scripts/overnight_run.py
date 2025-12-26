#!/usr/bin/env python3
"""
Overnight batch processing:
1. Import remaining DNA match trees
2. Discover tree IDs for more matches
3. Import those new trees
4. Fetch more shared matches
"""

import subprocess
import sys
import time
from datetime import datetime

VENV_PYTHON = "/Users/chris/dev-familytree/venv/bin/python"
WORK_DIR = "/Users/chris/dev-familytree"

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def run_script(script, args=[]):
    """Run a Python script and return success status."""
    cmd = [VENV_PYTHON, f"{WORK_DIR}/{script}"] + args
    log(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=WORK_DIR, timeout=7200)  # 2 hour timeout per script
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: {script}")
        return False
    except Exception as e:
        log(f"ERROR: {e}")
        return False

def main():
    log("=" * 60)
    log("OVERNIGHT BATCH PROCESSING STARTED")
    log("=" * 60)

    # Step 1: Import remaining DNA match trees
    log("\n>>> STEP 1: Import remaining DNA match trees")
    run_script("import_match_trees.py", ["--import-trees", "--min-cm", "20", "--max-tree-size", "2000", "--delay", "0.5"])

    time.sleep(10)

    # Step 2: Discover tree IDs for more matches (those without tree IDs)
    log("\n>>> STEP 2: Discover tree IDs for more DNA matches")
    run_script("import_match_trees.py", ["--discover", "--min-cm", "15", "--limit", "50", "--delay", "0.5"])

    time.sleep(10)

    # Step 3: Import newly discovered trees
    log("\n>>> STEP 3: Import newly discovered trees")
    run_script("import_match_trees.py", ["--import-trees", "--min-cm", "15", "--max-tree-size", "2000", "--delay", "0.5"])

    time.sleep(10)

    # Step 4: Fetch more shared matches
    log("\n>>> STEP 4: Fetch shared matches for matches >= 20 cM")
    run_script("import_shared_matches.py", ["--min-cm", "20", "--min-new", "10", "--delay", "0.8"])

    log("\n" + "=" * 60)
    log("OVERNIGHT BATCH PROCESSING COMPLETE")
    log("=" * 60)

    # Show final stats
    log("\nFinal statistics:")
    run_script("import_shared_matches.py", ["--stats"])

if __name__ == "__main__":
    main()
