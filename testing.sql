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