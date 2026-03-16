WITH big10 AS (
SELECT *
FROM university_conference_memberships
WHERE conference_name = 'Big Ten Conference'
)

SELECT *
FROM big10;

WITH uchicago AS (
SELECT *
FROM universities
WHERE university_name = 'University of Chicago'
)

SELECT *
FROM uchicago AS u
LEFT JOIN university_conference_memberships AS mem
ON u.university_wikipedia_href = mem.university_wikipedia_href;

SELECT *
FROM universities
WHERE LOWER(university_name) LIKE LOWER('%MicHigan%');


SELECT *
FROM universities AS u
LEFT JOIN university_conference_memberships AS mem
ON u.university_wikipedia_href = mem.university_wikipedia_href
WHERE u.university_id = 1117;


-- find most recent conference membership for university_id 1117
SELECT *
FROM universities AS u
LEFT JOIN university_conference_memberships AS mem
ON u.university_wikipedia_href = mem.university_wikipedia_href
WHERE u.university_id = 1117
	AND mem.start_year = (
		SELECT MAX(start_year)
	      FROM university_conference_memberships
	      WHERE university_wikipedia_href = u.university_wikipedia_href
	);


-- alternative to the previous code, but works properly for multiple schools
SELECT *
FROM (
    SELECT *,
           MAX(start_year) OVER (PARTITION BY university_wikipedia_href) AS max_start_year
    FROM university_conference_memberships
) mem
JOIN universities u
  ON u.university_wikipedia_href = mem.university_wikipedia_href
WHERE u.university_id IN (1117, 1118)
  AND mem.start_year = mem.max_start_year;