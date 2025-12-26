-- 004_dna_matches.sql
-- Tables for DNA match tracking from Ancestry.com

CREATE TABLE IF NOT EXISTS dna_match (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ancestry_id TEXT,                    -- Ancestry.com match ID if available
    name TEXT NOT NULL,                  -- Match name
    shared_cm REAL,                      -- Shared centimorgans
    shared_segments INTEGER,             -- Number of shared segments
    predicted_relationship TEXT,         -- Ancestry's prediction (e.g., "3rd cousin")
    common_ancestor_id INTEGER REFERENCES person(id),  -- Primary common ancestor
    match_side TEXT CHECK (match_side IN ('paternal', 'maternal', 'both', 'unknown')),
    has_tree BOOLEAN DEFAULT FALSE,      -- Does match have a tree?
    tree_size INTEGER,                   -- Number of people in their tree
    notes TEXT,
    cluster_group TEXT,                  -- For grouping related matches
    confirmed BOOLEAN DEFAULT FALSE,     -- Is the connection confirmed?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Link table for matches sharing multiple common ancestors
CREATE TABLE IF NOT EXISTS dna_match_ancestor_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dna_match_id INTEGER NOT NULL REFERENCES dna_match(id),
    person_id INTEGER NOT NULL REFERENCES person(id),
    relationship_to_match TEXT,          -- e.g., "great-great-grandfather"
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
    notes TEXT,
    UNIQUE(dna_match_id, person_id)
);

-- Track which matches share DNA with each other (for clustering)
CREATE TABLE IF NOT EXISTS dna_shared_match_group (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match1_id INTEGER NOT NULL REFERENCES dna_match(id),
    match2_id INTEGER NOT NULL REFERENCES dna_match(id),
    shared_cm REAL,
    notes TEXT
);
