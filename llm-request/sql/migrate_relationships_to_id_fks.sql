-- Migrate relationship tables to numeric ID foreign keys while preserving
-- existing href/name columns for traceability.

BEGIN;

ALTER TABLE university_name_aliases
    ADD COLUMN IF NOT EXISTS canonical_university_id BIGINT,
    ADD COLUMN IF NOT EXISTS source_conference_id BIGINT;

ALTER TABLE university_conference_memberships
    ADD COLUMN IF NOT EXISTS university_id BIGINT,
    ADD COLUMN IF NOT EXISTS conference_id BIGINT;

UPDATE university_name_aliases ua
SET canonical_university_id = u.university_id
FROM universities u
WHERE ua.canonical_university_id IS NULL
  AND ua.canonical_university_wikipedia_href = u.university_wikipedia_href;

UPDATE university_name_aliases ua
SET source_conference_id = c.conference_id
FROM conferences c
WHERE ua.source_conference_id IS NULL
  AND ua.source_conference_name = c.conference_name;

UPDATE university_conference_memberships m
SET university_id = u.university_id
FROM universities u
WHERE m.university_id IS NULL
  AND m.university_wikipedia_href = u.university_wikipedia_href;

UPDATE university_conference_memberships m
SET conference_id = c.conference_id
FROM conferences c
WHERE m.conference_id IS NULL
  AND m.conference_name = c.conference_name;

DO $$
DECLARE
    missing_alias_university_ids BIGINT;
    missing_membership_university_ids BIGINT;
    missing_membership_conference_ids BIGINT;
BEGIN
    SELECT COUNT(*) INTO missing_alias_university_ids
    FROM university_name_aliases
    WHERE canonical_university_id IS NULL;

    SELECT COUNT(*) INTO missing_membership_university_ids
    FROM university_conference_memberships
    WHERE university_id IS NULL;

    SELECT COUNT(*) INTO missing_membership_conference_ids
    FROM university_conference_memberships
    WHERE conference_id IS NULL;

    IF missing_alias_university_ids > 0
       OR missing_membership_university_ids > 0
       OR missing_membership_conference_ids > 0 THEN
        RAISE EXCEPTION
            'Migration failed: unresolved IDs (alias university %, membership university %, membership conference %)',
            missing_alias_university_ids,
            missing_membership_university_ids,
            missing_membership_conference_ids;
    END IF;
END $$;

ALTER TABLE university_name_aliases
    ALTER COLUMN canonical_university_id SET NOT NULL;

ALTER TABLE university_conference_memberships
    ALTER COLUMN university_id SET NOT NULL,
    ALTER COLUMN conference_id SET NOT NULL;

ALTER TABLE university_name_aliases
    ADD CONSTRAINT fk_aliases_university_id
        FOREIGN KEY (canonical_university_id)
        REFERENCES universities (university_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    ADD CONSTRAINT fk_aliases_conference_id
        FOREIGN KEY (source_conference_id)
        REFERENCES conferences (conference_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL;

ALTER TABLE university_conference_memberships
    ADD CONSTRAINT fk_memberships_university_id
        FOREIGN KEY (university_id)
        REFERENCES universities (university_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    ADD CONSTRAINT fk_memberships_conference_id
        FOREIGN KEY (conference_id)
        REFERENCES conferences (conference_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_aliases_university_id
    ON university_name_aliases (canonical_university_id);

CREATE INDEX IF NOT EXISTS idx_aliases_conference_id
    ON university_name_aliases (source_conference_id);

CREATE INDEX IF NOT EXISTS idx_memberships_university_id
    ON university_conference_memberships (university_id);

CREATE INDEX IF NOT EXISTS idx_memberships_conference_id
    ON university_conference_memberships (conference_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_membership_identity_period
    ON university_conference_memberships (university_id, conference_id, start_year, end_year);

COMMIT;
