## Design Decisions

The database schema is designed to meet the specified requirements for tracking university information, conference entities, and their primary conference memberships over time. The design adheres strictly to normalization principles and the provided scope constraints, avoiding unnecessary data points or relationships.

1.  **University Identification and Location:**
    *   A `Universities` table is created to store unique university entities.
    *   `university_id` serves as the primary key for unique identification.
    *   `university_wikipedia_href` is included as a canonical external identifier and is unique + non-null to prevent naming ambiguity (for example, schools with similar names).
    *   `university_name` is still required (`NOT NULL`) for readability, but uniqueness is anchored by `university_wikipedia_href`.
    *   `city` and `state` columns directly store the current geographical location of each university. These are non-nullable as every university is expected to have a location.

2.  **Conference Entities:**
    *   A `Conferences` table is established to store unique conference entities.
    *   `conference_id` acts as the primary key for unique identification.
    *   `conference_name` is unique and non-null, ensuring distinct conference names.
    *   `conference_wikipedia_href` is included as a canonical external identifier and is unique + non-null to prevent conference naming ambiguity.
    *   `conference_start_year` and `conference_end_year` capture the conference lifecycle itself (independent of any one university's membership periods).
    *   `conference_end_year` is nullable to support currently active conferences.
    *   A `CHECK` constraint ensures conference lifecycle years are valid (`conference_end_year IS NULL OR conference_start_year <= conference_end_year`).

3.  **Primary Conference Memberships Over Time:**
    *   The `University_Conference_Memberships` table models the many-to-many relationship between universities and conferences, incorporating the temporal aspect of membership.
    *   `university_id` and `conference_id` are foreign keys, creating links to the `Universities` and `Conferences` tables respectively. They are non-nullable, ensuring every membership record is tied to both a university and a conference.
    *   `start_year` captures the beginning year of a university's primary membership with a conference. It is non-nullable.
    *   `end_year` captures the ending year of a membership. This column is nullable (`NULL`) to represent ongoing or current memberships, fulfilling the requirement for open-ended periods.
    *   **Uniqueness Constraint:** The primary key for this table is a composite key consisting of (`university_id`, `conference_id`, `start_year`). This design directly addresses the rule to "prevent exact duplicate membership timeline rows for the same university and conference" by ensuring that a university cannot have two identical membership periods (same university, same conference, same start year). This also implicitly allows a university to have multiple, distinct membership periods with the same conference over time (e.g., leaving and rejoining).
    *   **Temporal Integrity:** A `CHECK` constraint (`end_year IS NULL OR start_year <= end_year`) is included to enforce logical consistency, ensuring that an end year, if present, is not before its corresponding start year.

## Schema DDL

```sql
CREATE TABLE Universities (
    university_id SERIAL PRIMARY KEY,
    university_name VARCHAR(255) NOT NULL,
    university_wikipedia_href VARCHAR(512) UNIQUE NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL
);

CREATE TABLE Conferences (
    conference_id SERIAL PRIMARY KEY,
    conference_name VARCHAR(255) UNIQUE NOT NULL,
    conference_wikipedia_href VARCHAR(512) UNIQUE NOT NULL,
    conference_start_year SMALLINT,
    conference_end_year SMALLINT,
    CHECK (conference_end_year IS NULL OR conference_start_year <= conference_end_year)
);

CREATE TABLE University_Conference_Memberships (
    university_id INT NOT NULL,
    conference_id INT NOT NULL,
    start_year SMALLINT NOT NULL,
    end_year SMALLINT,
    PRIMARY KEY (university_id, conference_id, start_year),
    FOREIGN KEY (university_id) REFERENCES Universities(university_id),
    FOREIGN KEY (conference_id) REFERENCES Conferences(conference_id),
    CHECK (end_year IS NULL OR start_year <= end_year)
);
```