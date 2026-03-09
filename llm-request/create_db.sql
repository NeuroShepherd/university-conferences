CREATE SCHEMA IF NOT EXISTS sports_conferences;
SET search_path TO sports_conferences;


CREATE TABLE dim_associations (
    association_id SERIAL PRIMARY KEY,
    association_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE dim_divisions (
    division_id SERIAL PRIMARY KEY,
    division_name VARCHAR(50) NOT NULL UNIQUE,
    association_id INT NOT NULL,
    CONSTRAINT fk_division_association
        FOREIGN KEY (association_id)
        REFERENCES dim_associations(association_id)
);

CREATE TABLE dim_states (
    state_id SERIAL PRIMARY KEY,
    state_name VARCHAR(100) NOT NULL UNIQUE,
    state_abbreviation VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE dim_cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    state_id INT NOT NULL,
    CONSTRAINT fk_city_state
        FOREIGN KEY (state_id)
        REFERENCES dim_states(state_id),
    UNIQUE (city_name, state_id)
);

CREATE TABLE dim_affiliations (
    affiliation_id SERIAL PRIMARY KEY,
    affiliation_type VARCHAR(100) NOT NULL UNIQUE,
    denomination VARCHAR(100) NULL
);

CREATE TABLE dim_universities (
    university_id SERIAL PRIMARY KEY,
    current_university_name VARCHAR(255) NOT NULL UNIQUE,
    founded_year INT NULL,
    current_enrollment INT NULL,
    current_colors VARCHAR(255) NULL,
    main_campus_city_id INT NULL,
    main_campus_latitude DECIMAL(9,6) NULL,
    main_campus_longitude DECIMAL(9,6) NULL,
    current_affiliation_id INT NULL,
    CONSTRAINT fk_university_city
        FOREIGN KEY (main_campus_city_id)
        REFERENCES dim_cities(city_id),
    CONSTRAINT fk_university_affiliation
        FOREIGN KEY (current_affiliation_id)
        REFERENCES dim_affiliations(affiliation_id)
);

CREATE TABLE dim_conferences (
    conference_id SERIAL PRIMARY KEY,
    current_conference_name VARCHAR(255) NOT NULL UNIQUE,
    short_name VARCHAR(50) UNIQUE NULL,
    founded_year INT NULL
);

CREATE TABLE dim_sports (
    sport_id SERIAL PRIMARY KEY,
    sport_name_normalized VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE dim_membership_types (
    membership_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NULL
);


CREATE TABLE bridge_university_names (
    university_name_history_id SERIAL PRIMARY KEY,
    university_id INT NOT NULL,
    university_name VARCHAR(255) NOT NULL,
    start_year INT NOT NULL,
    end_year INT NULL,
    CONSTRAINT fk_uni_name_history_university
        FOREIGN KEY (university_id)
        REFERENCES dim_universities(university_id),
    UNIQUE (university_id, university_name, start_year)
);

CREATE TABLE bridge_university_nicknames (
    uni_nickname_history_id SERIAL PRIMARY KEY,
    university_id INT NOT NULL,
    nickname VARCHAR(100) NOT NULL,
    start_year INT NOT NULL,
    end_year INT NULL,
    sport_id INT NULL,
    -- sport_id_normalized is not needed; use expression in unique index
    CONSTRAINT fk_uni_nickname_history_university
        FOREIGN KEY (university_id)
        REFERENCES dim_universities(university_id),
    CONSTRAINT fk_uni_nickname_history_sport
        FOREIGN KEY (sport_id)
        REFERENCES dim_sports(sport_id)
    -- Use an expression-based unique index for COALESCE(sport_id, 0)
);
CREATE UNIQUE INDEX uq_uni_nickname_history ON bridge_university_nicknames (university_id, nickname, start_year, COALESCE(sport_id, 0));

CREATE TABLE bridge_university_sports (
    university_sport_history_id SERIAL PRIMARY KEY,
    university_id INT NOT NULL,
    sport_id INT NOT NULL,
    division_id INT NULL,
    start_year INT NOT NULL,
    end_year INT NULL,
    is_varsity BOOLEAN NOT NULL DEFAULT TRUE,
    sport_notes TEXT NULL,
    CONSTRAINT fk_uni_sport_history_university
        FOREIGN KEY (university_id)
        REFERENCES dim_universities(university_id),
    CONSTRAINT fk_uni_sport_history_sport
        FOREIGN KEY (sport_id)
        REFERENCES dim_sports(sport_id),
    CONSTRAINT fk_uni_sport_history_division
        FOREIGN KEY (division_id)
        REFERENCES dim_divisions(division_id)
);
CREATE UNIQUE INDEX uq_uni_sport_history ON bridge_university_sports (
    university_id,
    sport_id,
    start_year,
    COALESCE(division_id, 0)
);

CREATE TABLE bridge_conference_names (
    conference_name_history_id SERIAL PRIMARY KEY,
    conference_id INT NOT NULL,
    conference_name VARCHAR(255) NOT NULL,
    start_year INT NOT NULL,
    end_year INT NULL,
    CONSTRAINT fk_conf_name_history_conference
        FOREIGN KEY (conference_id)
        REFERENCES dim_conferences(conference_id),
    UNIQUE (conference_id, conference_name, start_year)
);

CREATE TABLE bridge_conference_divisions (
    conf_div_history_id SERIAL PRIMARY KEY,
    conference_id INT NOT NULL,
    division_id INT NOT NULL,
    start_year INT NOT NULL,
    end_year INT NULL,
    CONSTRAINT fk_conf_div_history_conference
        FOREIGN KEY (conference_id)
        REFERENCES dim_conferences(conference_id),
    CONSTRAINT fk_conf_div_history_division
        FOREIGN KEY (division_id)
        REFERENCES dim_divisions(division_id),
    UNIQUE (conference_id, division_id, start_year)
);

-- Fact Table

-- Records conference affiliation for a university as a whole or for a
-- specific sponsored sport. A row with sport_id = NULL is the default
-- membership context for all sponsored sports not overridden by a
-- sport-specific membership row.

CREATE TABLE fact_membership (
    membership_id SERIAL PRIMARY KEY,
    university_id INT NOT NULL,
    conference_id INT NOT NULL,
    membership_type_id INT NOT NULL,
    joined_year INT NOT NULL,
    left_year INT NULL,
    sport_id INT NULL,
    division_id INT NOT NULL,
    primary_conference_for_sport_id INT NULL,
    previous_conference_id INT NULL,
    next_conference_id INT NULL,
    reason_for_change TEXT NULL,
    membership_notes TEXT NULL,
    CONSTRAINT fk_membership_university
        FOREIGN KEY (university_id)
        REFERENCES dim_universities(university_id),
    CONSTRAINT fk_membership_conference
        FOREIGN KEY (conference_id)
        REFERENCES dim_conferences(conference_id),
    CONSTRAINT fk_membership_type
        FOREIGN KEY (membership_type_id)
        REFERENCES dim_membership_types(membership_type_id),
    CONSTRAINT fk_membership_sport
        FOREIGN KEY (sport_id)
        REFERENCES dim_sports(sport_id),
    CONSTRAINT fk_membership_division
        FOREIGN KEY (division_id)
        REFERENCES dim_divisions(division_id),
    CONSTRAINT fk_membership_primary_conf
        FOREIGN KEY (primary_conference_for_sport_id)
        REFERENCES dim_conferences(conference_id),
    CONSTRAINT fk_membership_prev_conf
        FOREIGN KEY (previous_conference_id)
        REFERENCES dim_conferences(conference_id),
    CONSTRAINT fk_membership_next_conf
        FOREIGN KEY (next_conference_id)
        REFERENCES dim_conferences(conference_id)
    -- Use a unique index with COALESCE for sport_id and left_year
);
CREATE UNIQUE INDEX uq_fact_membership ON fact_membership (
    university_id,
    conference_id,
    COALESCE(sport_id, 0),
    division_id,
    joined_year,
    COALESCE(left_year, 9999)
);