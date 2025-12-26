# Genealogy Research Database

A comprehensive SQLite-based system for genealogy research, focusing on DNA match analysis and ancestor discovery.

## Project Goals

1. **Build a comprehensive database** - Accumulate as much information about ancestors as possible from multiple sources
2. **Import DNA matches from Ancestry** - Either via API or browser scraping (Playwright)
3. **Import family trees from matches** - To find common ancestors
4. **Track evidence for and against** - Family stories/claims need to be proven or disproven with evidence
5. **Continuous updates** - Pull new DNA matches as they appear on Ancestry

**Important**: This is an ongoing research project. We don't jump to conclusions - we gather evidence and let it speak for itself.

## Current Research Questions

### Lowther/Wrathall Connection (Unproven)
- **Claim**: Susan Wrathall (1842-1925) had a relationship with a member of the Lowther family (Earls of Lonsdale), resulting in Henry Lonsdale Wrathall (1863-1927)
- **Source of claim**: wrathall.org (a Wrathall family member's research)
- **Status**: UNPROVEN - gathering DNA and documentary evidence for/against
- **Evidence for**: The middle name "Lonsdale" (the Earl's title); family tradition
- **Evidence needed**: DNA matches with confirmed Lowther descendants; documentary records

## Scripts

All production scripts are in the `scripts/` directory. Experimental scripts are in `tmp-scripts/`.

### Daily Use Scripts (scripts/)

#### DNA Match Import (`scripts/ancestry_import.py`)
Imports DNA matches from Ancestry.com using browser automation.

```bash
# IMPORTANT: Close Chrome first! (cookies can't be read while browser is open)

# Browser mode - scrapes ALL matches
python scripts/ancestry_import.py --browser

# Headless mode (invisible browser)
python scripts/ancestry_import.py --browser --headless

# API mode - limited to ~200 matches
python scripts/ancestry_import.py

# Get shared matches for a specific person
python scripts/ancestry_import.py --shared "Rachel Wrathall"
```

#### Tree Import (`scripts/import_ancestry_tree.py`)
Imports a complete Ancestry tree with people AND relationships.

```bash
# Import a tree (with rate limiting)
python scripts/import_ancestry_tree.py TREE_ID --delay 0.3

# Limit size
python scripts/import_ancestry_tree.py TREE_ID --max-size 2000

# Show stats only
python scripts/import_ancestry_tree.py TREE_ID --stats
```

#### Shared Match Import (`scripts/import_shared_matches.py`)
Imports shared match data to find triangulation groups.

```bash
python scripts/import_shared_matches.py --min-cm 30 --delay 0.5
```

#### Tree ID Discovery (`scripts/import_match_trees.py`)
Discovers and imports trees from DNA matches.

```bash
# Discover tree IDs for matches
python scripts/import_match_trees.py --discover --min-cm 15 --limit 50

# Import discovered trees
python scripts/import_match_trees.py --import-trees --min-cm 20 --max-tree-size 2000
```

### Experimental Scripts (tmp-scripts/)
- `explore_tree_api.py` - API exploration
- `fetch_daisy_tree.py` - One-off tree fetch
- `fetch_shared_matches.py` - Early shared match experiments
- `import_wrathall_cluster.py` - Cluster import experiment
- `migrate_ahnentafel.py` - Ahnentafel migration
- `overnight_run.py` - Batch processing script

## Database Schema

### Core Tables

- **person** - Known ancestors with estimated details
- **relationship** - Parent/child/spouse links between people
- **tree** - Imported Ancestry trees
- **dna_match** - DNA matches from Ancestry
- **shared_match** - Shared matches between two DNA matches
- **census_record** - UK census transcriptions (1841-1911)
- **person_census_link** - Links people to census records with confidence scores

### Research Tables

- **ancestor** - Ahnentafel-numbered ancestors (1=self, 2=father, 3=mother, etc.)
- **cluster** - DNA match clusters for grouping related matches
- **match_ancestor** - Links DNA matches to known ancestors

## Quick Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Database location
sqlite3 genealogy.db

# Key queries
# List DNA matches by cM
SELECT name, shared_cm, match_side FROM dna_match ORDER BY shared_cm DESC LIMIT 20;

# Count matches per side
SELECT match_side, COUNT(*) FROM dna_match GROUP BY match_side;

# Find imported trees
SELECT id, ancestry_tree_id, name, (SELECT COUNT(*) FROM person WHERE tree_id = t.id) as people
FROM tree t ORDER BY people DESC;
```

## Important Notes for Future Sessions

1. **ALWAYS save working scripts** - Don't modify working code without a backup
2. **Document what works** - Write notes after each successful operation
3. **Note CSS selectors** - Ancestry's HTML structure changes; document working selectors
4. **Keep daily notes** - NOTES_YYYY-MM-DD.md files track progress and findings
5. **Don't assume claims are true** - The Lowther claim is a research question, not a fact

## Dependencies

```bash
pip install browser_cookie3 requests playwright
playwright install chromium
```

## Files Structure

```
dev-familytree/
├── README.md                 # This file
├── CLAUDE.md                 # Instructions for AI assistant
├── genealogy.db              # SQLite database (~30MB)
├── requirements.txt          # Python dependencies
├── migrations/               # Database schema migrations
├── NOTES_*.md                # Daily research notes
├── scripts/                  # Production scripts
│   ├── ancestry_import.py    # DNA match import
│   ├── import_ancestry_tree.py
│   ├── import_shared_matches.py
│   └── import_match_trees.py
├── tmp-scripts/              # Experimental/one-off scripts
└── venv/                     # Python virtual environment
```

## Current Status (Dec 26, 2025)

- **DNA Matches**: 2,038 in database
- **People**: ~12,000+ across imported trees
- **Trees**: 40+ imported
- **Shared Matches**: ~5,000 records

### Recent Fixes (Dec 26, 2025)
- DNA match browser scraping **FIXED** - now uses pagination instead of scrolling
- Key selectors documented in NOTES_2025-12-26.md

---

*Last updated: December 26, 2025*
