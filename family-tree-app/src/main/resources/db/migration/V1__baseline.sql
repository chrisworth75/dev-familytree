-- V1__baseline.sql
-- Baseline schema for Family Tree application
-- Captures existing schema state before Flyway adoption

-- ============================================
-- SEQUENCES
-- ============================================

CREATE SEQUENCE IF NOT EXISTS cluster_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS dna_match_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS match_cluster_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS partnership_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS person_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS person_source_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS person_url_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS source_record_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS tree_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;
CREATE SEQUENCE IF NOT EXISTS tree_relationship_id_seq AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1;

-- ============================================
-- TABLES
-- ============================================

CREATE TABLE person (
    id integer NOT NULL DEFAULT nextval('person_id_seq'::regclass),
    ahnentafel integer,
    first_name character varying(500),
    middle_names character varying(500),
    surname character varying(255),
    birth_surname character varying(255),
    birth_date date,
    birth_place character varying(255),
    death_date date,
    death_place character varying(255),
    gender character(1),
    parent_1_id integer,
    parent_2_id integer,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    birth_year_approx integer,
    death_year_approx integer,
    ancestry_guid character varying(36),
    CONSTRAINT person_pkey PRIMARY KEY (id),
    CONSTRAINT person_ahnentafel_key UNIQUE (ahnentafel)
);

COMMENT ON COLUMN person.ahnentafel IS 'Ahnentafel number for YOUR direct ancestors only. 1=you, 2=father, 3=mother, 4=paternal grandfather, etc. NULL for everyone else.';
COMMENT ON COLUMN person.parent_1_id IS 'First parent (typically father). NULL if unknown.';
COMMENT ON COLUMN person.parent_2_id IS 'Second parent (typically mother). NULL if unknown.';

CREATE TABLE cluster (
    id integer NOT NULL DEFAULT nextval('cluster_id_seq'::regclass),
    name character varying(255),
    notes text,
    ahnentafel_1 integer,
    ahnentafel_2 integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT cluster_pkey PRIMARY KEY (id)
);

COMMENT ON COLUMN cluster.ahnentafel_1 IS 'First common ancestor for this cluster (your ahnentafel number). NULL if not yet determined.';
COMMENT ON COLUMN cluster.ahnentafel_2 IS 'Second common ancestor (spouse of ahnentafel_1) for full relationships. NULL for half-relationships or if unknown.';

CREATE TABLE dna_match (
    id integer NOT NULL DEFAULT nextval('dna_match_id_seq'::regclass),
    person_1_id integer NOT NULL,
    person_2_id integer NOT NULL,
    shared_cm numeric(6,1),
    shared_segments integer,
    source character varying(50),
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dna_match_pkey PRIMARY KEY (id),
    CONSTRAINT unique_match UNIQUE (person_1_id, person_2_id),
    CONSTRAINT person_order CHECK (person_1_id < person_2_id)
);

COMMENT ON COLUMN dna_match.person_1_id IS 'First person in the match. Constraint ensures person_1_id < person_2_id to avoid duplicates.';
COMMENT ON COLUMN dna_match.source IS 'Testing company: ancestry, 23andme, myheritage, familytreedna, etc.';

CREATE TABLE match_cluster (
    id integer NOT NULL DEFAULT nextval('match_cluster_id_seq'::regclass),
    person_id integer NOT NULL,
    cluster_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT match_cluster_pkey PRIMARY KEY (id),
    CONSTRAINT unique_person_cluster UNIQUE (person_id, cluster_id)
);

CREATE TABLE partnership (
    id integer NOT NULL DEFAULT nextval('partnership_id_seq'::regclass),
    person_1_id integer NOT NULL,
    person_2_id integer NOT NULL,
    marriage_date date,
    marriage_date_approx boolean DEFAULT false,
    marriage_place character varying(255),
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT partnership_pkey PRIMARY KEY (id),
    CONSTRAINT unique_partnership UNIQUE (person_1_id, person_2_id)
);

COMMENT ON COLUMN partnership.person_1_id IS 'For childless couples only - couples with children are linked via parent_1_id/parent_2_id on children.';

CREATE TABLE source_record (
    id integer NOT NULL DEFAULT nextval('source_record_id_seq'::regclass),
    record_type character varying(50) NOT NULL,
    title character varying(500),
    record_date date,
    record_date_approx boolean DEFAULT false,
    location character varying(255),
    reference character varying(255),
    url character varying(1000),
    data jsonb,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT source_record_pkey PRIMARY KEY (id)
);

COMMENT ON COLUMN source_record.record_type IS 'Type of record: census, birth, marriage, death, probate, burial, phone_directory, newspaper, obituary, etc.';
COMMENT ON COLUMN source_record.data IS 'JSONB for record-type-specific fields. Census: {household_id, occupation, relationship_to_head}. Probate: {effects_value, executor}. etc.';

CREATE TABLE person_source (
    id integer NOT NULL DEFAULT nextval('person_source_id_seq'::regclass),
    person_id integer NOT NULL,
    source_record_id integer NOT NULL,
    role character varying(50) NOT NULL,
    confidence character varying(20),
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT person_source_pkey PRIMARY KEY (id),
    CONSTRAINT unique_person_source_role UNIQUE (person_id, source_record_id, role)
);

COMMENT ON COLUMN person_source.role IS 'How the person relates to this record: subject, spouse, parent, child, witness, executor, mentioned, head_of_household';
COMMENT ON COLUMN person_source.confidence IS 'How confident is this link: certain, probable, possible, speculative';

CREATE TABLE person_url (
    id integer NOT NULL DEFAULT nextval('person_url_id_seq'::regclass),
    person_id integer NOT NULL,
    url character varying(1000) NOT NULL,
    description character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT person_url_pkey PRIMARY KEY (id)
);

CREATE TABLE tree (
    id integer NOT NULL DEFAULT nextval('tree_id_seq'::regclass),
    name character varying(255),
    source character varying(100),
    owner_name character varying(255),
    match_person_id integer,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tree_pkey PRIMARY KEY (id)
);

COMMENT ON COLUMN tree.match_person_id IS 'The DNA match whose tree this is. Links to person record for the match.';

CREATE TABLE tree_relationship (
    id integer NOT NULL DEFAULT nextval('tree_relationship_id_seq'::regclass),
    tree_id integer NOT NULL,
    person_id integer NOT NULL,
    ancestry_id character varying(100),
    parent_1_ancestry_id character varying(100),
    parent_2_ancestry_id character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tree_relationship_pkey PRIMARY KEY (id),
    CONSTRAINT unique_tree_person UNIQUE (tree_id, person_id)
);

COMMENT ON COLUMN tree_relationship.ancestry_id IS 'The ID of this person in the original source system (e.g. Ancestry person ID).';

-- ============================================
-- SEQUENCE OWNERSHIP
-- ============================================

ALTER SEQUENCE cluster_id_seq OWNED BY cluster.id;
ALTER SEQUENCE dna_match_id_seq OWNED BY dna_match.id;
ALTER SEQUENCE match_cluster_id_seq OWNED BY match_cluster.id;
ALTER SEQUENCE partnership_id_seq OWNED BY partnership.id;
ALTER SEQUENCE person_id_seq OWNED BY person.id;
ALTER SEQUENCE person_source_id_seq OWNED BY person_source.id;
ALTER SEQUENCE person_url_id_seq OWNED BY person_url.id;
ALTER SEQUENCE source_record_id_seq OWNED BY source_record.id;
ALTER SEQUENCE tree_id_seq OWNED BY tree.id;
ALTER SEQUENCE tree_relationship_id_seq OWNED BY tree_relationship.id;

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_person_ahnentafel ON person(ahnentafel) WHERE ahnentafel IS NOT NULL;
CREATE INDEX idx_person_surname ON person(surname);
CREATE INDEX idx_person_parent_1 ON person(parent_1_id);
CREATE INDEX idx_person_parent_2 ON person(parent_2_id);
CREATE INDEX idx_person_ancestry_guid ON person(ancestry_guid) WHERE ancestry_guid IS NOT NULL;

CREATE INDEX idx_dna_match_person_1 ON dna_match(person_1_id);
CREATE INDEX idx_dna_match_person_2 ON dna_match(person_2_id);
CREATE INDEX idx_dna_match_shared_cm ON dna_match(shared_cm);

CREATE INDEX idx_match_cluster_person ON match_cluster(person_id);
CREATE INDEX idx_match_cluster_cluster ON match_cluster(cluster_id);

CREATE INDEX idx_partnership_person_1 ON partnership(person_1_id);
CREATE INDEX idx_partnership_person_2 ON partnership(person_2_id);

CREATE INDEX idx_source_record_type ON source_record(record_type);
CREATE INDEX idx_source_record_date ON source_record(record_date);
CREATE INDEX idx_source_record_data ON source_record USING GIN (data);

CREATE INDEX idx_person_source_person ON person_source(person_id);
CREATE INDEX idx_person_source_record ON person_source(source_record_id);

CREATE INDEX idx_person_url_person ON person_url(person_id);

CREATE INDEX idx_tree_relationship_tree ON tree_relationship(tree_id);
CREATE INDEX idx_tree_relationship_person ON tree_relationship(person_id);
CREATE INDEX idx_tree_relationship_ancestry_id ON tree_relationship(ancestry_id);

-- ============================================
-- FOREIGN KEYS
-- ============================================

ALTER TABLE person ADD CONSTRAINT person_parent_1_id_fkey FOREIGN KEY (parent_1_id) REFERENCES person(id);
ALTER TABLE person ADD CONSTRAINT person_parent_2_id_fkey FOREIGN KEY (parent_2_id) REFERENCES person(id);

ALTER TABLE cluster ADD CONSTRAINT cluster_ahnentafel_1_fkey FOREIGN KEY (ahnentafel_1) REFERENCES person(ahnentafel);
ALTER TABLE cluster ADD CONSTRAINT cluster_ahnentafel_2_fkey FOREIGN KEY (ahnentafel_2) REFERENCES person(ahnentafel);

ALTER TABLE dna_match ADD CONSTRAINT dna_match_person_1_id_fkey FOREIGN KEY (person_1_id) REFERENCES person(id);
ALTER TABLE dna_match ADD CONSTRAINT dna_match_person_2_id_fkey FOREIGN KEY (person_2_id) REFERENCES person(id);

ALTER TABLE match_cluster ADD CONSTRAINT match_cluster_person_id_fkey FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE match_cluster ADD CONSTRAINT match_cluster_cluster_id_fkey FOREIGN KEY (cluster_id) REFERENCES cluster(id);

ALTER TABLE partnership ADD CONSTRAINT partnership_person_1_id_fkey FOREIGN KEY (person_1_id) REFERENCES person(id);
ALTER TABLE partnership ADD CONSTRAINT partnership_person_2_id_fkey FOREIGN KEY (person_2_id) REFERENCES person(id);

ALTER TABLE person_source ADD CONSTRAINT person_source_person_id_fkey FOREIGN KEY (person_id) REFERENCES person(id);
ALTER TABLE person_source ADD CONSTRAINT person_source_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES source_record(id);

ALTER TABLE person_url ADD CONSTRAINT person_url_person_id_fkey FOREIGN KEY (person_id) REFERENCES person(id);

ALTER TABLE tree ADD CONSTRAINT tree_match_person_id_fkey FOREIGN KEY (match_person_id) REFERENCES person(id);

ALTER TABLE tree_relationship ADD CONSTRAINT tree_relationship_tree_id_fkey FOREIGN KEY (tree_id) REFERENCES tree(id);
ALTER TABLE tree_relationship ADD CONSTRAINT tree_relationship_person_id_fkey FOREIGN KEY (person_id) REFERENCES person(id);
