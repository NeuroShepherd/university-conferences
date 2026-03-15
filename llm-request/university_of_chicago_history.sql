SET search_path TO sports_conferences;

-- Full history for the University of Chicago
-- Run with:
-- \i llm-request/university_of_chicago_history.sql

WITH target_university AS (
    SELECT university_id, current_university_name
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
)
SELECT
    u.university_id,
    u.current_university_name,
    u.founded_year,
    u.current_enrollment,
    u.current_colors,
    c.city_name AS main_campus_city,
    s.state_name AS main_campus_state,
    a.affiliation_type,
    a.denomination,
    u.main_campus_latitude,
    u.main_campus_longitude
FROM dim_universities u
LEFT JOIN dim_cities c ON c.city_id = u.main_campus_city_id
LEFT JOIN dim_states s ON s.state_id = c.state_id
LEFT JOIN dim_affiliations a ON a.affiliation_id = u.current_affiliation_id
WHERE u.university_id IN (SELECT university_id FROM target_university);

-- University name history
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
)
SELECT
    bun.university_name,
    bun.start_year,
    bun.end_year
FROM bridge_university_names bun
WHERE bun.university_id IN (SELECT university_id FROM target_university)
ORDER BY bun.start_year NULLS FIRST, bun.end_year NULLS LAST, bun.university_name;

-- Nickname history
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
)
SELECT
    bun.nickname,
    ds.sport_name_normalized AS sport,
    bun.start_year,
    bun.end_year
FROM bridge_university_nicknames bun
LEFT JOIN dim_sports ds ON ds.sport_id = bun.sport_id
WHERE bun.university_id IN (SELECT university_id FROM target_university)
ORDER BY bun.start_year NULLS FIRST, bun.end_year NULLS LAST, bun.nickname, ds.sport_name_normalized;

-- Sports history
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
)
SELECT
    ds.sport_name_normalized AS sport,
    dd.division_name,
    bus.start_year,
    bus.end_year,
    bus.is_varsity,
    bus.sport_notes
FROM bridge_university_sports bus
LEFT JOIN dim_sports ds ON ds.sport_id = bus.sport_id
LEFT JOIN dim_divisions dd ON dd.division_id = bus.division_id
WHERE bus.university_id IN (SELECT university_id FROM target_university)
ORDER BY bus.start_year NULLS FIRST, bus.end_year NULLS LAST, ds.sport_name_normalized;

-- Conference membership history
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
)
SELECT
    dc.current_conference_name AS conference,
    dmt.type_name AS membership_type,
    ds.sport_name_normalized AS sport,
    dd.division_name,
    fm.joined_year,
    fm.left_year,
    CASE
        WHEN fm.left_year IS NULL THEN 'current'
        WHEN fm.left_year <= EXTRACT(YEAR FROM CURRENT_DATE)::INT THEN 'former'
        ELSE 'future/planned'
    END AS membership_status,
    (LOWER(dc.current_conference_name) LIKE '%big ten%') AS is_big_ten,
    primary_conf.current_conference_name AS primary_conference_for_sport,
    prev_conf.current_conference_name AS previous_conference,
    next_conf.current_conference_name AS next_conference,
    fm.reason_for_change,
    fm.membership_notes
FROM fact_membership fm
JOIN dim_conferences dc ON dc.conference_id = fm.conference_id
JOIN dim_membership_types dmt ON dmt.membership_type_id = fm.membership_type_id
LEFT JOIN dim_sports ds ON ds.sport_id = fm.sport_id
LEFT JOIN dim_divisions dd ON dd.division_id = fm.division_id
LEFT JOIN dim_conferences primary_conf ON primary_conf.conference_id = fm.primary_conference_for_sport_id
LEFT JOIN dim_conferences prev_conf ON prev_conf.conference_id = fm.previous_conference_id
LEFT JOIN dim_conferences next_conf ON next_conf.conference_id = fm.next_conference_id
WHERE fm.university_id IN (SELECT university_id FROM target_university)
ORDER BY fm.joined_year NULLS FIRST, fm.left_year NULLS LAST, dc.current_conference_name, ds.sport_name_normalized;

-- Explicit Big Ten verification (this should show former membership rows when present)
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
),
big_ten_memberships AS (
    SELECT
        dc.current_conference_name AS conference,
        dmt.type_name AS membership_type,
        fm.joined_year,
        fm.left_year,
        CASE
            WHEN fm.left_year IS NULL THEN 'current'
            WHEN fm.left_year <= EXTRACT(YEAR FROM CURRENT_DATE)::INT THEN 'former'
            ELSE 'future/planned'
        END AS membership_status,
        fm.reason_for_change,
        fm.membership_notes
    FROM fact_membership fm
    JOIN dim_conferences dc ON dc.conference_id = fm.conference_id
    JOIN dim_membership_types dmt ON dmt.membership_type_id = fm.membership_type_id
    WHERE fm.university_id IN (SELECT university_id FROM target_university)
      AND LOWER(dc.current_conference_name) LIKE '%big ten%'
)
SELECT
    conference,
    membership_type,
    joined_year,
    left_year,
    membership_status,
    reason_for_change,
    membership_notes
FROM big_ten_memberships
ORDER BY joined_year NULLS FIRST, left_year NULLS LAST
;

-- Summary row so the script always clearly answers the Big Ten question.
WITH target_university AS (
    SELECT university_id
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
),
big_ten_memberships AS (
    SELECT fm.joined_year, fm.left_year
    FROM fact_membership fm
    JOIN dim_conferences dc ON dc.conference_id = fm.conference_id
    WHERE fm.university_id IN (SELECT university_id FROM target_university)
      AND LOWER(dc.current_conference_name) LIKE '%big ten%'
)
SELECT
    CASE
        WHEN EXISTS (SELECT 1 FROM big_ten_memberships WHERE left_year IS NOT NULL) THEN 'YES'
        ELSE 'NO'
    END AS former_big_ten_member,
    (SELECT MIN(joined_year) FROM big_ten_memberships) AS first_big_ten_year,
    (SELECT MAX(left_year) FROM big_ten_memberships) AS last_big_ten_year,
    CASE
        WHEN EXISTS (SELECT 1 FROM big_ten_memberships) THEN NULL
        ELSE 'No Big Ten membership rows found in current fact_membership data for University of Chicago.'
    END AS note;

-- Historical expectation check (independent of model output quality)
-- University of Chicago is historically a former Big Ten member (roughly 1896-1946).
WITH target_university AS (
    SELECT university_id, current_university_name
    FROM dim_universities
    WHERE LOWER(current_university_name) = LOWER('University of Chicago')
),
expected_history AS (
    SELECT
        'University of Chicago'::TEXT AS university_name,
        'Big Ten Conference'::TEXT AS conference,
        1896::INT AS expected_joined_year,
        1946::INT AS expected_left_year,
        'former'::TEXT AS expected_status
),
observed_match AS (
    SELECT
        eh.university_name,
        eh.conference,
        eh.expected_joined_year,
        eh.expected_left_year,
        eh.expected_status,
        EXISTS (
            SELECT 1
            FROM fact_membership fm
            JOIN dim_conferences dc ON dc.conference_id = fm.conference_id
            WHERE fm.university_id IN (SELECT university_id FROM target_university)
              AND LOWER(dc.current_conference_name) LIKE '%big ten%'
              AND (fm.left_year IS NOT NULL OR fm.left_year = eh.expected_left_year)
        ) AS found_in_dataset
    FROM expected_history eh
)
SELECT
    university_name,
    conference,
    expected_joined_year,
    expected_left_year,
    expected_status,
    found_in_dataset,
    CASE
        WHEN found_in_dataset THEN 'Confirmed by current dataset'
        ELSE 'Expected historically, but missing from current dataset output'
    END AS validation_note
FROM observed_match;
