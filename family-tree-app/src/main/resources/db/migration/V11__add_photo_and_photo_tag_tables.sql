CREATE TABLE photo (
    id BIGSERIAL PRIMARY KEY,
    original_filename TEXT NOT NULL,
    description TEXT,
    year_taken INTEGER,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE photo_tag (
    photo_id BIGINT NOT NULL REFERENCES photo(id) ON DELETE CASCADE,
    person_id BIGINT NOT NULL REFERENCES person(id),
    x_position DOUBLE PRECISION,
    y_position DOUBLE PRECISION,
    PRIMARY KEY (photo_id, person_id)
);

CREATE INDEX idx_photo_tag_person_id ON photo_tag(person_id);
