-- V3__consolidate_dna_match.sql
-- Consolidate ancestry_person + ancestry_match into proper dna_match table
--
-- Current state (diverged from V2):
--   - ancestry_person: DNA match profiles (ancestry_id PK, name, etc.)
--   - ancestry_match: relationship data (person1_id, person2_id, shared_cm)
--   - dna_match: VIEW joining the above (hack)
--   - match_cluster.ancestry_person_id -> ancestry_person
--   - tree.ancestry_person_id -> ancestry_person
--
-- Target state:
--   - dna_match: proper TABLE with all match data
--   - match_cluster.dna_match_id -> dna_match
--   - tree.dna_match_id -> dna_match
--   - ancestry_person and ancestry_match dropped

-- ============================================
-- STEP 1: Drop the hacky view
-- ============================================

DROP VIEW IF EXISTS dna_match;

-- ============================================
-- STEP 2: Create proper dna_match table
-- ============================================

CREATE TABLE dna_match (
    ancestry_id VARCHAR(36) NOT NULL,
    name VARCHAR(500) NOT NULL,
    shared_cm NUMERIC(8,3),
    shared_segments INTEGER,
    predicted_relationship VARCHAR(100),
    source VARCHAR(50) DEFAULT 'ancestry',
    admin_level INTEGER,
    has_tree BOOLEAN DEFAULT FALSE,
    tree_size INTEGER,
    notes TEXT,
    match_side VARCHAR(20),
    mrca VARCHAR(50),
    mrca_confidence VARCHAR(20),
    community_id INTEGER,
    matched_to_person_id INTEGER NOT NULL DEFAULT 1,
    person_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dna_match_pkey PRIMARY KEY (ancestry_id),
    CONSTRAINT dna_match_match_side_check CHECK (match_side IN ('paternal', 'maternal', 'both', 'unknown')),
    CONSTRAINT dna_match_mrca_confidence_check CHECK (mrca_confidence IN ('confirmed', 'high', 'medium', 'low'))
);

COMMENT ON COLUMN dna_match.ancestry_id IS 'Ancestry.com test GUID - uniquely identifies this DNA match';
COMMENT ON COLUMN dna_match.name IS 'Display name of the DNA match';
COMMENT ON COLUMN dna_match.matched_to_person_id IS 'The person in our tree whose DNA test this match appears on (default 1 = me)';
COMMENT ON COLUMN dna_match.person_id IS 'Link to person record when match has been identified in family tree';
COMMENT ON COLUMN dna_match.admin_level IS 'Ancestry admin level: 0=viewer, 1=contributor, 2=editor, 3=manager, 4=owner';
COMMENT ON COLUMN dna_match.match_side IS 'Which side of the family: paternal, maternal, both, or unknown';
COMMENT ON COLUMN dna_match.mrca IS 'Most recent common ancestor if known';

-- ============================================
-- STEP 3: Migrate data from ancestry_person + ancestry_match
-- ============================================

-- Your ancestry_id for the LEFT JOIN (person1_id in ancestry_match)
-- We need to find this - it's the one that appears as person1_id
-- For now, assuming there's one primary tester

INSERT INTO dna_match (
    ancestry_id,
    name,
    shared_cm,
    shared_segments,
    predicted_relationship,
    source,
    admin_level,
    has_tree,
    tree_size,
    notes,
    match_side,
    mrca,
    mrca_confidence,
    community_id,
    matched_to_person_id,
    person_id,
    created_at,
    updated_at
)
SELECT DISTINCT ON (ap.ancestry_id)
    ap.ancestry_id,
    ap.name,
    am.shared_cm,
    am.shared_segments,
    ap.predicted_relationship,
    'ancestry',
    ap.admin_level,
    ap.has_tree,
    ap.tree_size,
    ap.notes,
    ap.match_side,
    ap.mrca,
    ap.mrca_confidence,
    ap.community_id,
    1,  -- matched_to_person_id (you)
    ap.person_id,
    ap.created_at,
    ap.updated_at
FROM ancestry_person ap
LEFT JOIN ancestry_match am ON ap.ancestry_id = am.person2_id
ORDER BY ap.ancestry_id, am.shared_cm DESC NULLS LAST;

-- ============================================
-- STEP 4: Update match_cluster
-- ============================================

-- Rename column for clarity (already named ancestry_person_id, rename to dna_match_id)
ALTER TABLE match_cluster RENAME COLUMN ancestry_person_id TO dna_match_id;

-- Drop old constraint if exists
ALTER TABLE match_cluster DROP CONSTRAINT IF EXISTS match_cluster_ancestry_person_fkey;

-- Add new foreign key
ALTER TABLE match_cluster 
ADD CONSTRAINT match_cluster_dna_match_fkey 
FOREIGN KEY (dna_match_id) REFERENCES dna_match(ancestry_id);

-- ============================================
-- STEP 5: Update tree table
-- ============================================

-- Rename column
ALTER TABLE tree RENAME COLUMN ancestry_person_id TO dna_match_id;

-- Drop old constraint if exists  
ALTER TABLE tree DROP CONSTRAINT IF EXISTS tree_ancestry_person_fkey;

-- Add new foreign key
ALTER TABLE tree
ADD CONSTRAINT tree_dna_match_fkey
FOREIGN KEY (dna_match_id) REFERENCES dna_match(ancestry_id);

-- ============================================
-- STEP 6: Add indexes
-- ============================================

CREATE INDEX idx_dna_match_name ON dna_match(name);
CREATE INDEX idx_dna_match_shared_cm ON dna_match(shared_cm DESC NULLS LAST);
CREATE INDEX idx_dna_match_matched_to_person ON dna_match(matched_to_person_id);
CREATE INDEX idx_dna_match_person_id ON dna_match(person_id) WHERE person_id IS NOT NULL;
CREATE INDEX idx_dna_match_match_side ON dna_match(match_side) WHERE match_side IS NOT NULL;

-- ============================================
-- STEP 7: Add foreign key for person_id (identified matches)
-- ============================================

-- Note: matched_to_person_id FK omitted - person 1 doesn't exist in this DB
-- It's just a marker for which DNA test kit these matches belong to

ALTER TABLE dna_match
ADD CONSTRAINT dna_match_person_fkey
FOREIGN KEY (person_id) REFERENCES person(id);

-- ============================================
-- STEP 8: Drop old tables
-- ============================================

-- Drop foreign keys first
ALTER TABLE ancestry_match DROP CONSTRAINT IF EXISTS ancestry_match_person1_id_fkey;
ALTER TABLE ancestry_match DROP CONSTRAINT IF EXISTS ancestry_match_person2_id_fkey;
ALTER TABLE ancestry_person DROP CONSTRAINT IF EXISTS ancestry_person_person_id_fkey;

-- Drop indexes
DROP INDEX IF EXISTS idx_ancestry_person_person_id;

-- Drop tables
DROP TABLE ancestry_match;
DROP TABLE ancestry_person;

-- ============================================
-- STEP 9: Clean up match_cluster.person_id if it exists
-- ============================================

-- This column was from the old V1 schema, may still exist
ALTER TABLE match_cluster DROP COLUMN IF EXISTS person_id;

-- ============================================
-- VERIFICATION (run manually after migration)
-- ============================================

-- SELECT COUNT(*) as total_matches FROM dna_match;
-- SELECT COUNT(*) as with_cm FROM dna_match WHERE shared_cm IS NOT NULL;
-- SELECT * FROM dna_match ORDER BY shared_cm DESC NULLS LAST LIMIT 10;
