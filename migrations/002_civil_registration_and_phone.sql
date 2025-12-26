-- 002_civil_registration_and_phone.sql
-- Tables for civil registration indexes (BMD) and phone directories

CREATE TABLE IF NOT EXISTS civil_registration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('birth', 'marriage', 'death')),
    year INTEGER NOT NULL,
    quarter TEXT CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    name TEXT NOT NULL,
    district TEXT,
    volume TEXT,
    page TEXT,
    spouse_surname TEXT,          -- for marriages
    mother_maiden_name TEXT,      -- for births (post-1911)
    notes TEXT,
    source_image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phone_directory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    phone_number TEXT,
    source_page TEXT,
    source_image TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS person_civil_registration_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES person(id),
    civil_registration_id INTEGER NOT NULL REFERENCES civil_registration(id),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(person_id, civil_registration_id)
);
