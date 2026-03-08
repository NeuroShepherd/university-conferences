
---

# Snowflake Schema Design for Sports Conference Membership Database

The goal is to create a comprehensive, normalized database schema using a snowflake design. This involves identifying core entities, their attributes, and their relationships, paying close attention to temporal data and complex scenarios like split conference memberships across sports or divisions.

---

## Considerations and Design Decisions

### 1. Normalization and Snowflake Schema

#### Core Entities

Universities, Conferences, Sports, Divisions, Associations, and Locations are central to the data.

#### Dimension Tables

Each core entity is modeled as a dimension table:

* `dim_universities`
* `dim_conferences`
* `dim_sports`
* `dim_divisions`
* `dim_associations`
* `dim_states`
* `dim_cities`
* `dim_affiliations`
* `dim_membership_types`

#### Further Normalization (Snowflake Aspect)

Dimensions like `dim_universities` and `dim_conferences` are not flat.

* `dim_universities` references:

  * `dim_cities` (for location)
  * `dim_affiliations` (for institutional type and denomination)
* `dim_cities` references:

  * `dim_states`
* `dim_divisions` references:

  * `dim_associations`

This layered structure is characteristic of a **snowflake schema**.

---

### 2. Temporal Data Handling (Membership Over Time)

#### Fact Table: `fact_membership`

This is the central table capturing the many-to-many relationship between universities and conferences over time, for specific sports and divisions.

It includes:

* `joined_year`
* `left_year`

These define the duration of each membership.

#### Slowly Changing Dimensions (Type 2)

For attributes that change over time (e.g., names), dedicated bridge tables are used:

* `bridge_university_names`
* `bridge_conference_names`
* `bridge_university_nicknames`
* `bridge_conference_divisions`

These store historical versions with:

* `start_year`
* `end_year`

The `dim_universities` and `dim_conferences` tables store only the **current state** for reporting convenience.

---

### 3. Complex Membership Scenarios

#### Split Membership Across Sports

The `fact_membership` table includes `sport_id` as a foreign key.

* **Full Member (all sports)**

  * `sport_id` = `NULL`
  * `membership_type_id` indicates "all sports"

* **Associate Member (sport)** or **Full Member (non-football)**

  * `sport_id` is populated with the specific sport

This allows multiple simultaneous memberships for a single university across different sports.

---

#### Sports Split Across Divisions

The `division_id` in `fact_membership` represents the division for that specific membership record.

This handles cases such as:

* A university competing in one division overall
* A specific sport competing in a different division

`dim_divisions` includes both NCAA divisions and NAIA.

---

#### University Name Changes

`bridge_university_names` tracks historical names.

`dim_universities` stores:

* `current_university_name`

---

#### Conference Name Changes

`bridge_conference_names` tracks historical conference names.

---

#### Nicknames

`bridge_university_nicknames` stores:

* General university nicknames
* Sport-specific nicknames
* Temporal history via `start_year` / `end_year`

`dim_universities` includes:

* `current_nickname` (for convenience)

---

#### Primary Conference for Affiliates

`primary_conference_for_sport_id` in `fact_membership` stores the main conference home for affiliate members.

---

### 4. Date/Year Handling

The following fields are modeled as `INT`:

* `start_year`
* `end_year`
* `joined_year`
* `left_year`

These represent calendar years and align with how membership timelines are typically presented (e.g., academic year spans).

This avoids unnecessary complexity from full `DATE` types when only year-level granularity is available.

---

### 5. Location and Affiliation Details

* `dim_states` and `dim_cities` provide geographic granularity.
* `dim_affiliations` captures:

  * Public
  * Private
  * Federal/Military
  * Religious denominations (when applicable)

This supports flexible institutional queries.

---

# SQL Database Schema

```sql
-- Create Schema (PostgreSQL)
CREATE SCHEMA IF NOT EXISTS sports_conferences;
SET search_path TO sports_conferences;

-- Dimension Tables

-- Stores information about athletic associations (e.g., NCAA, NAIA)
CREATE TABLE dim_associations (
    association_id SERIAL PRIMARY KEY,
    association_name VARCHAR(50) NOT NULL UNIQUE
);

-- Stores information about athletic divisions (e.g., Division I, Division II, NAIA)
CREATE TABLE dim_divisions (
    division_id SERIAL PRIMARY KEY,
    division_name VARCHAR(50) NOT NULL UNIQUE,
    association_id INT NOT NULL,
    CONSTRAINT fk_division_association
        FOREIGN KEY (association_id)
        REFERENCES dim_associations(association_id)
);

-- Stores information about states
CREATE TABLE dim_states (
    state_id SERIAL PRIMARY KEY,
    state_name VARCHAR(100) NOT NULL UNIQUE,
    state_abbreviation VARCHAR(10) NOT NULL UNIQUE
);

-- Stores information about cities, linked to states
CREATE TABLE dim_cities (
    city_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    state_id INT NOT NULL,
    CONSTRAINT fk_city_state
        FOREIGN KEY (state_id)
        REFERENCES dim_states(state_id),
    UNIQUE (city_name, state_id)
);

-- Stores information about university affiliations
CREATE TABLE dim_affiliations (
    affiliation_id SERIAL PRIMARY KEY,
    affiliation_type VARCHAR(100) NOT NULL UNIQUE,
    denomination VARCHAR(100) NULL
);

-- Stores current information about universities
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

-- Stores current information about conferences
CREATE TABLE dim_conferences (
    conference_id SERIAL PRIMARY KEY,
    current_conference_name VARCHAR(255) NOT NULL UNIQUE,
    short_name VARCHAR(50) UNIQUE NULL,
    founded_year INT NULL
);

-- Stores types of sports
CREATE TABLE dim_sports (
    sport_id SERIAL PRIMARY KEY,
    sport_name_normalized VARCHAR(100) NOT NULL UNIQUE
);

-- Stores types of memberships
CREATE TABLE dim_membership_types (
    membership_type_id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NULL
);

-- Bridge / History Tables

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
        REFERENCES dim_sports(sport_id),
    -- Use an expression-based unique index for COALESCE(sport_id, 0)
);
CREATE UNIQUE INDEX uq_uni_nickname_history ON bridge_university_nicknames (university_id, nickname, start_year, COALESCE(sport_id, 0));

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
```
