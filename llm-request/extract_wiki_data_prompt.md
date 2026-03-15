## Task

Extract structured data for a **single conference payload** from `data-assembly/json/final_data.json`.

The input object always represents one conference and contains:

1. `member_schools.content`
2. `conference_history.content`
3. Optional `timeline_map.map_text`

Your job is to extract only:

1. University name
2. University city
3. University state
4. Primary membership period in the conference (start year, end year if known)

Do not extract sports-level, division-level, or association-level records.

## Scope Rules

1. Only output rows that represent a university's **primary** membership in the current conference.
2. Ignore sport-only affiliate/associate memberships.
3. If `timeline_map.map_text` exists, use it as a high-priority source for years.
4. Use `member_schools.content` and `conference_history.content` to resolve names and fill missing years/locations.
5. Do not invent facts. If a value is not present or cannot be inferred with high confidence, use `null`.

## Primary Membership Guidance

When reading timeline maps, keep only entries that indicate full or primary conference membership.

1. Include entries marked as full members (for example, labels equivalent to all-sports membership, including all-sports-except-football if it is the institution's primary conference membership context).
2. Exclude entries marked as associate/affiliate/sport-only.
3. Exclude bars that only indicate membership in other conferences after departure.

## Normalization and Naming Rules

1. Use canonical university names when an alias is shown (for example, `[[University Name|Alias]]` should map to `University Name` if clear).
2. Keep conference name exactly as represented by the conference key in the input payload.
3. City and state should represent the university's campus location in current/common usage when present in source text.
4. Keep years as integers.
5. Use `null` for unknown `end_year` (ongoing membership) or unavailable values.

## Output Format

Return **only valid JSON** (no prose, no markdown, no code fences) using this exact top-level structure:

```json
{
	"universities": {
		"columns": ["university_name", "city", "state"],
		"rows": []
	},
	"conferences": {
		"columns": ["conference_name"],
		"rows": []
	},
	"university_conference_memberships": {
		"columns": ["university_name", "conference_name", "start_year", "end_year"],
		"rows": []
	}
}
```

## Output Constraints

1. Include exactly one conference row for the current conference.
2. `universities.rows` should contain one row per distinct university referenced by included primary-membership rows.
3. `university_conference_memberships.rows` may contain multiple periods for the same university if it left and rejoined.
4. Do not output exact duplicate membership rows (`university_name`, `conference_name`, `start_year`, `end_year`).
5. Ensure all membership rows reference a university present in `universities.rows`.

## Quality Checks Before Returning

1. Confirm JSON parses.
2. Confirm required keys and column lists match exactly.
3. Confirm each membership row has non-null `university_name`, `conference_name`, and `start_year`.
4. Confirm no sport-only/associate-only memberships are included.
