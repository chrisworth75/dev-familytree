-- V3__consolidate_dna_match.sql
-- Consolidate ancestry_person + ancestry_match into proper dna_match table
--
-- This migration handles TWO different starting states:
--
-- State A (from V2 standard path):
--   - dna_match already exists as a TABLE with ancestry_id PK
--   - ancestry_person and ancestry_match do NOT exist
--   - Action: Skip migration, table already correct
--
-- State B (from manual dev divergence):
--   - ancestry_person: DNA match profiles (ancestry_id PK, name, etc.)
--   - ancestry_match: relationship data (person1_id, person2_id, shared_cm)
--   - dna_match: VIEW joining the above (hack)
--   - match_cluster.ancestry_person_id -> ancestry_person
--   - tree.ancestry_person_id -> ancestry_person
--   - Action: Migrate data and restructure
--
-- Target state for both:
--   - dna_match: proper TABLE with all match data
--   - match_cluster.dna_match_id -> dna_match
--   - tree.dna_match_id -> dna_match

-- ============================================
-- STEP 1: Check which state we're in and act accordingly
-- ============================================

DO $$
DECLARE
    ancestry_person_exists BOOLEAN;
    dna_match_is_table BOOLEAN;
BEGIN
    -- Check if ancestry_person table exists (State B indicator)
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ancestry_person'
    ) INTO ancestry_person_exists;

    -- Check if dna_match exists as a table (not view)
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'dna_match' AND table_type = 'BASE TABLE'
    ) INTO dna_match_is_table;

    IF NOT ancestry_person_exists AND dna_match_is_table THEN
        -- State A: Coming from V2, dna_match already correct
        RAISE NOTICE 'V3: dna_match table already exists from V2, skipping migration';
    ELSIF ancestry_person_exists THEN
        -- State B: Need to migrate from ancestry_person/ancestry_match
        RAISE NOTICE 'V3: Migrating from ancestry_person/ancestry_match to dna_match';

        -- Drop the view
        DROP VIEW IF EXISTS dna_match CASCADE;

        -- Create proper dna_match table
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

        -- Migrate data
        INSERT INTO dna_match (
            ancestry_id, name, shared_cm, shared_segments, predicted_relationship,
            source, admin_level, has_tree, tree_size, notes, match_side,
            mrca, mrca_confidence, community_id, matched_to_person_id, person_id,
            created_at, updated_at
        )
        SELECT DISTINCT ON (ap.ancestry_id)
            ap.ancestry_id, ap.name, am.shared_cm, am.shared_segments,
            ap.predicted_relationship, 'ancestry', ap.admin_level, ap.has_tree,
            ap.tree_size, ap.notes, ap.match_side, ap.mrca, ap.mrca_confidence,
            ap.community_id, 1, ap.person_id, ap.created_at, ap.updated_at
        FROM ancestry_person ap
        LEFT JOIN ancestry_match am ON ap.ancestry_id = am.person2_id
        ORDER BY ap.ancestry_id, am.shared_cm DESC NULLS LAST;

        -- Update match_cluster
        ALTER TABLE match_cluster RENAME COLUMN ancestry_person_id TO dna_match_id;
        ALTER TABLE match_cluster DROP CONSTRAINT IF EXISTS match_cluster_ancestry_person_fkey;
        ALTER TABLE match_cluster ADD CONSTRAINT match_cluster_dna_match_fkey
            FOREIGN KEY (dna_match_id) REFERENCES dna_match(ancestry_id);

        -- Update tree
        ALTER TABLE tree RENAME COLUMN ancestry_person_id TO dna_match_id;
        ALTER TABLE tree DROP CONSTRAINT IF EXISTS tree_ancestry_person_fkey;
        ALTER TABLE tree ADD CONSTRAINT tree_dna_match_fkey
            FOREIGN KEY (dna_match_id) REFERENCES dna_match(ancestry_id);

        -- Add indexes
        CREATE INDEX idx_dna_match_name ON dna_match(name);
        CREATE INDEX idx_dna_match_shared_cm ON dna_match(shared_cm DESC NULLS LAST);
        CREATE INDEX idx_dna_match_matched_to_person ON dna_match(matched_to_person_id);
        CREATE INDEX idx_dna_match_person_id ON dna_match(person_id) WHERE person_id IS NOT NULL;
        CREATE INDEX idx_dna_match_match_side ON dna_match(match_side) WHERE match_side IS NOT NULL;

        -- Add foreign key for person_id
        ALTER TABLE dna_match ADD CONSTRAINT dna_match_person_fkey
            FOREIGN KEY (person_id) REFERENCES person(id);

        -- Drop old tables
        ALTER TABLE ancestry_match DROP CONSTRAINT IF EXISTS ancestry_match_person1_id_fkey;
        ALTER TABLE ancestry_match DROP CONSTRAINT IF EXISTS ancestry_match_person2_id_fkey;
        ALTER TABLE ancestry_person DROP CONSTRAINT IF EXISTS ancestry_person_person_id_fkey;
        DROP INDEX IF EXISTS idx_ancestry_person_person_id;
        DROP TABLE ancestry_match;
        DROP TABLE ancestry_person;
    ELSE
        -- Unexpected state - create dna_match from scratch
        RAISE NOTICE 'V3: Creating dna_match table from scratch';

        CREATE TABLE IF NOT EXISTS dna_match (
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
    END IF;

    -- Clean up match_cluster.person_id if it exists (from old V1 schema)
    IF EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_name = 'match_cluster' AND column_name = 'person_id'
    ) THEN
        ALTER TABLE match_cluster DROP COLUMN person_id;
    END IF;
END $$;

-- Add comments only for columns that exist (V2 path has fewer columns)
DO $$
BEGIN
    -- These columns exist in both V2 and State B paths
    COMMENT ON COLUMN dna_match.ancestry_id IS 'Ancestry.com test GUID - uniquely identifies this DNA match';
    COMMENT ON COLUMN dna_match.name IS 'Display name of the DNA match';
    COMMENT ON COLUMN dna_match.matched_to_person_id IS 'The person in our tree whose DNA test this match appears on (default 1 = me)';
    COMMENT ON COLUMN dna_match.person_id IS 'Link to person record when match has been identified in family tree';
    COMMENT ON COLUMN dna_match.admin_level IS 'Ancestry admin level: 0=viewer, 1=contributor, 2=editor, 3=manager, 4=owner';

    -- These columns only exist in State B path
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'dna_match' AND column_name = 'match_side') THEN
        COMMENT ON COLUMN dna_match.match_side IS 'Which side of the family: paternal, maternal, both, or unknown';
    END IF;
    IF EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'dna_match' AND column_name = 'mrca') THEN
        COMMENT ON COLUMN dna_match.mrca IS 'Most recent common ancestor if known';
    END IF;
END $$;
