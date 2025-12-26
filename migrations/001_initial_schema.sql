-- 001_initial_schema.sql
-- Core tables for genealogy census tracking

CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    birth_year_estimate INTEGER,
    birth_year_range_low INTEGER,
    birth_year_range_high INTEGER,
    birth_place TEXT,
    death_year INTEGER,
    death_place TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS census_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    piece_folio TEXT,
    registration_district TEXT,
    sub_district TEXT,
    parish TEXT,
    address TEXT,
    
    name_as_recorded TEXT NOT NULL,
    relationship_to_head TEXT,
    marital_status TEXT,
    age_as_recorded INTEGER,
    sex TEXT,
    occupation TEXT,
    birth_place_as_recorded TEXT,
    
    household_id TEXT,
    schedule_number INTEGER,
    
    raw_text TEXT,
    source_url TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS person_census_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES person(id),
    census_record_id INTEGER NOT NULL REFERENCES census_record(id),
    
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    name_score REAL,
    age_score REAL,
    birthplace_score REAL,
    household_score REAL,
    location_score REAL,
    occupation_score REAL,
    
    reasoning TEXT,
    linked_by TEXT DEFAULT 'manual',
    verified INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(person_id, census_record_id)
);

CREATE TABLE IF NOT EXISTS relationship (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id_1 INTEGER NOT NULL REFERENCES person(id),
    person_id_2 INTEGER NOT NULL REFERENCES person(id),
    relationship_type TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
