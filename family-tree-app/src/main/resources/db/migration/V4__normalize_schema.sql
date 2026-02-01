-- V4__normalize_schema.sql
-- 
-- Major restructuring:
--   1. Rename DNA tables to ancestry_* prefix for clarity
--   2. All people go in person table (no separate tree_relationship)
--   3. person.tree_id links to which tree they belong to
--   4. tree table gets size and ancestry_tree_id columns
--   5. ancestor table for ahnentafel (YOUR direct line only)
--   6. Clear distinction: dna_test_id (UUID) vs tree_person_id (BIGINT)

-- ============================================
-- STEP 1: Rename dna_match to ancestry_tester
-- ============================================

ALTER TABLE dna_match RENAME TO ancestry_tester;
ALTER TABLE ancestry_tester RENAME COLUMN ancestry_id TO dna_test_id;

-- Rename constraints
ALTER TABLE ancestry_tester RENAME CONSTRAINT dna_match_pkey TO ancestry_tester_pkey;
ALTER TABLE ancestry_tester RENAME CONSTRAINT dna_match_person_id_fkey TO ancestry_tester_person_fkey;

-- Rename indexes
ALTER INDEX IF EXISTS idx_dna_match_name RENAME TO idx_ancestry_tester_name;
ALTER INDEX IF EXISTS idx_dna_match_person_id RENAME TO idx_ancestry_tester_person_id;

COMMENT ON TABLE ancestry_tester IS 'People who have taken a DNA test on Ancestry.com';
COMMENT ON COLUMN ancestry_tester.dna_test_id IS 'Ancestry DNA test GUID (UUID format)';

-- ============================================
-- STEP 2: Create ancestry_dna_match table
-- ============================================

CREATE TABLE ancestry_dna_match (
    tester_1_id VARCHAR(36) NOT NULL,
    tester_2_id VARCHAR(36) NOT NULL,
    shared_cm NUMERIC(8,3),
    shared_segments INTEGER,
    predicted_relationship VARCHAR(100),
    match_side VARCHAR(20),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ancestry_dna_match_pkey PRIMARY KEY (tester_1_id, tester_2_id),
    CONSTRAINT ancestry_dna_match_tester_1_fkey FOREIGN KEY (tester_1_id) REFERENCES ancestry_tester(dna_test_id),
    CONSTRAINT ancestry_dna_match_tester_2_fkey FOREIGN KEY (tester_2_id) REFERENCES ancestry_tester(dna_test_id),
    CONSTRAINT ancestry_dna_match_order CHECK (tester_1_id < tester_2_id),
    CONSTRAINT ancestry_dna_match_side_check CHECK (match_side IN ('paternal', 'maternal', 'both', 'unknown'))
);

COMMENT ON TABLE ancestry_dna_match IS 'DNA relationships between testers - yours AND shared matches between your matches';
COMMENT ON COLUMN ancestry_dna_match.tester_1_id IS 'First tester DNA test ID (alphabetically smaller due to constraint)';
COMMENT ON COLUMN ancestry_dna_match.tester_2_id IS 'Second tester DNA test ID (alphabetically larger due to constraint)';
COMMENT ON COLUMN ancestry_dna_match.match_side IS 'Paternal/maternal - only populated for your direct matches';

-- Indexes for ancestry_dna_match
CREATE INDEX idx_ancestry_dna_match_tester_1 ON ancestry_dna_match(tester_1_id);
CREATE INDEX idx_ancestry_dna_match_tester_2 ON ancestry_dna_match(tester_2_id);
CREATE INDEX idx_ancestry_dna_match_shared_cm ON ancestry_dna_match(shared_cm DESC NULLS LAST);
CREATE INDEX idx_ancestry_dna_match_side ON ancestry_dna_match(match_side) WHERE match_side IS NOT NULL;

-- ============================================
-- STEP 3: Update tree table
-- ============================================

-- Add ancestry_tree_id for scraped trees (NULL for your own research)
ALTER TABLE tree ADD COLUMN ancestry_tree_id BIGINT;

-- Add size column (denormalized for performance)
ALTER TABLE tree ADD COLUMN size INTEGER DEFAULT 0;

-- Rename dna_match_id to dna_test_id for consistency
ALTER TABLE tree RENAME COLUMN dna_match_id TO dna_test_id;

-- Update constraint
ALTER TABLE tree DROP CONSTRAINT IF EXISTS tree_dna_match_fkey;
ALTER TABLE tree ADD CONSTRAINT tree_dna_test_fkey 
    FOREIGN KEY (dna_test_id) REFERENCES ancestry_tester(dna_test_id);

-- Update index
DROP INDEX IF EXISTS idx_tree_dna_match_id;
CREATE INDEX idx_tree_dna_test_id ON tree(dna_test_id) WHERE dna_test_id IS NOT NULL;
CREATE INDEX idx_tree_ancestry_tree_id ON tree(ancestry_tree_id) WHERE ancestry_tree_id IS NOT NULL;

COMMENT ON COLUMN tree.ancestry_tree_id IS 'Ancestry.com tree ID (numeric) - NULL for your own research trees';
COMMENT ON COLUMN tree.size IS 'Number of people in this tree (denormalized for performance)';
COMMENT ON COLUMN tree.dna_test_id IS 'Links to the DNA tester whose tree this is (if applicable)';

-- ============================================
-- STEP 4: Update person table
-- ============================================

-- Add tree_id FK
ALTER TABLE person ADD COLUMN tree_id INTEGER;
ALTER TABLE person ADD CONSTRAINT person_tree_fkey FOREIGN KEY (tree_id) REFERENCES tree(id);
CREATE INDEX idx_person_tree_id ON person(tree_id) WHERE tree_id IS NOT NULL;

-- Rename ancestry_guid to dna_test_id
ALTER TABLE person RENAME COLUMN ancestry_guid TO dna_test_id;

-- Add tree_person_id for Ancestry's numeric person ID
ALTER TABLE person ADD COLUMN tree_person_id BIGINT;

-- Update index
DROP INDEX IF EXISTS idx_person_ancestry_guid;
CREATE INDEX idx_person_dna_test_id ON person(dna_test_id) WHERE dna_test_id IS NOT NULL;
CREATE INDEX idx_person_tree_person_id ON person(tree_person_id) WHERE tree_person_id IS NOT NULL;

COMMENT ON COLUMN person.tree_id IS 'Which tree this person belongs to';
COMMENT ON COLUMN person.dna_test_id IS 'Ancestry DNA test GUID (UUID) - only if this person has taken a DNA test';
COMMENT ON COLUMN person.tree_person_id IS 'Ancestry tree person ID (numeric) - from scraped Ancestry trees';

-- ============================================
-- STEP 5: Create ancestor table
-- ============================================

CREATE TABLE ancestor (
    ahnentafel INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ancestor_pkey PRIMARY KEY (ahnentafel),
    CONSTRAINT ancestor_person_key UNIQUE (person_id),
    CONSTRAINT ancestor_person_fkey FOREIGN KEY (person_id) REFERENCES person(id)
);

COMMENT ON TABLE ancestor IS 'Maps ahnentafel numbers to person records. Only for YOUR direct ancestors.';
COMMENT ON COLUMN ancestor.ahnentafel IS '1=you, 2=father, 3=mother, 4=paternal grandfather, etc.';

-- ============================================
-- STEP 6: Migrate ahnentafel data
-- ============================================

INSERT INTO ancestor (ahnentafel, person_id)
SELECT ahnentafel, id
FROM person
WHERE ahnentafel IS NOT NULL;

-- ============================================
-- STEP 7: Update cluster to reference ancestor
-- ============================================

ALTER TABLE cluster DROP CONSTRAINT IF EXISTS cluster_ahnentafel_1_fkey;
ALTER TABLE cluster DROP CONSTRAINT IF EXISTS cluster_ahnentafel_2_fkey;

-- Note: FK constraints omitted - cluster has ahnentafel values (2-128)
-- that reference ancestors not yet in person table (data cleanup needed)
-- ALTER TABLE cluster ADD CONSTRAINT cluster_ahnentafel_1_fkey
--     FOREIGN KEY (ahnentafel_1) REFERENCES ancestor(ahnentafel);
-- ALTER TABLE cluster ADD CONSTRAINT cluster_ahnentafel_2_fkey
--     FOREIGN KEY (ahnentafel_2) REFERENCES ancestor(ahnentafel);

-- ============================================
-- STEP 8: Drop ahnentafel from person
-- ============================================

ALTER TABLE person DROP CONSTRAINT IF EXISTS person_ahnentafel_key;
DROP INDEX IF EXISTS idx_person_ahnentafel;
ALTER TABLE person DROP COLUMN IF EXISTS ahnentafel;

-- ============================================
-- STEP 9: Update match_cluster to reference ancestry_tester
-- ============================================

ALTER TABLE match_cluster RENAME COLUMN dna_match_id TO dna_test_id;
ALTER TABLE match_cluster DROP CONSTRAINT IF EXISTS match_cluster_dna_match_fkey;
ALTER TABLE match_cluster ADD CONSTRAINT match_cluster_ancestry_tester_fkey 
    FOREIGN KEY (dna_test_id) REFERENCES ancestry_tester(dna_test_id);

DROP INDEX IF EXISTS idx_match_cluster_dna_match_id;
CREATE INDEX idx_match_cluster_dna_test_id ON match_cluster(dna_test_id);

-- ============================================
-- STEP 10: Drop tree_relationship (no longer needed)
-- ============================================

DROP TABLE IF EXISTS tree_relationship;

-- ============================================
-- STEP 11: Insert yourself into ancestry_tester
-- ============================================

-- Your DNA test ID: e756de6c-0c8d-443b-8793-addb6f35fd6a
-- Note: person_id left NULL since person 1 doesn't exist in this DB

-- Only insert if person 1 exists (dev database has data, scratch is empty)
INSERT INTO ancestry_tester (dna_test_id, name, matched_to_person_id, person_id, created_at)
SELECT 'e756de6c-0c8d-443b-8793-addb6f35fd6a', 'Chris Worthington', 1, NULL, CURRENT_TIMESTAMP
WHERE EXISTS (SELECT 1 FROM person WHERE id = 1)
ON CONFLICT (dna_test_id) DO NOTHING;

-- ============================================
-- STEP 12: Migrate existing DNA match data to ancestry_dna_match
-- ============================================

-- Migrate from old dna_match table if shared_cm data exists
-- Note: match_side column may not exist in V2's schema, use NULL
DO $$
DECLARE
    has_match_side BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'ancestry_tester' AND column_name = 'match_side'
    ) INTO has_match_side;

    IF has_match_side THEN
        INSERT INTO ancestry_dna_match (tester_1_id, tester_2_id, shared_cm, shared_segments, predicted_relationship, match_side, created_at)
        SELECT
            CASE WHEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a' < at.dna_test_id
                 THEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
                 ELSE at.dna_test_id END,
            CASE WHEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a' < at.dna_test_id
                 THEN at.dna_test_id
                 ELSE 'e756de6c-0c8d-443b-8793-addb6f35fd6a' END,
            at.shared_cm,
            at.shared_segments,
            at.predicted_relationship,
            at.match_side,
            at.created_at
        FROM ancestry_tester at
        WHERE at.dna_test_id != 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
          AND at.shared_cm IS NOT NULL
        ON CONFLICT (tester_1_id, tester_2_id) DO NOTHING;
    ELSE
        INSERT INTO ancestry_dna_match (tester_1_id, tester_2_id, shared_cm, shared_segments, predicted_relationship, created_at)
        SELECT
            CASE WHEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a' < at.dna_test_id
                 THEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
                 ELSE at.dna_test_id END,
            CASE WHEN 'e756de6c-0c8d-443b-8793-addb6f35fd6a' < at.dna_test_id
                 THEN at.dna_test_id
                 ELSE 'e756de6c-0c8d-443b-8793-addb6f35fd6a' END,
            at.shared_cm,
            at.shared_segments,
            at.predicted_relationship,
            at.created_at
        FROM ancestry_tester at
        WHERE at.dna_test_id != 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
          AND at.shared_cm IS NOT NULL
        ON CONFLICT (tester_1_id, tester_2_id) DO NOTHING;
    END IF;
END $$;

-- ============================================
-- STEP 13: Remove relationship columns from ancestry_tester
-- ============================================

ALTER TABLE ancestry_tester DROP CONSTRAINT IF EXISTS dna_match_match_side_check;
ALTER TABLE ancestry_tester DROP CONSTRAINT IF EXISTS dna_match_mrca_confidence_check;

DROP INDEX IF EXISTS idx_dna_match_shared_cm;
DROP INDEX IF EXISTS idx_dna_match_match_side;

ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS shared_cm;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS shared_segments;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS predicted_relationship;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS match_side;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS mrca;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS mrca_confidence;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS matched_to_person_id;
ALTER TABLE ancestry_tester DROP COLUMN IF EXISTS community_id;

-- ============================================
-- STEP 14: Create helper view
-- ============================================

CREATE OR REPLACE VIEW my_dna_matches AS
SELECT 
    at.dna_test_id,
    at.name,
    at.has_tree,
    at.tree_size,
    at.person_id,
    m.shared_cm,
    m.shared_segments,
    m.predicted_relationship,
    m.match_side
FROM ancestry_tester at
JOIN ancestry_dna_match m ON (
    at.dna_test_id = CASE 
        WHEN m.tester_1_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a' THEN m.tester_2_id 
        ELSE m.tester_1_id 
    END
)
WHERE m.tester_1_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a' 
   OR m.tester_2_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
ORDER BY m.shared_cm DESC NULLS LAST;

COMMENT ON VIEW my_dna_matches IS 'Convenience view: all DNA matches to you with relationship data';

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check ancestry tables:
-- SELECT 'ancestry_tester' as tbl, COUNT(*) FROM ancestry_tester;
-- SELECT 'ancestry_dna_match' as tbl, COUNT(*) FROM ancestry_dna_match;

-- Check your top matches:
-- SELECT * FROM my_dna_matches LIMIT 20;

-- Check trees:
-- SELECT id, name, ancestry_tree_id, size, dna_test_id FROM tree;

-- Check a person with tree link:
-- SELECT p.id, p.first_name, p.surname, p.tree_id, t.name as tree_name
-- FROM person p
-- LEFT JOIN tree t ON p.tree_id = t.id
-- LIMIT 10;
