-- Family Tree Application Schema
-- PostgreSQL

-- ============================================
-- CORE TABLES
-- ============================================

CREATE TABLE person (
    id SERIAL PRIMARY KEY,
    ahnentafel INTEGER UNIQUE,  -- only your direct ancestors get a value
    first_name VARCHAR(100),
    middle_names VARCHAR(200),
    surname VARCHAR(100),
    birth_surname VARCHAR(100),  -- maiden name
    birth_date DATE,
    birth_date_approx BOOLEAN DEFAULT FALSE,
    birth_place VARCHAR(255),
    death_date DATE,
    death_date_approx BOOLEAN DEFAULT FALSE,
    death_place VARCHAR(255),
    gender CHAR(1),  -- M, F, U
    parent_1_id INTEGER REFERENCES person(id),
    parent_2_id INTEGER REFERENCES person(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_person_ahnentafel ON person(ahnentafel) WHERE ahnentafel IS NOT NULL;
CREATE INDEX idx_person_surname ON person(surname);
CREATE INDEX idx_person_parent_1 ON person(parent_1_id);
CREATE INDEX idx_person_parent_2 ON person(parent_2_id);

CREATE TABLE dna_match (
    id SERIAL PRIMARY KEY,
    person_1_id INTEGER NOT NULL REFERENCES person(id),
    person_2_id INTEGER NOT NULL REFERENCES person(id),
    shared_cm DECIMAL(6,1),
    shared_segments INTEGER,
    source VARCHAR(50),  -- ancestry, 23andme, myheritage, etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT person_order CHECK (person_1_id < person_2_id),
    CONSTRAINT unique_match UNIQUE (person_1_id, person_2_id)
);

CREATE INDEX idx_dna_match_person_1 ON dna_match(person_1_id);
CREATE INDEX idx_dna_match_person_2 ON dna_match(person_2_id);
CREATE INDEX idx_dna_match_shared_cm ON dna_match(shared_cm);

CREATE TABLE cluster (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    notes TEXT,
    ahnentafel_1 INTEGER REFERENCES person(ahnentafel),
    ahnentafel_2 INTEGER REFERENCES person(ahnentafel),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE match_cluster (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(id),
    cluster_id INTEGER NOT NULL REFERENCES cluster(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_person_cluster UNIQUE (person_id, cluster_id)
);

CREATE INDEX idx_match_cluster_person ON match_cluster(person_id);
CREATE INDEX idx_match_cluster_cluster ON match_cluster(cluster_id);

-- ============================================
-- EVIDENCE / SOURCE RECORDS
-- ============================================

CREATE TABLE source_record (
    id SERIAL PRIMARY KEY,
    record_type VARCHAR(50) NOT NULL,  -- census, birth, marriage, death, probate, burial, phone_directory, newspaper, etc.
    title VARCHAR(500),
    record_date DATE,
    record_date_approx BOOLEAN DEFAULT FALSE,
    location VARCHAR(255),
    reference VARCHAR(255),  -- archive reference, piece number, etc.
    url VARCHAR(1000),
    data JSONB,  -- type-specific fields
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_source_record_type ON source_record(record_type);
CREATE INDEX idx_source_record_date ON source_record(record_date);
CREATE INDEX idx_source_record_data ON source_record USING GIN (data);

CREATE TABLE person_source (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(id),
    source_record_id INTEGER NOT NULL REFERENCES source_record(id),
    role VARCHAR(50) NOT NULL,  -- subject, spouse, parent, child, witness, executor, mentioned, head_of_household
    confidence VARCHAR(20),  -- certain, probable, possible, speculative
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_person_source_role UNIQUE (person_id, source_record_id, role)
);

CREATE INDEX idx_person_source_person ON person_source(person_id);
CREATE INDEX idx_person_source_record ON person_source(source_record_id);

-- ============================================
-- IMPORTED TREES
-- ============================================

CREATE TABLE tree (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    source VARCHAR(100),  -- ancestry, findmypast, etc.
    owner_name VARCHAR(255),  -- who owns the tree
    match_person_id INTEGER REFERENCES person(id),  -- the DNA match this tree belongs to
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tree_relationship (
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES tree(id),
    person_id INTEGER NOT NULL REFERENCES person(id),
    ancestry_id VARCHAR(100),  -- their ID in the source system
    parent_1_ancestry_id VARCHAR(100),  -- parent's ID in source system
    parent_2_ancestry_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_tree_person UNIQUE (tree_id, person_id)
);

CREATE INDEX idx_tree_relationship_tree ON tree_relationship(tree_id);
CREATE INDEX idx_tree_relationship_person ON tree_relationship(person_id);
CREATE INDEX idx_tree_relationship_ancestry_id ON tree_relationship(ancestry_id);

-- ============================================
-- OTHER
-- ============================================

CREATE TABLE person_url (
    id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES person(id),
    url VARCHAR(1000) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_person_url_person ON person_url(person_id);

CREATE TABLE partnership (
    id SERIAL PRIMARY KEY,
    person_1_id INTEGER NOT NULL REFERENCES person(id),
    person_2_id INTEGER NOT NULL REFERENCES person(id),
    marriage_date DATE,
    marriage_date_approx BOOLEAN DEFAULT FALSE,
    marriage_place VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_partnership UNIQUE (person_1_id, person_2_id)
);

CREATE INDEX idx_partnership_person_1 ON partnership(person_1_id);
CREATE INDEX idx_partnership_person_2 ON partnership(person_2_id);

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN person.ahnentafel IS 'Ahnentafel number for YOUR direct ancestors only. 1=you, 2=father, 3=mother, 4=paternal grandfather, etc. NULL for everyone else.';
COMMENT ON COLUMN person.parent_1_id IS 'First parent (typically father). NULL if unknown.';
COMMENT ON COLUMN person.parent_2_id IS 'Second parent (typically mother). NULL if unknown.';
COMMENT ON COLUMN dna_match.person_1_id IS 'First person in the match. Constraint ensures person_1_id < person_2_id to avoid duplicates.';
COMMENT ON COLUMN dna_match.source IS 'Testing company: ancestry, 23andme, myheritage, familytreedna, etc.';
COMMENT ON COLUMN cluster.ahnentafel_1 IS 'First common ancestor for this cluster (your ahnentafel number). NULL if not yet determined.';
COMMENT ON COLUMN cluster.ahnentafel_2 IS 'Second common ancestor (spouse of ahnentafel_1) for full relationships. NULL for half-relationships or if unknown.';
COMMENT ON COLUMN source_record.record_type IS 'Type of record: census, birth, marriage, death, probate, burial, phone_directory, newspaper, obituary, etc.';
COMMENT ON COLUMN source_record.data IS 'JSONB for record-type-specific fields. Census: {household_id, occupation, relationship_to_head}. Probate: {effects_value, executor}. etc.';
COMMENT ON COLUMN person_source.role IS 'How the person relates to this record: subject, spouse, parent, child, witness, executor, mentioned, head_of_household';
COMMENT ON COLUMN person_source.confidence IS 'How confident is this link: certain, probable, possible, speculative';
COMMENT ON COLUMN tree.match_person_id IS 'The DNA match whose tree this is. Links to person record for the match.';
COMMENT ON COLUMN tree_relationship.ancestry_id IS 'The ID of this person in the original source system (e.g. Ancestry person ID).';
COMMENT ON COLUMN partnership.person_1_id IS 'For childless couples only - couples with children are linked via parent_1_id/parent_2_id on children.';
