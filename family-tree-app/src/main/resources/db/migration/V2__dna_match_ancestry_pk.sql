-- V2__dna_match_ancestry_pk.sql
-- Restructure dna_match to use Ancestry GUID as primary key
--
-- Current state:
--   - dna_match links two person records (person_1_id, person_2_id)
--   - DNA match details (name, ancestry_guid) are on person records (id >= 900000)
--   - match_cluster.person_id references person records for DNA matches
--   - tree.match_person_id references person records for DNA matches
--
-- New state:
--   - dna_match is a standalone entity with ancestry_id (GUID) as primary key
--   - Contains match details: name, shared_cm, shared_segments, etc.
--   - matched_to_person_id is a required FK to person whose match list this appears on (e.g. me)
--   - person_id is a nullable FK for when we've identified the match in our tree
--   - match_cluster references dna_match.ancestry_id
--   - tree references dna_match.ancestry_id

-- ============================================
-- STEP 1: Create new dna_match table structure
-- ============================================

CREATE TABLE dna_match_new (
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
    matched_to_person_id INTEGER NOT NULL,
    person_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dna_match_new_pkey PRIMARY KEY (ancestry_id)
);

COMMENT ON COLUMN dna_match_new.ancestry_id IS 'Ancestry.com test GUID - uniquely identifies this DNA match';
COMMENT ON COLUMN dna_match_new.name IS 'Display name of the DNA match (username or real name from Ancestry)';
COMMENT ON COLUMN dna_match_new.matched_to_person_id IS 'The person in our tree whose DNA test this match appears on (e.g. person 1 = me)';
COMMENT ON COLUMN dna_match_new.person_id IS 'Optional link to person record when match has been identified in our family tree';
COMMENT ON COLUMN dna_match_new.admin_level IS 'Ancestry admin level: 0=viewer, 1=contributor, 2=editor, 3=manager, 4=owner';

-- ============================================
-- STEP 2: Migrate data from old structure
-- ============================================

-- Insert data joining old dna_match with person table to get ancestry_guid and name
-- We only migrate records where we have an ancestry_guid (the Ancestry GUID)
-- matched_to_person_id comes from person_1_id (the person whose match list this appears on)
INSERT INTO dna_match_new (
    ancestry_id,
    name,
    shared_cm,
    shared_segments,
    source,
    notes,
    matched_to_person_id,
    created_at
)
SELECT DISTINCT ON (p.ancestry_guid)
    p.ancestry_guid,
    COALESCE(NULLIF(TRIM(CONCAT(p.first_name, ' ', COALESCE(p.surname, ''))), ''), 'Unknown'),
    dm.shared_cm,
    dm.shared_segments,
    dm.source,
    dm.notes,
    dm.person_1_id,
    dm.created_at
FROM dna_match dm
JOIN person p ON p.id = dm.person_2_id
WHERE p.ancestry_guid IS NOT NULL
ORDER BY p.ancestry_guid, dm.shared_cm DESC NULLS LAST;

-- ============================================
-- STEP 3: Update match_cluster to reference dna_match
-- ============================================

-- Add new column for ancestry_id reference
ALTER TABLE match_cluster ADD COLUMN dna_match_id VARCHAR(36);

-- Populate from person.ancestry_guid
UPDATE match_cluster mc
SET dna_match_id = p.ancestry_guid
FROM person p
WHERE mc.person_id = p.id
  AND p.ancestry_guid IS NOT NULL;

-- Add foreign key constraint (only after populating)
ALTER TABLE match_cluster
ADD CONSTRAINT match_cluster_dna_match_id_fkey
FOREIGN KEY (dna_match_id) REFERENCES dna_match_new(ancestry_id);

-- Create index for the new column
CREATE INDEX idx_match_cluster_dna_match ON match_cluster(dna_match_id);

-- ============================================
-- STEP 4: Update tree to reference dna_match
-- ============================================

-- Add new column for ancestry_id reference
ALTER TABLE tree ADD COLUMN dna_match_id VARCHAR(36);

-- Populate from person.ancestry_guid
UPDATE tree t
SET dna_match_id = p.ancestry_guid
FROM person p
WHERE t.match_person_id = p.id
  AND p.ancestry_guid IS NOT NULL;

-- Add foreign key constraint
ALTER TABLE tree
ADD CONSTRAINT tree_dna_match_id_fkey
FOREIGN KEY (dna_match_id) REFERENCES dna_match_new(ancestry_id);

-- Create index
CREATE INDEX idx_tree_dna_match ON tree(dna_match_id);

-- ============================================
-- STEP 5: Add indexes to new dna_match table
-- ============================================

CREATE INDEX idx_dna_match_new_name ON dna_match_new(name);
CREATE INDEX idx_dna_match_new_shared_cm ON dna_match_new(shared_cm);
CREATE INDEX idx_dna_match_new_matched_to_person ON dna_match_new(matched_to_person_id);
CREATE INDEX idx_dna_match_new_person_id ON dna_match_new(person_id) WHERE person_id IS NOT NULL;

-- Add foreign key for matched_to_person_id
ALTER TABLE dna_match_new
ADD CONSTRAINT dna_match_new_matched_to_person_id_fkey
FOREIGN KEY (matched_to_person_id) REFERENCES person(id);

-- Add foreign key for person_id
ALTER TABLE dna_match_new
ADD CONSTRAINT dna_match_new_person_id_fkey
FOREIGN KEY (person_id) REFERENCES person(id);

-- ============================================
-- STEP 6: Clean up old structure
-- ============================================

-- Drop old foreign key constraints on dna_match
ALTER TABLE dna_match DROP CONSTRAINT IF EXISTS dna_match_person_1_id_fkey;
ALTER TABLE dna_match DROP CONSTRAINT IF EXISTS dna_match_person_2_id_fkey;

-- Drop old match_cluster constraints and column
ALTER TABLE match_cluster DROP CONSTRAINT IF EXISTS match_cluster_person_id_fkey;
DROP INDEX IF EXISTS idx_match_cluster_person;

-- Drop old tree constraint and column (keep match_person_id for now as it may still be useful)
ALTER TABLE tree DROP CONSTRAINT IF EXISTS tree_match_person_id_fkey;

-- Drop old dna_match table
DROP TABLE dna_match;

-- Rename new table to dna_match
ALTER TABLE dna_match_new RENAME TO dna_match;

-- Rename constraints to match new table name
ALTER TABLE dna_match RENAME CONSTRAINT dna_match_new_pkey TO dna_match_pkey;
ALTER TABLE dna_match RENAME CONSTRAINT dna_match_new_matched_to_person_id_fkey TO dna_match_matched_to_person_id_fkey;
ALTER TABLE dna_match RENAME CONSTRAINT dna_match_new_person_id_fkey TO dna_match_person_id_fkey;

-- Rename indexes
ALTER INDEX idx_dna_match_new_name RENAME TO idx_dna_match_name;
ALTER INDEX idx_dna_match_new_shared_cm RENAME TO idx_dna_match_shared_cm;
ALTER INDEX idx_dna_match_new_matched_to_person RENAME TO idx_dna_match_matched_to_person;
ALTER INDEX idx_dna_match_new_person_id RENAME TO idx_dna_match_person_id;

-- Update match_cluster constraint name
ALTER TABLE match_cluster RENAME CONSTRAINT match_cluster_dna_match_id_fkey TO match_cluster_dna_match_fkey;
ALTER INDEX idx_match_cluster_dna_match RENAME TO idx_match_cluster_dna_match_id;

-- Update tree constraint name
ALTER TABLE tree RENAME CONSTRAINT tree_dna_match_id_fkey TO tree_dna_match_fkey;
ALTER INDEX idx_tree_dna_match RENAME TO idx_tree_dna_match_id;

-- ============================================
-- STEP 7: Clean up match_cluster person_id column
-- ============================================

-- Make person_id nullable (it referenced DNA match persons, now we use dna_match_id)
ALTER TABLE match_cluster ALTER COLUMN person_id DROP NOT NULL;

-- Note: We keep person_id for now in case there are references we missed,
-- but dna_match_id is now the canonical reference

-- ============================================
-- VERIFICATION QUERIES (commented out for reference)
-- ============================================

-- Check migrated records:
-- SELECT COUNT(*) FROM dna_match;
-- SELECT * FROM dna_match ORDER BY shared_cm DESC LIMIT 10;

-- Check match_cluster updates:
-- SELECT mc.*, dm.name FROM match_cluster mc JOIN dna_match dm ON mc.dna_match_id = dm.ancestry_id LIMIT 5;

-- Check tree updates:
-- SELECT t.id, t.name, t.dna_match_id, dm.name as match_name FROM tree t JOIN dna_match dm ON t.dna_match_id = dm.ancestry_id LIMIT 5;
