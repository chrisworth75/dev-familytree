-- Rename parent columns for clarity
ALTER TABLE person RENAME COLUMN parent_1_id TO father_id;
ALTER TABLE person RENAME COLUMN parent_2_id TO mother_id;
