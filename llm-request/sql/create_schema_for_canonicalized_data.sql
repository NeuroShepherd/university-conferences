-- Schema for loading llm-request/sql/conference_data_canonicalized.sql
-- This is intentionally permissive so the generated insert file can load without manual cleanup.

BEGIN;

-- Drop in dependency-safe order.
DROP TABLE IF EXISTS university_conference_memberships;
DROP TABLE IF EXISTS university_name_aliases;
DROP TABLE IF EXISTS conferences;
DROP TABLE IF EXISTS universities;

CREATE TABLE universities (
    university_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    university_wikipedia_href TEXT NOT NULL UNIQUE,
    university_name TEXT NOT NULL,
    city TEXT,
    state TEXT
);

CREATE TABLE conferences (
    conference_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conference_name TEXT NOT NULL UNIQUE,
    conference_wikipedia_href TEXT,
    conference_start_year INTEGER,
    conference_end_year INTEGER,
    CHECK (
        conference_end_year IS NULL
        OR conference_start_year IS NULL
        OR conference_start_year <= conference_end_year
    )
);

CREATE TABLE university_name_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    canonical_university_wikipedia_href TEXT NOT NULL,
    alias_university_name TEXT NOT NULL,
    source_conference_name TEXT NOT NULL,
    FOREIGN KEY (canonical_university_wikipedia_href)
        REFERENCES universities (university_wikipedia_href)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

CREATE TABLE university_conference_memberships (
    membership_id BIGSERIAL PRIMARY KEY,
    university_wikipedia_href TEXT NOT NULL,
    conference_name TEXT NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    CHECK (
        end_year IS NULL
        OR start_year IS NULL
        OR start_year <= end_year
    )
);

CREATE INDEX idx_university_name_aliases_href
    ON university_name_aliases (canonical_university_wikipedia_href);

CREATE INDEX idx_university_name_aliases_name
    ON university_name_aliases (alias_university_name);

CREATE INDEX idx_memberships_href
    ON university_conference_memberships (university_wikipedia_href);

CREATE INDEX idx_memberships_conference
    ON university_conference_memberships (conference_name);

CREATE INDEX idx_memberships_years
    ON university_conference_memberships (start_year, end_year);

COMMIT;
