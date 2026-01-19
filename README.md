# Genealogy Research Database

## About This Project

**Researcher:** Chris Worthington

All research in this database is geared towards building Chris Worthington's family tree and identifying unknown ancestors, particularly Henry Lonsdale Wrathall's father.

### My Trees in Database

| Tree ID | Ancestry ID | Name | People | Purpose |
|---------|-------------|------|-------:|---------|
| 1 | - | My Tree | 452 | Primary local tree for research |
| 125 | 193991232 | Main Ancestry Tree | 484 | Main family tree on Ancestry |
| 169 | 208052350 | Lowther Research Tree | 632 | Separate tree for Lowther family research (68 Lowthers) |

**Note on Tree 169 (Lowther Research Tree):** This is a dedicated tree for researching the Lowther family to identify potential DNA matches. It contains 68 Lowther family members with documented lineages. This tree exists to help identify confirmed Lowther descendants who could provide proof via DNA triangulation - NOT to assume any connection to our tree.

---

---

## ⚠️ IMPORTANT: The Lowther Claim is UNPROVEN

There is a family tradition that Henry Lonsdale Wrathall's father was a member of the Lowther family (Earls of Lonsdale). **THIS IS UNPROVEN SPECULATION.**

**Source of the claim:** A family memoir at [wrathall.org](https://wrathall.org/wrathall/james/australia/lonsdalewrathall.html)

**Critical warnings:**
- The memoir is family tradition, NOT documentary evidence
- **DO NOT trust ThruLines suggestions** that show Lowther connections - these come from speculative Wrathall family trees (including possibly our own), creating circular reasoning
- The only "evidence" is the middle name "Lonsdale" and oral tradition
- We need DNA matches with CONFIRMED Lowther descendants to prove/disprove this
- Any Lowther data imported from ThruLines has been REMOVED from this database

**What would constitute proof:**
1. DNA triangulation with documented Lowther descendants who have verified paper trails
2. Documentary evidence (parish records, letters, etc.) linking Susan Wrathall to the Lowther family
3. Y-DNA testing matching the Lowther male line

Until such evidence is found, **position 36 (HLW's father) remains UNKNOWN**.

---

## Research Missions

### Mission 1: Identify Henry Lonsdale Wrathall's Father
Henry Lonsdale Wrathall (1863-1927) was born to Susan Wrathall in Blackburn, Lancashire. His father is unknown (Ahnentafel position 36). This project uses DNA evidence to systematically gather data that may reveal his identity.

**We do not assume any conclusion.** The "Lonsdale" middle name and family tradition suggest a possible connection to the Lowther family (Earls of Lonsdale), but this is a hypothesis to test with DNA evidence, not a fact to accept.

### Mission 2: Identify How I Am Related to My Top 50 Matches
For each of the top 50 DNA matches (by cM), determine the exact relationship by:
1. Building a research tree for each match (regardless of whether they have a public tree)
2. Tracing their ancestry until it intersects with our known tree
3. Documenting the MRCA (Most Recent Common Ancestors)

**Progress is tracked in the Top 50 Match Table below.** This table is derived from the `dna_match` database table but includes additional tracking columns.

### Mission 3: Prove a Family Link to the Cricketer Harry Wrathall
Harry Wrathall (1857-1930) was a professional cricketer from Kirkby Lonsdale/Lowther area. Is there a documented family connection?

### Mission 4: Prove or Disprove a Family Link to WG Grace
W.G. Grace (1848-1915) was the famous Victorian cricketer from Bristol/Gloucestershire. Is there any family connection through DNA or documentary evidence?

**Current Status: LIKELY CONNECTION FOUND**

Our family tree (Tree 110 / Rebecca Hyndman's tree) includes W.G. Grace, suggesting a researched connection exists. The link is through:

- **Marjorie Grace Goodall** (1920) - Chris's grandmother, middle name "Grace" from her paternal grandmother
- **William Cheetham Goodall** (1878) - Marjorie's father
- **Emma Grace** - William's mother, Chris's great-great-grandmother

Tree 125 (193991232) contains detailed Grace family data including:
- Henry Mills Grace (1808) - W.G. Grace's father
- William Gilbert "W.G." Grace (1848) - the famous cricketer
- Graham Grace (1849) - W.G. Grace's brother
- Blanch Maud Grace (1864) - W.G. Grace's daughter

**Next Steps:**
1. Determine Emma Grace's exact relationship to W.G. Grace (sister? cousin? same branch?)
2. Find Emma Grace's parents to confirm the connection
3. Document the complete lineage from Emma Grace to Henry Mills Grace

**Bristol Connection:** User's aunt reports "GW Grace went to Bristol" (W.G. Grace was from Bristol/Gloucestershire) and "Marjorie's uncle George lived in Clevedon Bristol" (Clevedon is in Somerset, near Bristol). This geographic connection supports the family link.

### Mission 5: Determine How Toby Yates Connects to the Maternal Side
Toby Yates is a close DNA match. How does he connect through the maternal line?

### Mission 6: Find All Descendants of Ancestors up to HLW's Level
Build a comprehensive descendant tree for ancestors at Henry Lonsdale Wrathall's generation and above (Ahnentafel 36+).

### Mission 7: Build a Family Website
Create a minimal viable product website where descendants of HLW can:
- Login securely
- View the family tree
- Query the database
- Download tree data (GEDCOM)

**Status: MVP COMPLETE** (January 2026)

The `family-tree-app/` contains a working Spring Boot application with:
- [x] Secure login (Spring Security form authentication)
- [x] Per-user access control (configured in YAML)
- [x] View family trees (interactive D3.js timeline visualization)
- [x] Click person cards to view details + census records in sidebar
- [ ] Query the database (future)
- [ ] Download GEDCOM (future)

**Interactive D3.js Tree Features:**
- Timeline layout: X position = birth year, card width = lifespan
- Zoom and pan with mouse/trackpad
- Collapsible nodes (click +/- or shift+click)
- Animated transitions
- Click person to open detail sidebar with census records

Run with: `cd family-tree-app && mvn spring-boot:run` → http://localhost:3500

### Mission 8: Automate Free Census Website Searches
Create scripts to systematically search free UK genealogy websites for ancestor and descendant records, reducing dependence on paid Ancestry subscriptions.

**Status: IN PROGRESS**

#### Free UK Genealogy Resources

| Site | URL | Records | Access | Notes |
|------|-----|---------|--------|-------|
| **FreeCEN** | freecen.org.uk | Census 1841-1901 | Free, no CAPTCHA | ~52M records, partial coverage |
| **FamilySearch** | familysearch.org | Census, BMD, parish | Free (account required) | Largest free collection |
| **FreeBMD** | freebmd.org.uk | Birth/Marriage/Death indexes 1837-1983 | Free | Links to GRO references |
| **UKBMD** | ukbmd.org.uk | Regional BMD office links | Free | Portal to local registrars |
| **GRO** | gro.gov.uk/gro/content/certificates | BMD indexes | Free index, paid certificates | Official government records |
| **1939 Register** | findmypast.co.uk | 1939 census substitute | Free index, paid images | Via FindMyPast |
| **ScotlandsPeople** | scotlandspeople.gov.uk | Scottish records | Free index, paid images | Census, BMD, wills |
| **GENUKI** | genuki.org.uk | County guides & links | Free | Encyclopedia of UK genealogy |

#### Scripts

| Script | Status | Description |
|--------|--------|-------------|
| `search_freecen.py` | ✅ Working | Search FreeCEN by surname/forename/year |
| `batch_freecen_search.py` | ✅ Working | Batch search for all people with a surname |
| `search_familysearch.py` | ✅ Working | Search FamilySearch census records (1841-1911) |
| `search_freebmd.py` | ✅ Working | Search FreeBMD for BMD index entries |
| `census_crawler.py` | ✅ Working | Master script - searches all free sites for a person |

#### Goals

1. **Automated census search**: For each person in the database born 1835-1905, search all free census sites
2. **Match and link**: Automatically match results to database records using confidence scoring
3. **Fill gaps**: Identify people missing from expected censuses (death? emigration? institution?)
4. **Reduce costs**: Minimize need for Ancestry/FindMyPast subscriptions for basic census data

#### Usage

```bash
# Search FreeCEN for a surname (working now)
python scripts/search_freecen.py --surname Wrathall --forename Henry --birth-year 1863

# Batch search for all Virgos in My Tree
python scripts/batch_freecen_search.py --surname Virgo --tree-id 1 --store
```

---

## Approach: Daily Automated Data Collection

**This project is NOT about contacting people.** It is about establishing a daily routine for automated data collection that will accumulate evidence over time.

### The Strategy
1. **Import new DNA matches daily** - Ancestry adds new matches regularly
2. **Import shared match data** - Build triangulation networks
3. **Import match trees** - Gather surname and location data
4. **Analyse patterns** - Look for Westmorland/Cumberland connections
5. **Repeat** - Consistency over time builds the dataset

### Why This Works
- DNA matches increase as more people test
- Each new tree import adds potential evidence
- Triangulation data reveals which matches share ancestors
- Over months, patterns emerge that single sessions miss

---

## Daily Routine

### Quick Daily Run (5-10 minutes)
```bash
cd /Users/chris/dev-familytree
source venv/bin/activate

# 1. Import any new DNA matches
python scripts/ancestry_import.py --browser --headless --limit 500

# 2. Import shared matches for recent imports
python scripts/import_shared_matches.py --min-cm 20 --delay 0.5

# 3. Discover and import new trees (max 500 people per tree)
# NOTE: We are ignoring trees >500 people completely for now.
# These large trees take too long to import and often contain noise.
# Focus on smaller, more targeted trees first.
python scripts/import_match_trees.py --discover --min-cm 20 --delay 0.3
python scripts/import_match_trees.py --import-trees --max-tree-size 500

# 4. Import ThruLines data (ancestors and MRCA mappings)
python scripts/import_thrulines.py

# 5. Run analysis
python scripts/find_unknown_father_matches.py
```

### Overnight/Extended Runs
```bash
# Import shared matches for lower cM threshold (takes hours)
python scripts/import_shared_matches.py --min-cm 15 --delay 0.5

# Import larger trees (takes hours)
python scripts/import_match_trees.py --import-trees --max-tree-size 2000
```

### Check Progress
```bash
sqlite3 genealogy.db "
SELECT 'DNA matches' as metric, COUNT(*) as count FROM dna_match
UNION ALL SELECT 'Shared match records', COUNT(*) FROM shared_match
UNION ALL SELECT 'Trees imported', COUNT(*) FROM tree
UNION ALL SELECT 'People in trees', COUNT(*) FROM person;
"
```

---

## Current Data (19 January 2026)

| Metric | Count |
|--------|-------|
| DNA matches | 9,985 |
| Shared match records | 14,468 |
| Trees imported | 435 |
| People in trees | 68,078 |
| People in My Tree (#1) | 452 |
| Matches assigned to clusters | 30 |
| Clusters with matches | 9 |

---

## Top 50 Match Table (Mission 2)

This table tracks progress on Mission 2: identifying how each top match connects to our tree.

**Key:**
- **Public Tree**: Size of match's public Ancestry tree (0 = none/private)
- **Identified**: Yes = connection proven, Partial = likely but unproven, No = unknown
- **MRCA**: Most Recent Common Ancestors (if identified)
- **Research Tree**: Our research tree ID for this match (built regardless of public tree)

> **Note:** This table is derived from the `dna_match` database table but maintained manually here with additional tracking columns. The database is the source of truth for cM values; this table tracks our research progress.

### MRCA Reference

| Gen | MRCA | Friendly Name | Typical cM |
|-----|------|---------------|------------|
| 1 | 2+3 | Jon+Pat | 2500+ (sibling) |
| 2 | 4+5 | Gord+Marj | 400-900 (1st cousin) |
| 2 | 6+7 | Albert+Doris | 400-900 (1st cousin) |
| 3 | 8+9 | Arthur+Connie | 100-300 (2nd cousin) |
| 3 | 10+11 | Goodalls | 100-300 |
| 3 | 12+13 | John+Betsy | 100-300 |
| 3 | 14+15 | Sam+Thea | 100-300 |
| 4 | 16+17 | Worthingtons | 40-100 (3rd cousin) |
| 4 | 18+19 | Henry+Mary | 40-100 |
| 4 | 22+23 | Virgos | 40-100 |
| 4 | 30+31 | Tarts | 40-100 |
| 5 | **UNK-PAT** | **Unknown Paternal** | 20-50 (4th cousin) |

**Note on UNK-PAT:** Susan Wrathall had only one child (Henry) with the unknown father. Matches in this cluster share DNA through the unknown father's OTHER family - his parents, siblings, or children from another relationship.

### Top 50 Matches

| # | Match | cM | Shared | Public Tree | Identified | MRCA | Research Tree |
|--:|-------|---:|-------:|------------:|:----------:|------|:-------------:|
| 1 | Rebecca Hyndman | 2699 | 35 | 241 | Yes | 2+3 (Jon+Pat) | - |
| 2 | Bruce Horrocks | 605 | 30 | 18 | Yes | 4+5 (Gord+Marj) | - |
| 3 | Toby Yates | 466 | 30 | 0 | Yes | 26+27 (Parker/Thompson) | - |
| 4 | Emily Hine | 134 | 30 | 84 | Yes | 22+23 (Virgos) | 113 |
| 5 | jane_gessler | 125 | 27 | 88 | Yes | Heywood (maternal) | 114 |
| 6 | Bruce Lightfoot | 118 | 29 | 4107 | Yes | 8-15 (Wrathall) | 115 |
| 7 | Helen Brammer | 112 | 24 | 0 | **✓** | 19 (Mary Alice Metcalfe) | - |
| 8 | Brenda Davey | 100 | 15 | 32 | Yes | **UNK-PAT** | 116 |
| 9 | Neil Farnworth | 90 | 28 | 9 | Yes | 30+31 (Tarts) | - |
| 10 | Angela Ganley | 70 | 24 | 70 | Partial | **UNK-PAT?** | 118 |
| 11 | hazelhersant | 58 | 25 | 2713 | **✓** | 22+23 (Virgo/Brown) | - |
| 12 | Margaret Wagstaff | 53 | 15 | 0 | **✓** | 26+27 (Parker/Thompson) | - |
| 13 | Ethel Hull | 51 | 11 | 32 | Yes | **UNK-PAT** | 120 |
| 14 | Michelle Morris | 49 | 20 | 0 | Yes | 18+19 (Wrathall) | - |
| 15 | geri_wood | 48 | 28 | 675 | Yes | 24+25 (Wood) | 121 |
| 16 | diane_lovick | 48 | 7 | 0 | **✓** | 30+31 (TART/Emily) | - |
| 17 | Valerie Simpson | 45 | 26 | 4 | Yes | **UNK-PAT** | 122 |
| 18 | Wendy Freeman | 44 | 28 | 0 | Yes | 18+19 (Wrathall) | - |
| 19 | Thelma Howard | 43 | 25 | 0 | Yes | 16+17 (Worthingtons) | 451 |
| 20 | Kim Parker | 43 | 21 | 0 | Yes | 18+19 (Wrathall) | - |
| 21 | hugh copland | 43 | 21 | 96 | **✓** | 19 (Mary Alice Metcalfe) | 304 |
| 22 | Kate Ellis | 42 | 13 | 1 | Yes | 16+17 (Worthingtons) | - |
| 23 | Georgina Burton-Roberts | 41 | 20 | 0 | Yes | 18+19 (Wrathall) | - |
| 24 | RuthieStennett | 40 | 26 | 0 | Yes | 16+17 (Worthingtons) | - |
| 25 | Emily Evans | 39 | 15 | 0 | Partial | **UNK-PAT** | TODO |
| 26 | Katrina Barnes | 39 | 8 | 0 | Partial | **UNK-PAT** | TODO |
| 27 | Joseph James | 38 | 25 | 697 | Yes | 32-35 (Worthingtons) | - |
| 28 | Rachel Wrathall | 38 | 22 | 257 | **✓** | 19 (Mary Alice Metcalfe) | 305 |
| 29 | Jill Lester | 37 | 24 | 2020 | Yes | **UNK-PAT** | 128 |
| 30 | Caroline James | 37 | 24 | 0 | Partial | 32-35 (Worthingtons?) | TODO |
| 31 | Paul Crook | 36 | 26 | 0 | Partial | 32-63 | TODO |
| 32 | Thomas Arnstein | 36 | 15 | 6 | Partial | **UNK-PAT** | TODO |
| 33 | diane rowles | 36 | 19 | 22 | Partial | 32-35 | TODO |
| 34 | Robert Greenhalgh | 35 | 11 | 17 | Partial | 32-63 | TODO |
| 35 | gstewart37 | 34 | 20 | 624 | **✓** | 30+31 (TART/Emily) | - |
| 36 | B.H. | 34 | 20 | 0 | Partial | 32-35 | TODO |
| 37 | Lynne Colley | 34 | 16 | 71 | Partial | 60+61 | TODO |
| 38 | Peter Ennor | 34 | 13 | 4 | Partial | **UNK-PAT** | TODO |
| 39 | Roger Meredith | 34 | 13 | 0 | Partial | 60+61 | TODO |
| 40 | Leo Taylor-Jannati | 34 | 13 | 0 | Partial | 32-63 | TODO |
| 41 | Joanne Harrison | 34 | 10 | 72 | Partial | **UNK-PAT** | TODO |
| 42 | Kathleen Macnab | 34 | 9 | 16 | Partial | 32-63 | TODO |
| 43 | karen_pelletier90 | 33 | 12 | 9 | Partial | 32-63 | TODO |
| 44 | Em Crooks | 33 | 20 | 0 | Partial | 32-35 | TODO |
| 45 | Regine Aichlmayr | 33 | 20 | 0 | Partial | 32-63 | TODO |
| 46 | Julie Stonehouse | 32 | 13 | 484 | Partial | 32-63 | - |
| 47 | Jed Wood | 32 | 16 | 675 | Yes | 32-47 (Wood) | 121 |
| 48 | SandyJoseph43 | 32 | 20 | 155 | Partial | 32-35 | TODO |
| 49 | Luke Rowles | 32 | 13 | 484 | Partial | 32-35 | - |
| 50 | Emma Alexander | 32 | 10 | 484 | Partial | 60+61 | - |

**Progress: 28/50 identified (56%), 19/50 partial (38%), 3/50 unknown (6%)**

**✓ = Confirmed via ThruLines**

### Notes on Identification Status

- **Yes**: Documentary proof exists (e.g., shared tree shows exact connection)
- **Partial**: Strong evidence but not conclusive (e.g., cluster membership, geographic patterns)
- **No**: Connection unknown, needs research
- **Unk-Pat?**: Likely connects through HLW's unknown father (Mission 1 target)
- **Shared tree**: Match shares tree 193991232 (main family tree) - connection likely but specific line unconfirmed

---

## Key Findings So Far

### Grace Family Connection (Mission 4)
Strong evidence of a connection to W.G. Grace's family:

| Person | Role | Birth Year | Tree |
|--------|------|------------|------|
| Emma Grace | Great-great-grandmother (paternal) | Unknown | 110 |
| William Cheetham Goodall | Great-grandfather | 1878 | 110, 119, 125 |
| Marjorie Grace Goodall | Grandmother | 1920 | 110, 119, 125 |
| W.G. Grace | Famous cricketer | 1848 | 110, 125 |
| Henry Mills Grace | W.G. Grace's father | 1808 | 125 |

The Grace family were from Bristol/Gloucestershire. Family oral history mentions "Marjorie's uncle George lived in Clevedon Bristol" (Clevedon is near Bristol), supporting the geographic connection.

**Goodall Family Structure (Tree 110):**
- William Anderson Goodall (1812) - earlier generation
- **William Goodall** + **Emma Grace** → parents of:
  - **William Cheetham Goodall** (1878) - Marjorie's father
  - **George Hay Goodall** - likely "Uncle George" who lived in Clevedon, Bristol
  - Norman Goodall
  - Martha Goodall

**Key Discovery (10 Jan 2026):** Emma Grace is **NOT** a sibling of W.G. Grace. Henry Mills Grace's 9 children were:
- Sons: Henry (1833), Alfred (1840), Edward Mills (1841), W.G. (1848), George Frederick (1850)
- Daughters: Anne (1835), Fanny (1839), Alice Rose (1845), Elizabeth Blanche (1847)

**No Emma among them.** Emma Grace must be from a different branch:
- Possibly a cousin (daughter of Henry Mills Grace's sibling)
- Possibly from an earlier generation
- Or from a different Grace family entirely

**Investigation needed:**
1. **Find Henry Mills Grace's siblings** - Did he have brothers/sisters whose children included Emma?
2. Find Emma Grace in 1851/1861 census as a child with her parents
3. Confirm George Hay Goodall lived in Clevedon, Somerset
4. Determine if/how the Bolton Graces connect to the Bristol Graces

**Sources:**
- [W.G. Grace WikiTree](https://www.wikitree.com/wiki/Grace-1086)
- [Grace family Wikipedia](https://en.wikipedia.org/wiki/Grace_family)

### Westmorland/Cumberland Candidates
Matches with connections to Lowther territory (but NO known family surnames):

| Match | cM | Location Connections |
|-------|-----|---------------------|
| Jill Lester | 38.0 | Great Strickland, Cumberland |
| Susan_Wilcock | 31.3 | Cumberland |
| Lisa Carter | 29.2 | Caldbeck, Cumberland |
| Kenneth Olsen | 28.1 | Witon, Cumberland |
| mkmanson40 | 25.9 | Kendal, Cockermouth |
| Geoffrey Carr | 25.8 | St Bees, Whitehaven |

### Potential Lead
**Geoffrey Carr** has "Lowther John Barrington" in their tree - a person with "Lowther" as a first/middle name, suggesting a naming connection to the Lowther family.

### The Problem
These Westmorland/Cumberland matches do NOT triangulate with each other, suggesting they connect through DIFFERENT ancestors rather than a single unknown father line.

---

## Scripts

| Script | Purpose | Daily Use |
|--------|---------|-----------|
| `ancestry_import.py` | Import DNA matches | Yes |
| `import_shared_matches.py` | Import triangulation data | Yes |
| `import_match_trees.py` | Discover/import match trees | Yes |
| `import_thrulines.py` | Scrape ThruLines for ancestors & MRCA mappings | Yes |
| `find_unknown_father_matches.py` | Analyse for unknown father | Yes |
| `cluster_matches.py` | Graph-based clustering | Weekly |
| `import_ancestry_tree.py` | Import single tree by ID | As needed |
| `import_census_from_tree.py` | Import census records for people in a tree | As needed |

---

## Database Schema

**Location:** `genealogy.db`

### Key Tables
| Table | Purpose |
|-------|---------|
| `dna_match` | DNA matches with cM, side, tree info |
| `shared_match` | Who shares DNA with whom (triangulation) |
| `tree` | Imported family trees |
| `person` | People from imported trees |
| `relationship` | Family relationships in trees |

### Tree Types

The database supports two types of trees to separate imported data from research expansions:

| Type | Purpose |
|------|---------|
| `imported` | Direct copy of a match's Ancestry tree - kept pristine for re-verification |
| `research` | Expanded tree with census records, BMD findings, and hypothetical connections |

**Why this matters:** When investigating a DNA match, we want to:
1. Keep their original tree unchanged (so we can re-import to check for updates)
2. Build out expanded research with census/BMD records in a separate tree
3. Track which findings came from the original tree vs our research

**Schema:**
```sql
-- tree table columns for this:
tree_type TEXT DEFAULT 'imported'   -- 'imported' or 'research'
source_tree_id INTEGER              -- links research tree to its source imported tree

-- person table:
source TEXT DEFAULT 'import'        -- 'import', 'census', 'bmd', 'research'
```

**Workflow:**
1. Import match's tree → stored as `tree_type='imported'`
2. Create research tree → `tree_type='research'`, `source_tree_id` points to original
3. Add people from census/BMD → `source='census'` or `source='bmd'`
4. Original tree remains unchanged for future re-imports

### Useful Queries
```sql
-- Find matches with Westmorland connections
SELECT dm.name, dm.shared_cm, p.birth_place
FROM dna_match dm
JOIN tree t ON t.ancestry_tree_id = dm.linked_tree_id
JOIN person p ON p.tree_id = t.id
WHERE p.birth_place LIKE '%Westmorland%';

-- Check triangulation between two matches
SELECT * FROM shared_match
WHERE match1_id = X AND match2_id = Y;

-- Find matches without imported trees
SELECT name, shared_cm FROM dna_match
WHERE has_tree = 1 AND linked_tree_id IS NULL
ORDER BY shared_cm DESC;

-- Find research trees and their sources
SELECT r.name as research_tree, i.name as source_tree
FROM tree r
JOIN tree i ON r.source_tree_id = i.id
WHERE r.tree_type = 'research';

-- Find people added from census records
SELECT p.name, p.birth_year_estimate, p.source, t.name as tree
FROM person p
JOIN tree t ON p.tree_id = t.id
WHERE p.source = 'census';
```

---

## Troubleshooting

### "Error fetching page 1: 403" during tree imports
Your Ancestry session cookies have expired. Fix:
1. Open Chrome and log into ancestry.co.uk
2. Retry the import script

### Ancestry tree sizes are inaccurate
Ancestry's reported tree size (visible in DNA match list) is often wildly wrong. A tree reported as having 100 people might actually have 3,000+. The `--max-tree-size` flag now aborts early during fetch if the actual size exceeds the limit.

### Tree size strategy (current policy)
**We are ignoring trees >500 people completely for now.** Rationale:
- Large trees (500+) take 10-30 minutes to import and often fail
- Many large trees contain distant/irrelevant branches
- Small focused trees are more likely to contain useful close-relative data
- We can revisit large trees later once all small trees are processed

---

## Research Principles

1. **Automated data collection** - Scripts do the work, not manual clicking
2. **Daily consistency** - Small daily imports beat occasional large sessions
3. **Evidence over assumption** - The Lonsdale hypothesis must be tested, not assumed
4. **No contact required** - All data comes from public trees and match lists
5. **Reproducible** - Scripts can be re-run to update/verify data

---

## What Would Prove the Connection

1. A triangulating group of matches whose trees ALL contain Lowther/Lonsdale surnames
2. Multiple matches with trees showing descent from confirmed Lowther family members
3. Y-DNA evidence linking to Lowther male line (separate test required)

---

## Project Structure

```
dev-familytree/
├── README.md                    # This file
├── CLAUDE.md                    # AI assistant instructions
├── ANALYSIS_REPORT.md           # Latest analysis report
├── genealogy.db                 # SQLite database
├── scripts/
│   ├── ancestry_import.py       # Import DNA matches
│   ├── import_shared_matches.py # Import triangulation data
│   ├── import_match_trees.py    # Batch tree imports
│   ├── import_ancestry_tree.py  # Single tree import
│   ├── import_thrulines.py      # Import ThruLines data
│   ├── find_unknown_father_matches.py  # Main analysis
│   └── cluster_matches.py       # Graph clustering
├── family-tree-app/             # Web app for viewing trees (Mission 7)
│   ├── pom.xml                  # Spring Boot 3.4 + Thymeleaf
│   └── src/main/
│       ├── java/                # Controllers, config, models
│       └── resources/
│           ├── static/trees/    # SVG tree diagrams
│           └── templates/       # Thymeleaf templates
├── logs/                        # Research session logs
└── venv/                        # Python environment
```

---

---

## Overnight Research Session (11-12 January 2026)

### Key Findings

**Wrathall Line (18+19) Cluster Identified:**
- Bruce Lightfoot (118 cM), Helen Brammer (112 cM), Michelle Morris (49 cM), Wendy Freeman (44 cM), Kim Parker (43 cM), Rachel Wrathall (38 cM)
- All triangulate with hugh copland (44 cM) through Henry Wrathall + Mary Alice Metcalfe (positions 18+19)
- Rachel Wrathall's tree (305) contains detailed Wrathall genealogy from Thornton-in-Lonsdale, Yorkshire

**Heywood Line (28+29) Confirmed:**
- jane_gessler (125 cM) connects through Thomas Heywood line
- Her tree has different Heywood children than the main tree, suggesting connection through Thomas Heywood's parents or siblings

**Wood Line (24+25) Confirmed:**
- geri_wood (48 cM), Jed Wood (32 cM), Ryan Wood (29 cM), Travis Wood (23 cM)
- Distinctive "Leigh" middle names in geri_wood's tree suggest a specific Wood branch

**UNK-PAT Cluster (Unknown Paternal Line):**
Strong cluster identified with consistent triangulation:
- Brenda Davey (100 cM), Ethel Hull (51 cM), Valerie Simpson (45 cM), Jill Lester (37 cM), Peter Ennor (34 cM)
- Shared surnames across UNK-PAT trees include: Hill, Fletcher, Harrison, Barlow, Carpenter
- No distinctive surname yet identified as potential unknown father's family

**Key Surnames from Brenda Davey's Tree (Top UNK-PAT Match at 101 cM):**
- **STEMP** - Concentrated in West Sussex (15%), Greater London (11%), Hampshire (10%)
- **FREEMANTLE** - 31% in Hampshire, 10% Greater London, 8% Berkshire (named after parish near Southampton)
- **IVES** - Common across Southern England

**Geographic Significance:** These surnames point to Hampshire/South England, NOT Lancashire where Susan Wrathall lived. This could indicate:
1. The unknown father was from Southern England (not Westmorland)
2. Or these are matches through a different line in Brenda's tree
3. Further triangulation within the sub-cluster needed

**Brenda Davey Sub-Cluster:** Brenda Davey (101 cM), Katrina Barnes (39 cM), and Alexander Lloyd (22 cM) share extremely high cM with each other (1600+ cM), indicating they are close family (siblings/parent-child). They form a distinct group within UNK-PAT.

**Important Pattern: UNK-PAT + Wrathall Overlap**
Several UNK-PAT matches ALSO share matches on the 18+19 (Wrathall) line:
- Emily Evans (UNK-PAT) shares: Wendy Freeman (18+19), hugh copland (18+19)
- Thomas Arnstein (UNK-PAT) shares: Wendy Freeman (18+19), hugh copland (18+19)
- Joanne Harrison (UNK-PAT) shares: Bruce Lightfoot (18+19), Michelle Morris (18+19)

This could indicate:
1. The unknown father was connected to the Wrathall family (supporting the Lowther hypothesis)
2. Or these matches have multiple relationship paths
3. Or some MRCA markings need correction

- Angela Ganley (70 cM) marked UNK-PAT but shares jane_gessler (126 cM, Heywood) - marking may be incorrect

**Lonsdale Name Usage:**
- Henry Lonsdale Wrathall (1863) gave "Lonsdale" middle name to multiple children:
  - Constance Mary Lonsdale Wrathall (1887)
  - Kenneth David Lonsdale Wrathall (1923)
- This naming pattern supports the hypothesis of a Lowther/Lonsdale family connection

### MRCA Marking Corrections Needed

| Match | Current MRCA | Should Be | Reason |
|-------|--------------|-----------|--------|
| Margaret Wagstaff | 18+19 | UNK-PAT | All shared matches are UNK-PAT |
| Angela Ganley | UNK-PAT | ? | Shares jane_gessler at 126 cM (Heywood) - investigate |
| Georgina Burton-Roberts | 18+19 | UNK-PAT? | Shares mostly UNK-PAT matches |

### Next Steps

1. Investigate Angela Ganley / jane_gessler overlap - why does an UNK-PAT share so strongly with a Heywood match?
2. Expand research on Jill Lester's tree for Westmorland/Cumberland connections
3. Continue researching remaining top 50 matches (diane_lovick, Kate Ellis, etc.)
4. Cross-reference UNK-PAT trees for common geographic areas (Lancashire, Westmorland)

---

---

## ThruLines Import Session (12 January 2026)

### Data Imported from ThruLines
- **176 ancestors** extracted from ThruLines main grid (Ahnentafel 2-176+)
- **203 people** imported to tree_id=1 with source='thrulines'
- **Tree now contains 452 people**

### New Ancestors Identified

| Ahnentafel | Name | Years | Notes |
|------------|------|-------|-------|
| 38 | Richard Metcalfe | 1830-1868 | 3rd great-grandfather, father of Mary Alice Metcalfe |
| 64 | James Worthington | 1791-1857 | 4th great-grandfather |
| 65 | Jane Roby | 1801-1881 | 4th great-grandmother |
| 128 | Henry Worthington | 1777-1854 | 5th great-grandfather |
| 129 | Jane Hooton | 1777-1851 | 5th great-grandmother |

### DNA Matches Mapped via ThruLines

| Match | cM | MRCA (Ahnentafel) | Ancestor Names |
|-------|-----|-------------------|----------------|
| hazelhersant | 58 cM | 22+23 | George Virgo / Maria Brown |
| Margaret Wagstaff | 53 cM | 26+27 | John Parker / Margaret Thompson |
| diane_lovick | 48 cM | 30+31 | James TART / Emily Tart |
| gstewart37 | 35 cM | 30+31 | James TART / Emily Tart |
| James Horridge | 17 cM | 30+31 | James TART / Emily Tart |
| youngcodge2 | 17 cM | 34+35 | Charles Hollows / Mary Rothwell |
| Christopher Bryan | 12 cM | 32+33 | George WORTHINGTON / Nancy HOWARTH |
| pcmtdm | 12 cM | 34+35 | Charles Hollows / Mary Rothwell |

### ThruLines Warning: Lowther Data Removed

ThruLines suggested Lowther family members as ancestors based on other users' speculative trees. **This data has been removed from our database** because:

1. It originates from unverified Wrathall family trees (possibly including our own)
2. It creates circular reasoning - we can't prove a Lowther connection using trees that assume the connection
3. The source is family tradition ([wrathall.org memoir](https://wrathall.org/wrathall/james/australia/lonsdalewrathall.html)), not documentary evidence

**Position 36 (HLW's father) remains UNKNOWN.** Any ThruLines suggestion for this position should be ignored until verified by independent DNA evidence from confirmed Lowther descendants.

### New Script Added

`scripts/import_thrulines.py` - Scrapes ThruLines page using Playwright:
- Extracts all suggested ancestors
- Drills into each ancestor to find connected DNA matches
- Imports people and MRCA connections to database

Usage:
```bash
source venv/bin/activate
python scripts/import_thrulines.py
```

---

---

## D3.js Interactive Tree Migration (15 January 2026)

### Changes Made

Replaced static pre-generated SVG files with interactive D3.js visualization for the family tree viewer.

**New Files:**
- `family-tree-app/src/main/java/com/familytree/controller/TreeApiController.java` - REST endpoint for tree hierarchy JSON
- `family-tree-app/src/main/resources/static/js/d3-tree.js` - D3.js visualization module

**Modified Files:**
- `tree-view.html` - Updated to use D3.js instead of inline SVG
- `FamilyTreeConfig.java` - Added `rootPersonId` field
- `application.yml` - Added `rootPersonId` to each tree configuration

**Features:**
- Horizontal timeline layout (X = birth year, width = lifespan)
- Zoom/pan with mouse wheel and drag
- Collapsible nodes (shift+click or +/- buttons)
- Click person cards to open sidebar with details + census records
- Gender-colored cards (blue for male, pink for female)
- Year marker lines every 25 years

**API Endpoint:**
```
GET /api/trees/{slug}/hierarchy
```
Returns nested JSON hierarchy for D3.js:
```json
{
  "id": 1,
  "name": "Henry S. Wrathall",
  "dates": "1843-1927",
  "gender": "M",
  "children": [...]
}
```

---

---

## Ahnentafel Cluster System (19 January 2026)

### Overview

Rebuilt the DNA match clustering system from scratch using ahnentafel positions. Each cluster represents an ancestral line, not necessarily descent from that specific ancestor.

**Key principle:** Assigning a match to cluster 18 (HLW) means "the DNA we share likely comes through the HLW ancestral line" - NOT "this person descends from HLW." The match could descend from HLW, HLW's sibling, HLW's uncle, etc.

### Cluster Structure

Created 127 clusters covering ahnentafel positions 2-128:

| Generation | Positions | Example |
|------------|-----------|---------|
| Parents | 2-3 | Jonathan Worthington, Patricia Wood |
| Grandparents | 4-7 | Arthur GL Worthington, Marjorie Goodall |
| Great-GP | 8-15 | Arthur Worthington, Constance Wrathall |
| 2x Great-GP | 16-31 | James Worthington, HLW, Emily Tart |
| 3x Great-GP | 32-63 | George Worthington, Charles Hollows, Mary Rothwell |
| 4x Great-GP | 64-127 | James Worthington Sr, Henry Worthington |

### Compound Clusters

For close relatives who match through multiple ancestors:
- **203 (2+3)** - Full siblings (both parents)
- **405 (4+5)** - Paternal grandparent descendants (1st cousins)

### Current Cluster Assignments (ThruLines-verified)

| Pos | Ancestor | Matches | Top Match (cM) |
|-----|----------|---------|----------------|
| 18 | Henry L Wrathall (HLW) | 3 | Helen Brammer (113) |
| 31 | Emily Tart | 9 | diane_lovick (48) |
| 32 | George Worthington | 5 | Peter Davies (21) |
| 34 | Charles Hollows | 2 | youngcodge2 (17) |
| 35 | Mary Rothwell | 6 | noel booth (27) |
| 38 | Richard Metcalfe | 1 | john durling (13) |
| 64 | James Worthington | 1 | sthomas14145 (9) |
| 203 | 2+3 (Sibling) | 1 | Rebecca Hyndman (2699) |
| 405 | 4+5 (Paternal GP) | 2 | Bruce Horrocks (605) |

**Total: 30 matches across 9 clusters**

### Validation Discovery

During cluster validation, discovered that the previous "Unknown HLW Father" cluster (position 36) was incorrectly assigned. Confirmed HLW descendants (Rachel Wrathall, Helen Brammer, Bruce Lightfoot) did NOT share with that cluster's members, indicating it was not the paternal line.

The cluster system has been reset. Only ThruLines-verified connections are now assigned.

### Database Schema

```sql
-- Cluster table
CREATE TABLE cluster (
    id INTEGER PRIMARY KEY,
    assigned_ahnentafel INTEGER,  -- NULL for compound clusters
    description TEXT,
    created_at DATETIME
);

-- DNA match cluster assignment
dna_match.cluster_id  -- FK to cluster.id
dna_match.mrca        -- Text like "18", "4+5", "32"
```

### Query Examples

```sql
-- View all clustered matches
SELECT c.id, c.description, dm.name, dm.shared_cm
FROM dna_match dm
JOIN cluster c ON dm.cluster_id = c.id
ORDER BY c.id, dm.shared_cm DESC;

-- Find matches in a specific ancestral line
SELECT name, shared_cm FROM dna_match
WHERE cluster_id = 18;  -- HLW line
```

---

*Last updated: 19 January 2026*
