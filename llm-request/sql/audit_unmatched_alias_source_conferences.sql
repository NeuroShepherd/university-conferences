-- Audit alias rows whose source conference names do not map to canonical conferences.

-- Summary count of alias rows with no mapped source_conference_id.
SELECT COUNT(*) AS unmatched_alias_rows
FROM university_name_aliases
WHERE source_conference_id IS NULL;

-- Distinct unmatched source conference names with row counts.
SELECT
    source_conference_name,
    COUNT(*) AS alias_row_count
FROM university_name_aliases
WHERE source_conference_id IS NULL
GROUP BY source_conference_name
ORDER BY alias_row_count DESC, source_conference_name;

-- Detailed rows for manual reconciliation if needed.
SELECT
    alias_id,
    canonical_university_id,
    canonical_university_wikipedia_href,
    alias_university_name,
    source_conference_name
FROM university_name_aliases
WHERE source_conference_id IS NULL
ORDER BY source_conference_name, canonical_university_wikipedia_href, alias_university_name;
