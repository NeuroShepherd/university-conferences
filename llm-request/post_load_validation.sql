SET search_path TO sports_conferences;

-- 1) Core row counts
SELECT 'dim_universities' AS table_name, COUNT(*) AS row_count FROM dim_universities
UNION ALL
SELECT 'dim_conferences', COUNT(*) FROM dim_conferences
UNION ALL
SELECT 'fact_membership', COUNT(*) FROM fact_membership
ORDER BY table_name;

-- 2) Duplicate current university names
SELECT LOWER(current_university_name) AS normalized_name, COUNT(*) AS duplicate_count
FROM dim_universities
GROUP BY LOWER(current_university_name)
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, normalized_name;

-- 3) Duplicate current conference names
SELECT LOWER(current_conference_name) AS normalized_name, COUNT(*) AS duplicate_count
FROM dim_conferences
GROUP BY LOWER(current_conference_name)
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, normalized_name;

-- 4) Sample fact rows with joined labels
SELECT
    fm.membership_id,
    u.current_university_name,
    c.current_conference_name,
    mt.type_name AS membership_type,
    s.sport_name_normalized AS sport,
    d.division_name,
    fm.joined_year,
    fm.left_year,
    fm.membership_notes
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
JOIN dim_conferences c ON c.conference_id = fm.conference_id
JOIN dim_membership_types mt ON mt.membership_type_id = fm.membership_type_id
LEFT JOIN dim_sports s ON s.sport_id = fm.sport_id
LEFT JOIN dim_divisions d ON d.division_id = fm.division_id
ORDER BY fm.joined_year NULLS LAST, u.current_university_name, c.current_conference_name
LIMIT 50;

-- 5) Membership rows that are sport-specific
SELECT
    fm.membership_id,
    u.current_university_name,
    c.current_conference_name,
    mt.type_name,
    s.sport_name_normalized,
    d.division_name,
    fm.joined_year,
    fm.left_year
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
JOIN dim_conferences c ON c.conference_id = fm.conference_id
JOIN dim_membership_types mt ON mt.membership_type_id = fm.membership_type_id
JOIN dim_sports s ON s.sport_id = fm.sport_id
LEFT JOIN dim_divisions d ON d.division_id = fm.division_id
ORDER BY u.current_university_name, c.current_conference_name, s.sport_name_normalized
LIMIT 100;

-- 6) Membership rows that are not sport-specific
SELECT
    fm.membership_id,
    u.current_university_name,
    c.current_conference_name,
    mt.type_name,
    d.division_name,
    fm.joined_year,
    fm.left_year
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
JOIN dim_conferences c ON c.conference_id = fm.conference_id
JOIN dim_membership_types mt ON mt.membership_type_id = fm.membership_type_id
LEFT JOIN dim_divisions d ON d.division_id = fm.division_id
WHERE fm.sport_id IS NULL
ORDER BY u.current_university_name, c.current_conference_name
LIMIT 100;

-- 7) Rows that may be suspicious: sport-specific type but no sport
SELECT
    fm.membership_id,
    u.current_university_name,
    c.current_conference_name,
    mt.type_name,
    d.division_name,
    fm.joined_year,
    fm.left_year,
    fm.membership_notes
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
JOIN dim_conferences c ON c.conference_id = fm.conference_id
JOIN dim_membership_types mt ON mt.membership_type_id = fm.membership_type_id
LEFT JOIN dim_divisions d ON d.division_id = fm.division_id
WHERE fm.sport_id IS NULL
  AND (
      mt.type_name ILIKE '%Sport-Specific%'
      OR mt.type_name ILIKE '%Football only%'
      OR mt.type_name ILIKE '%Ice Hockey only%'
  )
ORDER BY u.current_university_name, c.current_conference_name;

-- 8) Rows that may be suspicious: full/general type but sport filled in
SELECT
    fm.membership_id,
    u.current_university_name,
    c.current_conference_name,
    mt.type_name,
    s.sport_name_normalized,
    d.division_name,
    fm.joined_year,
    fm.left_year,
    fm.membership_notes
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
JOIN dim_conferences c ON c.conference_id = fm.conference_id
JOIN dim_membership_types mt ON mt.membership_type_id = fm.membership_type_id
JOIN dim_sports s ON s.sport_id = fm.sport_id
LEFT JOIN dim_divisions d ON d.division_id = fm.division_id
WHERE mt.type_name IN (
    'Full Member',
    'Former Full Member',
    'Future Full Member',
    'Full Member (non-football)',
    'Future Full Member (non-football)'
)
ORDER BY u.current_university_name, c.current_conference_name, s.sport_name_normalized;

-- 9) Universities with the most membership rows
SELECT
    u.current_university_name,
    COUNT(*) AS membership_rows
FROM fact_membership fm
JOIN dim_universities u ON u.university_id = fm.university_id
GROUP BY u.current_university_name
ORDER BY membership_rows DESC, u.current_university_name
LIMIT 25;

-- 10) Conferences with the most membership rows
SELECT
    c.current_conference_name,
    COUNT(*) AS membership_rows
FROM fact_membership fm
JOIN dim_conferences c ON c.conference_id = fm.conference_id
GROUP BY c.current_conference_name
ORDER BY membership_rows DESC, c.current_conference_name
LIMIT 25;

-- 11) Membership rows with missing optional context
SELECT
    SUM(CASE WHEN sport_id IS NULL THEN 1 ELSE 0 END) AS rows_without_sport,
    SUM(CASE WHEN primary_conference_for_sport_id IS NULL THEN 1 ELSE 0 END) AS rows_without_primary_sport_conference,
    SUM(CASE WHEN previous_conference_id IS NULL THEN 1 ELSE 0 END) AS rows_without_previous_conference,
    SUM(CASE WHEN next_conference_id IS NULL THEN 1 ELSE 0 END) AS rows_without_next_conference,
    SUM(CASE WHEN membership_notes IS NULL THEN 1 ELSE 0 END) AS rows_without_notes
FROM fact_membership;

-- 12) Universities missing location or affiliation context
SELECT
    current_university_name,
    main_campus_city_id,
    current_affiliation_id
FROM dim_universities
WHERE main_campus_city_id IS NULL
   OR current_affiliation_id IS NULL
ORDER BY current_university_name;
