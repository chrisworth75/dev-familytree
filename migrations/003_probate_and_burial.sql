-- 003_probate_and_burial.sql
-- Tables for probate calendars and burial registers

CREATE TABLE IF NOT EXISTS probate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT,
    death_date TEXT,
    probate_date TEXT,
    effects_value TEXT,
    occupation TEXT,
    executor TEXT,
    notes TEXT,
    source_image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS burial_register (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    burial_date TEXT,
    age INTEGER,
    abode TEXT,
    parish TEXT,
    diocese TEXT,
    entry_number INTEGER,
    officiant TEXT,
    notes TEXT,
    source_image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
